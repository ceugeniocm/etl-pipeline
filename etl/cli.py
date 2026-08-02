"""Interface de linha de comando do pipeline (FR-012).

A interface completa — ``argparse`` com o caminho da configuração e as
sobreposições, ajuda em ``pt_BR``, ``--dry-run`` e códigos de saída por classe
de falha — está prevista para a Fase 6 de ``docs/tasks.md`` (tarefas 48 a 50).
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from typing import Any

from etl import logging_setup, messages
from etl.config import EtlConfig, load_config
from etl.errors import EXIT_SUCCESS, EXIT_UNEXPECTED_ERROR, exit_code_for
from etl.pipeline import Pipeline

__all__ = ["main"]


def main(argv: Sequence[str] | None = None) -> int:
    """Ponto de entrada da CLI; devolve o código de saída do processo (tarefa 48).

    :param argv: argumentos da linha de comando, sem o nome do programa; o
        padrão é ``sys.argv[1:]``.
    """
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        prog="etl",
        description=messages.CLI_DESCRIPTION,
        epilog=messages.CLI_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=True,
    )

    parser.add_argument("config", help=messages.CLI_HELP_CONFIG)
    parser.add_argument("--source", help=messages.CLI_HELP_SOURCE)
    parser.add_argument("--sheet", help=messages.CLI_HELP_SHEET)
    parser.add_argument("--table", help=messages.CLI_HELP_TABLE)
    parser.add_argument("--chunk-size", type=int, help=messages.CLI_HELP_CHUNK_SIZE)
    parser.add_argument("--batch-size", type=int, help=messages.CLI_HELP_BATCH_SIZE)
    parser.add_argument("--mode", help=messages.CLI_HELP_LOAD_MODE)
    parser.add_argument("--log-level", help=messages.CLI_HELP_LOG_LEVEL)
    parser.add_argument("--log-file", help=messages.CLI_HELP_LOG_FILE)
    parser.add_argument(
        "--dry-run", action="store_true", default=None, help=messages.CLI_HELP_DRY_RUN
    )
    parser.add_argument(
        "--verbose", action="store_true", help=messages.CLI_HELP_VERBOSE
    )
    parser.add_argument("--resume", action="store_true", help=messages.CLI_HELP_RESUME)
    parser.add_argument("--workers", type=int, help=messages.CLI_HELP_WORKERS)

    args = parser.parse_args(argv)

    try:
        # 1. Monta as sobreposições (overrides)
        overrides: dict[str, Any] = {
            "source.path": args.source,
            "source.sheet": args.sheet,
            "load.table": args.table,
            "source.chunk_size": args.chunk_size,
            "load.batch_size": args.batch_size,
            "load.mode": args.mode,
            "run.log_file": args.log_file,
            "run.dry_run": args.dry_run,
            "run.resume": args.resume or None,
            "run.workers": args.workers,
        }

        if args.verbose:
            overrides["run.log_level"] = "DEBUG"
        elif args.log_level:
            overrides["run.log_level"] = args.log_level

        # 2. Carrega e valida a configuração (Task 12)
        config = load_config(args.config, overrides=overrides)

        # 3. Inicializa o log (Task 6)
        logging_setup.configure_logging(
            level=config.run.log_level,
            log_file=config.run.log_file,
        )

        # 4. Executa o pipeline (Task 46)
        pipeline = Pipeline(config)
        success = pipeline.run()

        return EXIT_SUCCESS if success else exit_code_for(None)  # Será tratado no run

    except Exception as error:
        # Tratamento de erros de configuração ou falhas fatais (Task 49)
        # Se o log já estiver configurado, o erro já foi logado.
        # Caso contrário, imprimimos no stderr.
        exit_code = exit_code_for(error)
        if exit_code == EXIT_UNEXPECTED_ERROR:
            # Para erros não previstos, mostra a mensagem completa
            print(messages.ERR_UNEXPECTED.format(reason=str(error)), file=sys.stderr)
        else:
            # Para erros previstos (EtlError), a mensagem já é amigável
            print(str(error), file=sys.stderr)

        return exit_code
