"""Validação de dados e gestão de rejeições (FR-006).

Este módulo verifica se os registros atendem às regras de negócio (campos
obrigatórios, limites de valor e comprimento) e gerencia o limite de erros
aceitáveis para a execução.
"""

from dataclasses import dataclass
from typing import Any

from etl import messages
from etl.config import ValidationConfig
from etl.errors import RejectionThresholdExceeded
from etl.transform.types import CoercionFailure


@dataclass(frozen=True, slots=True)
class Rejection:
    """Representa um erro em uma coluna específica de uma linha (tarefa 30)."""

    sheet: str
    row: int
    column: str
    reason: str


def validate_row(
    values: dict[str, Any],
    config: ValidationConfig,
    sheet: str,
    row_number: int,
) -> dict[str, Any] | list[Rejection]:
    """Valida a linha contra as regras da configuração (tarefa 29).

    :param values: valores já mapeados, limpos e com tipos coagidos.
    :param config: configuração de validação.
    :param sheet: nome da aba de origem.
    :param row_number: número da linha na planilha.
    :return: o dicionário de valores (se limpo) ou uma lista de :class:`Rejection`.
    """
    rejections: list[Rejection] = []

    # 1. Falhas de conversão de tipo (tarefa 28)
    for column, value in values.items():
        if isinstance(value, CoercionFailure):
            rejections.append(
                Rejection(
                    sheet=sheet,
                    row=row_number,
                    column=column,
                    reason=messages.REJECT_TYPE_CONVERSION.format(
                        value=value.value, column=column, expected_type=value.target_type
                    ),
                )
            )

    # Se houve erro de tipo, não faz sentido validar faixas ou comprimentos.
    if rejections:
        return rejections

    # 2. Campos obrigatórios
    for column in config.required:
        if values.get(column) is None:
            rejections.append(
                Rejection(
                    sheet=sheet,
                    row=row_number,
                    column=column,
                    reason=messages.REJECT_REQUIRED_FIELD.format(column=column),
                )
            )

    # 3. Intervalos de valores (ranges)
    for column, (minimum, maximum) in config.ranges.items():
        value = values.get(column)
        if value is not None:
            if (minimum is not None and value < minimum) or (
                maximum is not None and value > maximum
            ):
                rejections.append(
                    Rejection(
                        sheet=sheet,
                        row=row_number,
                        column=column,
                        reason=messages.REJECT_OUT_OF_RANGE.format(
                            value=value,
                            column=column,
                            minimum=minimum,
                            maximum=maximum,
                        ),
                    )
                )

    # 4. Comprimento máximo
    for column, max_len in config.max_lengths.items():
        value = values.get(column)
        if value is not None:
            length = len(str(value))
            if length > max_len:
                rejections.append(
                    Rejection(
                        sheet=sheet,
                        row=row_number,
                        column=column,
                        reason=messages.REJECT_MAX_LENGTH.format(
                            column=column, length=length, maximum=max_len
                        ),
                    )
                )

    if rejections:
        return rejections

    return values


class RejectionThreshold:
    """Controla o limite de registros rejeitados (tarefa 31)."""

    def __init__(self, config: ValidationConfig) -> None:
        self._config = config
        self._rejected = 0
        self._total = 0

    def count(self, is_rejected: bool) -> None:
        """Contabiliza uma linha e aborta se o limite for excedido.

        :raises RejectionThresholdExceeded: se o limite absoluto ou percentual
            for ultrapassado.
        """
        self._total += 1
        if is_rejected:
            self._rejected += 1
            self._check_limits()

    def _check_limits(self) -> None:
        # Limite absoluto
        limit_rows = self._config.max_rejected_rows
        if limit_rows is not None and self._rejected > limit_rows:
            raise RejectionThresholdExceeded(
                messages.ERR_REJECTION_THRESHOLD_EXCEEDED.format(
                    rejected=self._rejected,
                    total=self._total,
                    threshold=limit_rows,
                )
            )

        # Limite percentual
        limit_pct = self._config.max_rejected_percent
        if limit_pct is not None:
            percent = (self._rejected / self._total) * 100
            if percent > limit_pct:
                raise RejectionThresholdExceeded(
                    messages.ERR_REJECTION_THRESHOLD_EXCEEDED.format(
                        rejected=self._rejected,
                        total=self._total,
                        threshold=f"{limit_pct}%",
                    )
                )
