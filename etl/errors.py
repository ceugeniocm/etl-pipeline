"""Hierarquia de exceções do pipeline e códigos de saída (NFR-006, FR-012).

Toda falha prevista é sinalizada por uma subclasse de :class:`EtlError`, que
carrega uma mensagem em ``pt_BR`` (NFR-007) e o código de saída correspondente
(:attr:`EtlError.exit_code`), consumido pela CLI.

Os nomes das classes e dos atributos permanecem em ``en_US`` por serem strings
técnicas.
"""

from __future__ import annotations

__all__ = [
    "EXIT_SUCCESS",
    "EXIT_UNEXPECTED_ERROR",
    "EXIT_CONFIG_ERROR",
    "EXIT_EXTRACTION_ERROR",
    "EXIT_MAPPING_ERROR",
    "EXIT_VALIDATION_ERROR",
    "EXIT_REJECTION_THRESHOLD",
    "EXIT_DATABASE_CONNECTION_ERROR",
    "EXIT_LOAD_ERROR",
    "EXIT_NOT_IMPLEMENTED",
    "EtlError",
    "ConfigError",
    "ExtractionError",
    "MappingError",
    "ValidationError",
    "RejectionThresholdExceeded",
    "DatabaseConnectionError",
    "LoadError",
    "exit_code_for",
]

# --------------------------------------------------------------------------
# Códigos de saída (FR-012)
# --------------------------------------------------------------------------

#: Execução concluída com sucesso.
EXIT_SUCCESS = 0
#: Falha não prevista pela hierarquia de exceções.
EXIT_UNEXPECTED_ERROR = 1
#: Configuração ausente ou inválida.
EXIT_CONFIG_ERROR = 2
#: Falha ao abrir ou ler a planilha de origem.
EXIT_EXTRACTION_ERROR = 3
#: Colunas mapeadas ausentes ou mapeamento inválido.
EXIT_MAPPING_ERROR = 4
#: Falha estrutural de validação que impede a execução.
EXIT_VALIDATION_ERROR = 5
#: Limite configurado de registros rejeitados foi excedido.
EXIT_REJECTION_THRESHOLD = 6
#: Falha ao conectar ou reconectar ao banco de dados.
EXIT_DATABASE_CONNECTION_ERROR = 7
#: Falha durante a gravação dos dados.
EXIT_LOAD_ERROR = 8
#: Funcionalidade ainda não implementada.
EXIT_NOT_IMPLEMENTED = 70


# --------------------------------------------------------------------------
# Hierarquia de exceções
# --------------------------------------------------------------------------


class EtlError(Exception):
    """Erro base do pipeline, com mensagem em ``pt_BR`` e código de saída.

    :param message: texto já formatado, normalmente vindo de
        :mod:`etl.messages`.
    :param cause: exceção original que motivou esta falha, quando houver.
    """

    #: Código de saída associado a esta classe de erro.
    exit_code: int = EXIT_UNEXPECTED_ERROR

    def __init__(self, message: str, *, cause: BaseException | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.cause = cause

    def __str__(self) -> str:
        """Retorna a mensagem em ``pt_BR`` destinada ao usuário."""
        return self.message


class ConfigError(EtlError):
    """Configuração ausente, incompleta ou com valores inválidos (FR-011)."""

    exit_code = EXIT_CONFIG_ERROR


class ExtractionError(EtlError):
    """Falha ao localizar, abrir ou ler a planilha de origem (FR-001)."""

    exit_code = EXIT_EXTRACTION_ERROR


class MappingError(EtlError):
    """Mapeamento de colunas inválido ou incompatível com a origem (FR-003)."""

    exit_code = EXIT_MAPPING_ERROR


class ValidationError(EtlError):
    """Falha de validação que impede o prosseguimento da execução (FR-006).

    Rejeições de linhas individuais **não** usam esta exceção: elas são
    registradas como ocorrências no relatório de rejeições e a execução
    continua.
    """

    exit_code = EXIT_VALIDATION_ERROR


class RejectionThresholdExceeded(EtlError):
    """O limite configurado de registros rejeitados foi ultrapassado (FR-006)."""

    exit_code = EXIT_REJECTION_THRESHOLD


class DatabaseConnectionError(EtlError):
    """Falha ao conectar ou reconectar ao MySQL (FR-008).

    O nome evita colidir com a exceção nativa ``ConnectionError`` do Python.
    """

    exit_code = EXIT_DATABASE_CONNECTION_ERROR


class LoadError(EtlError):
    """Falha ao gravar dados na tabela de destino (FR-009, FR-010)."""

    exit_code = EXIT_LOAD_ERROR


def exit_code_for(error: BaseException) -> int:
    """Retorna o código de saída associado a ``error``.

    Erros fora da hierarquia :class:`EtlError` recebem
    :data:`EXIT_UNEXPECTED_ERROR`.
    """
    if isinstance(error, EtlError):
        return error.exit_code
    return EXIT_UNEXPECTED_ERROR
