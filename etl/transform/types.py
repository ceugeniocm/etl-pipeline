"""Coerção de tipos e tratamento de valores Excel (FR-005).

Este módulo converte os valores brutos da planilha nos tipos Python esperados
pelo banco de dados, tratando particularidades como números de série do Excel
e separadores decimais brasileiros.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from etl.config import MappingConfig

#: Data base usada pelo Excel (tarefa 27).
EXCEL_BASE_DATE = datetime(1899, 12, 30)

#: Valores reconhecidos como verdadeiro/falso (consistente com etl.config).
_TRUE_VALUES = ("1", "true", "t", "yes", "y", "on", "sim", "s")
_FALSE_VALUES = ("0", "false", "f", "no", "n", "off", "nao", "não")


@dataclass(frozen=True, slots=True)
class CoercionFailure:
    """Representa uma falha na conversão de tipo (tarefa 28).

    Ao invés de lançar uma exceção, o pipeline armazena este objeto para que a
    validação na etapa seguinte possa gerar uma rejeição amigável sem
    interromper o processamento da linha.
    """

    value: Any
    target_type: str


def coerce_value(value: Any, target_type: str) -> Any | CoercionFailure:
    """Tenta converter ``value`` para ``target_type``.

    :param value: valor bruto (pode ser None).
    :param target_type: um dos tipos em ``etl.config.KNOWN_TYPES``.
    :return: o valor convertido ou uma :class:`CoercionFailure` se a
        conversão falhar.
    """
    if value is None:
        return None

    try:
        if target_type == "str":
            return str(value)

        if target_type == "int":
            # Trata "1.234" vindo de texto como 1234
            if isinstance(value, str):
                value = value.replace(".", "").replace(",", "")
            return int(float(value))

        if target_type == "decimal":
            if isinstance(value, str):
                # Separadores decimais brasileiros (tarefa 27)
                if "," in value:
                    value = value.replace(".", "").replace(",", ".")
            return Decimal(str(value))

        if target_type == "float":
            if isinstance(value, str):
                if "," in value:
                    value = value.replace(".", "").replace(",", ".")
            return float(value)

        if target_type == "bool":
            if isinstance(value, bool):
                return value
            s = str(value).strip().lower()
            if s in _TRUE_VALUES:
                return True
            if s in _FALSE_VALUES:
                return False
            return CoercionFailure(value, "bool")

        if target_type in ("date", "datetime"):
            result = None
            if isinstance(value, (datetime, date)):
                result = value
            elif isinstance(value, (int, float)):
                # Número de série do Excel (tarefa 27)
                result = EXCEL_BASE_DATE + timedelta(days=value)
            elif isinstance(value, str):
                try:
                    result = datetime.fromisoformat(value)
                except ValueError:
                    pass

            if result:
                if target_type == "date" and isinstance(result, datetime):
                    return result.date()
                return result

            return CoercionFailure(value, target_type)

    except (ValueError, TypeError, InvalidOperation, OverflowError):
        return CoercionFailure(value, target_type)

    return CoercionFailure(value, target_type)


def coerce_row(values: dict[str, Any], config: MappingConfig) -> dict[str, Any]:
    """Aplica a coerção de tipos em todas as colunas da linha.

    :param values: valores já mapeados e limpos.
    :param config: configuração contendo os tipos por coluna.
    :return: dicionário onde os valores podem ser tipos Python ou instâncias
        de :class:`CoercionFailure`.
    """
    result = {}
    for column, value in values.items():
        target_type = config.types.get(column)
        if target_type:
            value = coerce_value(value, target_type)
        result[column] = value
    return result
