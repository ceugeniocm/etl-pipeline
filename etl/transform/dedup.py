"""Deduplicação por chave de negócio (FR-007).

Este módulo identifica registros duplicados na mesma execução com base em uma
chave composta, garantindo a integridade dos dados antes da carga no MySQL.
"""

from typing import Any

from etl import messages
from etl.config import ValidationConfig
from etl.transform.validation import Rejection


class Deduplicator:
    """Identifica registros repetidos com base na chave de negócio (tarefa 32).

    Mantém em memória apenas a chave e o número da primeira linha onde ela
    apareceu, o que mantém o consumo de memória baixo mesmo para grandes
    volumes (NFR-001).
    """

    def __init__(self, config: ValidationConfig) -> None:
        self._config = config
        self._key_columns = config.business_key
        #: Mapeia a tupla de valores da chave para o número da primeira linha.
        self._seen: dict[tuple[Any, ...], int] = {}

    def check(
        self, values: dict[str, Any], sheet: str, row_number: int
    ) -> Rejection | None:
        """Verifica se a linha é duplicada.

        Se não houver chave de negócio configurada, esta função é um no-op
        (tarefa 32).

        :param values: valores da linha já validados.
        :param sheet: nome da aba de origem.
        :param row_number: número da linha na planilha.
        :return: uma :class:`Rejection` se for duplicado, caso contrário ``None``.
        """
        if not self._key_columns:
            return None

        # Monta a chave composta. Se uma coluna faltar, o valor será None.
        key = tuple(values.get(col) for col in self._key_columns)

        if key in self._seen:
            first_row = self._seen[key]
            return Rejection(
                sheet=sheet,
                row=row_number,
                column=", ".join(self._key_columns),
                reason=messages.REJECT_DUPLICATE_KEY.format(
                    key=key, first_row=first_row
                ),
            )

        self._seen[key] = row_number
        return None

    def clear(self) -> None:
        """Limpa o estado do deduplicador."""
        self._seen.clear()
