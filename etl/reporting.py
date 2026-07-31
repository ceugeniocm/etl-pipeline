"""Contadores, progresso, resumo e relatório de rejeições (FR-006, FR-014).

Implementação prevista para a Fase 6 de ``docs/tasks.md`` (tarefas 51 a 53).
"""

from __future__ import annotations

import csv
import sys
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from etl import messages

if TYPE_CHECKING:
    from etl.transform.validation import Rejection


@dataclass
class ExecutionStats:
    """Contadores da execução do pipeline (tarefa 51)."""

    read: int = 0
    transformed: int = 0
    loaded: int = 0
    rejected: int = 0
    duplicated: int = 0
    start_time: float = 0.0
    end_time: float = 0.0

    def start(self) -> None:
        """Marca o início da execução."""
        self.start_time = time.time()

    def finish(self) -> None:
        """Marca o fim da execução."""
        self.end_time = time.time()

    @property
    def elapsed(self) -> str:
        """Devolve o tempo decorrido formatado como HH:MM:SS."""
        seconds = int(self.end_time - self.start_time)
        return time.strftime("%H:%M:%S", time.gmtime(seconds))


def print_progress(stats: ExecutionStats) -> None:
    """Exibe uma linha de progresso no console (tarefa 51)."""
    line = messages.PROGRESS_CHUNK.format(
        read=stats.read,
        transformed=stats.transformed,
        loaded=stats.loaded,
        rejected=stats.rejected,
    )
    print(line, file=sys.stderr)


def print_summary(stats: ExecutionStats, success: bool) -> None:
    """Exibe o resumo final da execução (tarefa 52)."""
    print(f"\n{messages.SUMMARY_TITLE}", file=sys.stderr)
    print("-" * len(messages.SUMMARY_TITLE), file=sys.stderr)
    print(messages.SUMMARY_ROWS_READ.format(count=stats.read), file=sys.stderr)
    print(
        messages.SUMMARY_ROWS_TRANSFORMED.format(count=stats.transformed),
        file=sys.stderr,
    )
    print(messages.SUMMARY_ROWS_LOADED.format(count=stats.loaded), file=sys.stderr)
    print(messages.SUMMARY_ROWS_REJECTED.format(count=stats.rejected), file=sys.stderr)
    if stats.duplicated > 0:
        print(
            messages.SUMMARY_ROWS_DUPLICATED.format(count=stats.duplicated),
            file=sys.stderr,
        )
    print(messages.SUMMARY_ELAPSED.format(elapsed=stats.elapsed), file=sys.stderr)

    status = (
        messages.SUMMARY_STATUS_SUCCESS if success else messages.SUMMARY_STATUS_FAILURE
    )
    print(status, file=sys.stderr)


class RejectionReporter:
    """Grava as rejeições em um arquivo CSV (tarefa 53)."""

    def __init__(self, path: str) -> None:
        self.path = path
        self._count = 0

    def write(self, rejections: list[Rejection]) -> None:
        """Adiciona rejeições ao relatório.

        Cria o arquivo e escreve o cabeçalho na primeira chamada.
        """
        if not rejections:
            return

        mode = "a" if self._count > 0 else "w"
        with open(self.path, mode, encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            if self._count == 0:
                # Cabeçalhos em pt_BR conforme NFR-009
                writer.writerow(["aba", "linha", "coluna", "motivo"])

            for r in rejections:
                writer.writerow([r.sheet, r.row, r.column, r.reason])
                self._count += 1

    @property
    def count(self) -> int:
        """Total de rejeições gravadas."""
        return self._count
