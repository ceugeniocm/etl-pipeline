"""Interface de linha de comando do pipeline (FR-012).

A interface completa — ``argparse`` com o caminho da configuração e as
sobreposições, ajuda em ``pt_BR``, ``--dry-run`` e códigos de saída por classe
de falha — está prevista para a Fase 6 de ``docs/tasks.md`` (tarefas 48 a 50).

Nesta fase existe apenas o ponto de entrada :func:`main`, chamado por
``main.py``, que sinaliza a ausência da implementação com o código de saída
:data:`etl.errors.EXIT_NOT_IMPLEMENTED`.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence

from etl import messages
from etl.errors import EXIT_NOT_IMPLEMENTED

__all__ = ["main"]


def main(argv: Sequence[str] | None = None) -> int:
    """Ponto de entrada da CLI; devolve o código de saída do processo.

    :param argv: argumentos da linha de comando, sem o nome do programa; o
        padrão é ``sys.argv[1:]``.
    """
    del argv  # Os argumentos passam a ser tratados na Fase 6.
    print(messages.CLI_NOT_IMPLEMENTED, file=sys.stderr)
    return EXIT_NOT_IMPLEMENTED
