"""Mapeamento de colunas de origem para destino (FR-003).

Este módulo é responsável por transformar os nomes das colunas conforme
definido na configuração e garantir que a origem possua todas as colunas
necessárias antes de iniciar a extração.
"""

from typing import Any

from etl import messages
from etl.config import MappingConfig
from etl.errors import MappingError
from etl.extract import SourceRow


def check_mapping(
    columns_in_header: tuple[str, ...], config: MappingConfig, sheet_name: str
) -> None:
    """Verifica se todas as colunas de origem mapeadas existem no cabeçalho.

    :raises MappingError: listando todas as colunas ausentes (FR-003).
    """
    missing = [source for source in config.columns if source not in columns_in_header]
    if missing:
        raise MappingError(
            messages.ERR_MAPPING_MISSING_COLUMNS.format(
                sheet=sheet_name, columns=", ".join(sorted(missing))
            )
        )


def apply_mapping(row: SourceRow, config: MappingConfig) -> dict[str, Any]:
    """Transforma os nomes das colunas de origem para os nomes de destino.

    Colunas de origem que não foram mapeadas são descartadas (FR-003).

    :param row: linha lida da planilha.
    :param config: configuração de mapeamento.
    :return: dicionário com as chaves sendo os nomes das colunas de destino.
    """
    return {
        target: row.values[source]
        for source, target in config.columns.items()
        if source in row.values
    }
