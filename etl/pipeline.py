"""Orquestração das etapas do pipeline (FR-001 a FR-010, NFR-001).

Implementação prevista para a Fase 6 de ``docs/tasks.md`` (tarefas 46 e 47):
encadeamento preguiçoso extração -> blocos -> mapeamento -> limpeza ->
conversão -> validação -> deduplicação -> carga, além do ciclo de vida da
execução (contadores, propagação de erros e encerramento da conexão).
"""

from __future__ import annotations

import logging
from typing import Any

from etl import messages
from etl.checkpoint import delete_checkpoint, load_checkpoint, save_checkpoint
from etl.config import EtlConfig
from etl.errors import EtlError, RejectionThresholdExceeded
from etl.extract import open_source, iter_chunks
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


class Pipeline:
    """Orquestrador do processo ETL (tarefa 46)."""

    def __init__(self, config: EtlConfig) -> None:
        self.config = config
        self.stats = ExecutionStats()
        self.reporter = RejectionReporter(config.run.rejection_report)
        self.threshold = RejectionThreshold(config.validation)
        self.deduplicator = Deduplicator(config.validation)

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
                    loader = Loader(
                        conn,
                        self.config.database,
                        self.config.load,
                        self.config.mapping,
                    )
                    loader.check_target()
                    loader.prepare()

                # 3. Iteração em blocos (lazy chain)
                for chunk in iter_chunks(sheet.rows(), self.config.source.chunk_size):
                    batch_data: list[tuple[int, dict[str, Any]]] = []

                    for row in chunk:
                        if last_row and row.number <= last_row:
                            continue

                        self.stats.read += 1

                        # Pipeline de transformação
                        mapped = apply_mapping(row, self.config.mapping)
                        cleaned = clean_row(mapped, self.config.mapping)
                        coerced = coerce_row(cleaned, self.config.mapping)

                        outcome = validate_row(
                            coerced,
                            self.config.validation,
                            row.sheet,
                            row.number,
                        )

                        if isinstance(outcome, list):  # Rejeições de validação
                            self.stats.rejected += 1
                            self.reporter.write(outcome)
                            self.threshold.count(is_rejected=True)
                            continue

                        # Se chegou aqui, a linha passou na validação estrutural
                        self.stats.transformed += 1

                        # Deduplicação
                        dup_rejection = self.deduplicator.check(
                            outcome, row.sheet, row.number
                        )
                        if dup_rejection:
                            self.stats.rejected += 1
                            self.stats.duplicated += 1
                            self.reporter.write([dup_rejection])
                            self.threshold.count(is_rejected=True)
                            continue

                        # Linha limpa e única, pronta para carga
                        self.threshold.count(is_rejected=False)
                        batch_data.append((row.number, outcome))

                    # 4. Carga do lote (Task 38)
                    def save_cb(row_num: int) -> None:
                        save_checkpoint(self.config.run.checkpoint_file, row_num)

                    if loader and batch_data:
                        loaded, failed = loader.load_batch(batch_data, on_success=save_cb)
                        self.stats.loaded += loaded
                        self.stats.rejected += failed
                    elif batch_data:
                        # Dry-run: apenas conta como carregado (Task 50)
                        self.stats.loaded += len(batch_data)
                        # No dry-run, salvamos o ponto ao final do bloco
                        save_cb(batch_data[-1][0])

                    print_progress(self.stats)

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
