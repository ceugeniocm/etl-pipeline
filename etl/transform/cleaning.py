"""Limpeza e normalização de strings (FR-004).

Este módulo remove espaços em branco, converte textos vazios em ``None`` e
aplica transformações como maiúsculas/minúsculas e remoção de pontuação,
conforme configurado para cada coluna.
"""

import re
import string
from collections.abc import Mapping
from typing import Any, Callable

from etl.config import MappingConfig

#: Funções de normalização disponíveis.
NORMALIZERS: Mapping[str, Callable[[str], str]] = {
    "trim": lambda v: v.strip(),
    "upper": lambda v: v.upper(),
    "lower": lambda v: v.lower(),
    "strip_punctuation": lambda v: v.translate(
        str.maketrans("", "", string.punctuation)
    ),
    "collapse_spaces": lambda v: " ".join(v.split()),
}


def clean_row(values: dict[str, Any], config: MappingConfig) -> dict[str, Any]:
    """Aplica as regras de limpeza e normalização em toda a linha.

    Para cada valor do tipo texto:
    1. Remove espaços em branco nas extremidades (FR-004).
    2. Converte textos vazios ou compostos apenas por espaços em ``None`` (FR-004).
    3. Aplica os normalizadores configurados para a coluna (FR-004).

    :param values: valores da linha indexados pelo nome da coluna de destino.
    :param config: configuração contendo os normalizadores por coluna.
    :return: novo dicionário com os valores limpos.
    """
    result = {}
    for column, value in values.items():
        if isinstance(value, str):
            # Limpeza básica (tarefa 24)
            value = value.strip()
            if not value:
                value = None

            # Normalizadores específicos (tarefa 25)
            if value is not None and column in config.normalizers:
                for name in config.normalizers[column]:
                    # O valor pode se tornar None durante a normalização
                    if value is None:
                        break
                    # O nome já foi validados em etl.config._parse_mapping
                    normalizer = NORMALIZERS[name]
                    value = normalizer(str(value)).strip()
                    if not value:
                        value = None

        result[column] = value
    return result
