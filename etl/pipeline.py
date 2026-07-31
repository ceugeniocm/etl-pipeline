"""Orquestração das etapas do pipeline (FR-001 a FR-010, NFR-001).

Implementação prevista para a Fase 6 de ``docs/tasks.md`` (tarefas 46 e 47):
encadeamento preguiçoso extração -> blocos -> mapeamento -> limpeza ->
conversão -> validação -> deduplicação -> carga, além do ciclo de vida da
execução (contadores, propagação de erros e encerramento da conexão).
"""

from __future__ import annotations

__all__: list[str] = []
