"""Orquestração das etapas do pipeline (FR-001 a FR-010, NFR-001).

Implementação prevista para a Fase 6 de ``docs/tasks.md`` (tarefas 46 e 47):
encadeamento preguiçoso extração -> blocos -> mapeamento -> limpeza ->
conversão -> validação -> deduplicação -> carga, além do ciclo de vida da
execução (contadores, propagação de erros e encerramento da conexão).
"""

from __future__ import annotations

import logging
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from typing import Any, Iterable

from etl import messages
from etl.checkpoint import delete_checkpoint, load_checkpoint, save_checkpoint
from etl.config import DimensionConfig, EtlConfig, MappingConfig, ValidationConfig
from etl.errors import EtlError, RejectionThresholdExceeded
from etl.extract import SourceRow, iter_chunks, open_source
from etl.load.connection import get_connection
from etl.load.loader import Loader
from etl.reporting import (
    ExecutionStats,
    RejectionReporter,
    print_progress,
    print_summary,
)
from etl.transform.cleaning import clean_row
from etl.transform.dedup import Deduplicator
from etl.transform.mapping import apply_mapping, check_mapping
from etl.transform.types import coerce_row
from etl.transform.validation import RejectionThreshold, validate_row

logger = logging.getLogger(__name__)


def _transform_row(
    row: SourceRow,
    mapping: MappingConfig,
    validation: ValidationConfig,
    dimensions: list[DimensionConfig],
) -> tuple[int, str, Any, list[Any]]:
    """Transforma uma única linha (FR-017).
    
    Esta função é top-level para ser serializável pelo multiprocessing.
    """
    # 1. Processamento de dimensões
    dim_outcomes = []
    for dim_cfg in dimensions:
        d_mapped = apply_mapping(row, dim_cfg.mapping)
        d_cleaned = clean_row(d_mapped, dim_cfg.mapping)
        d_coerced = coerce_row(d_cleaned, dim_cfg.mapping)
        d_outcome = validate_row(d_coerced, dim_cfg.validation, row.sheet, row.number)
        dim_outcomes.append(d_outcome)

    # 2. Processamento da fato
    mapped = apply_mapping(row, mapping)
    cleaned = clean_row(mapped, mapping)
    coerced = coerce_row(cleaned, mapping)
    outcome = validate_row(coerced, validation, row.sheet, row.number)

    return row.number, row.sheet, outcome, dim_outcomes


class Pipeline:
    """Orquestrador do processo ETL (tarefa 46)."""

    def __init__(self, config: EtlConfig) -> None:
        self.config = config
        self.stats = ExecutionStats()
        self.reporter = RejectionReporter(config.run.rejection_report)
        self.threshold = RejectionThreshold(config.validation)
        self.deduplicator = Deduplicator(config.validation)
        self.seen_by_table: dict[str, set[tuple[Any, ...]]] = {}
        self.dimension_contexts = []
        for dim in config.dimensions:
            table = dim.load.table
            if table not in self.seen_by_table:
                self.seen_by_table[table] = set()
            
            self.dimension_contexts.append({
                "config": dim,
                "seen": self.seen_by_table[table],
                "loader": None
            })

    def _get_unique_key_value(
        self, data: dict[str, Any], unique_key: tuple[str, ...]
    ) -> tuple[Any, ...]:
        """Extrai os valores da chave única para deduplicação (FR-016)."""
        return tuple(data.get(col) for col in unique_key)

    def run(self) -> bool:
        """Executa o pipeline completo (tarefa 47).

        :return: True se concluído com sucesso, False em caso de erro.
        :raises EtlError: para falhas fatais que interrompem a execução.
        """
        self.stats.start()
        success = False
        conn = None

        try:
            logger.info(
                messages.INFO_RUN_STARTED.format(
                    source=self.config.source.path, table=self.config.load.table
                )
            )

            if self.config.run.dry_run:
                logger.info(messages.INFO_DRY_RUN)

            logger.info(messages.INFO_LOAD_MODE.format(mode=self.config.load.mode))

            last_row = None
            if self.config.run.resume:
                last_row = load_checkpoint(self.config.run.checkpoint_file)
                if last_row:
                    logger.info(messages.INFO_RESUMING.format(row=last_row))

            # 1. Abertura da origem e verificação do mapeamento
            with open_source(self.config.source) as sheet:
                check_mapping(sheet.columns, self.config.mapping, sheet.sheet)

                # 2. Conexão e Loader (se não for dry-run)
                loader = None
                if not self.config.run.dry_run:
                    conn = get_connection(self.config.database)
                    
                    # Loader principal
                    loader = Loader(
                        conn,
                        self.config.database,
                        self.config.load,
                        self.config.mapping,
                    )
                    loader.check_target()
                    loader.prepare()

                    # Loaders de dimensões (Task 71)
                    for dim_ctx in self.dimension_contexts:
                        dim_loader = Loader(
                            conn,
                            self.config.database,
                            dim_ctx["config"].load,
                            dim_ctx["config"].mapping,
                        )
                        dim_loader.check_target()
                        dim_loader.prepare()
                        dim_ctx["loader"] = dim_loader

                # 3. Iteração em blocos (lazy chain)
                executor = None
                if self.config.run.workers > 1:
                    executor = ProcessPoolExecutor(max_workers=self.config.run.workers)

                # Executor para carga assíncrona (I/O paralelo)
                # Usamos apenas 1 worker para garantir a ordem de inserção e evitar 
                # concorrência na mesma conexão MySQL.
                load_executor = ThreadPoolExecutor(max_workers=1)
                load_futures = []

                try:
                    for chunk in iter_chunks(sheet.rows(), self.config.source.chunk_size):
                        active_rows = [
                            r for r in chunk if not (last_row and r.number <= last_row)
                        ]
                        if not active_rows:
                            continue

                        self.stats.read += len(active_rows)

                        if executor:
                            # Transformação paralela (FR-017)
                            # Otimização: chunksize > 1 reduz drasticamente o overhead de IPC
                            map_chunksize = max(1, len(active_rows) // (self.config.run.workers * 2))
                            results = executor.map(
                                _transform_row,
                                active_rows,
                                [self.config.mapping] * len(active_rows),
                                [self.config.validation] * len(active_rows),
                                [list(self.config.dimensions)] * len(active_rows),
                                chunksize=map_chunksize,
                            )
                        else:
                            # Transformação sequencial
                            results = (
                                _transform_row(
                                    r,
                                    self.config.mapping,
                                    self.config.validation,
                                    list(self.config.dimensions),
                                )
                                for r in active_rows
                            )

                        batch_data: list[tuple[int, dict[str, Any]]] = []
                        dimension_batches: list[list[tuple[int, dict[str, Any]]]] = [
                            [] for _ in self.dimension_contexts
                        ]

                        for row_number, sheet_name, outcome, dim_outcomes in results:
                            # Processamento de dimensões (Deduplicação centralizada)
                            for i, d_outcome in enumerate(dim_outcomes):
                                if not isinstance(
                                    d_outcome, list
                                ):  # Se passou na validação
                                    dim_ctx = self.dimension_contexts[i]
                                    dim_cfg = dim_ctx["config"]
                                    key = self._get_unique_key_value(
                                        d_outcome, dim_cfg.load.unique_key
                                    )
                                    if (
                                        all(v is not None for v in key)
                                        and key not in dim_ctx["seen"]
                                    ):
                                        dimension_batches[i].append(
                                            (row_number, d_outcome)
                                        )
                                        dim_ctx["seen"].add(key)

                            # Pipeline de transformação da fato (Deduplicação centralizada)
                            if isinstance(outcome, list):  # Rejeições de validação
                                self.stats.rejected += 1
                                self.reporter.write(outcome)
                                self.threshold.count(is_rejected=True)
                                continue

                            # Se chegou aqui, a linha passou na validação estrutural
                            self.stats.transformed += 1

                            # Deduplicação fato
                            dup_rejection = self.deduplicator.check(
                                outcome, sheet_name, row_number
                            )
                            if dup_rejection:
                                self.stats.rejected += 1
                                self.stats.duplicated += 1
                                self.reporter.write([dup_rejection])
                                self.threshold.count(is_rejected=True)
                                continue

                            # Linha limpa e única, pronta para carga
                            self.threshold.count(is_rejected=False)
                            batch_data.append((row_number, outcome))

                        # 4. Carga do lote (Task 38)
                        def save_cb(row_num: int) -> None:
                            save_checkpoint(self.config.run.checkpoint_file, row_num)

                        def _perform_load(b_data, d_batches):
                            """Executa a carga de um lote (dimensões e fato)."""
                            # Carga das dimensões antes da fato (Task 71)
                            for i, dim_ctx in enumerate(self.dimension_contexts):
                                db_batch = d_batches[i]
                                if db_batch and dim_ctx["loader"]:
                                    dim_ctx["loader"].load_batch(db_batch, auto_commit=False)

                            if loader and b_data:
                                l_count, f_count = loader.load_batch(
                                    b_data, on_success=None, auto_commit=False
                                )
                                conn.commit()
                                save_cb(b_data[-1][0])
                                return l_count, f_count
                            elif b_data:
                                # Dry-run: salvamos o ponto ao final do bloco
                                save_cb(b_data[-1][0])
                                return len(b_data), 0

                            if not self.config.run.dry_run and conn:
                                conn.commit()
                            return 0, 0

                        if self.config.run.workers > 1:
                            # Pipelining: Carga assíncrona enquanto processa o próximo chunk
                            future = load_executor.submit(
                                _perform_load, batch_data, dimension_batches
                            )
                            load_futures.append(future)

                            # Limpa futuros finalizados para atualizar estatísticas
                            for f in load_futures[:]:
                                if f.done():
                                    l_count, f_count = f.result()
                                    self.stats.loaded += l_count
                                    self.stats.rejected += f_count
                                    load_futures.remove(f)
                        else:
                            # Sequencial
                            l_count, f_count = _perform_load(batch_data, dimension_batches)
                            self.stats.loaded += l_count
                            self.stats.rejected += f_count

                        print_progress(self.stats)

                    # Aguarda cargas pendentes
                    for f in load_futures:
                        l_count, f_count = f.result()
                        self.stats.loaded += l_count
                        self.stats.rejected += f_count
                        print_progress(self.stats)

                finally:
                    if executor:
                        executor.shutdown()
                    load_executor.shutdown(wait=True)

            success = True
            delete_checkpoint(self.config.run.checkpoint_file)
            logger.info(messages.INFO_RUN_FINISHED)

        except EtlError:
            # Erros do pipeline já possuem mensagens amigáveis e logs (Task 47)
            raise
        except Exception as err:
            # Erros inesperados (Task 47)
            logger.exception(messages.ERR_UNEXPECTED.format(reason=str(err)))
            raise
        finally:
            self.stats.finish()
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

            # Relatório e resumo (Task 52, 53)
            if self.reporter.count > 0:
                logger.info(
                    messages.INFO_REJECTION_REPORT_WRITTEN.format(
                        path=self.config.run.rejection_report,
                        count=self.reporter.count,
                    )
                )

            print_summary(self.stats, success)

        return success
