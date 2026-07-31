"""Configuração de log do pipeline e redação de credenciais (FR-013, NFR-004).

O módulo configura o logger do pacote ``etl`` com um handler de console e,
opcionalmente, um handler de arquivo, ambos com nível configurável.

Nenhuma credencial pode chegar à saída de log. A proteção é aplicada em duas
camadas:

1. :class:`RedactingFilter` atua sobre ``record.msg`` e ``record.args`` antes
   da formatação;
2. :class:`RedactingFormatter` atua sobre o texto final, cobrindo também
   ``exc_info`` (tracebacks) e ``stack_info``.

Valores conhecidos (por exemplo, a senha lida da configuração) devem ser
informados com :func:`register_secret`; padrões do tipo ``password=...`` e
credenciais embutidas em URIs são removidos automaticamente.
"""

from __future__ import annotations

import logging
import re
import sys
from typing import Any, IO

from etl import messages
from etl.errors import ConfigError

__all__ = [
    "PACKAGE_LOGGER_NAME",
    "DEFAULT_LOG_FORMAT",
    "DEFAULT_DATE_FORMAT",
    "DEFAULT_LOG_LEVEL",
    "RedactingFilter",
    "RedactingFormatter",
    "clear_secrets",
    "configure_logging",
    "get_logger",
    "redact",
    "register_secret",
    "resolve_level",
    "shutdown_logging",
]

#: Logger raiz do pacote; todos os módulos usam filhos deste logger.
PACKAGE_LOGGER_NAME = "etl"

DEFAULT_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_LOG_LEVEL = "INFO"

#: Chaves cujo valor é sempre suprimido quando aparece como ``chave=valor``.
_SECRET_KEYS = ("password", "passwd", "pwd", "senha", "secret", "token")

_KEY_VALUE_PATTERN = re.compile(
    r"(?i)\b(" + "|".join(_SECRET_KEYS) + r")\b(\s*[:=]\s*)"
    r"(\"[^\"]*\"|'[^']*'|[^\s,;)\]}]+)"
)

#: Credenciais embutidas em URI, por exemplo ``mysql://user:senha@host``.
_URI_CREDENTIALS_PATTERN = re.compile(
    r"(?i)([a-z][a-z0-9+.\-]*://[^:/@\s]+:)([^@\s]+)(@)"
)

#: Valores literais registrados em tempo de execução (senhas da configuração).
_secrets: set[str] = set()


# --------------------------------------------------------------------------
# Registro e remoção de credenciais
# --------------------------------------------------------------------------


def register_secret(value: object) -> None:
    """Registra um valor literal a ser suprimido de toda saída de log.

    Valores vazios ou não textuais são ignorados. O registro é global ao
    processo, pois qualquer módulo pode emitir log.
    """
    if isinstance(value, str) and value:
        _secrets.add(value)


def clear_secrets() -> None:
    """Remove todos os valores registrados por :func:`register_secret`."""
    _secrets.clear()


def redact(text: Any) -> Any:
    """Suprime credenciais de ``text``.

    Aplica, nesta ordem: os valores registrados em :func:`register_secret`,
    os padrões ``chave=valor`` para chaves sensíveis e as credenciais
    embutidas em URIs. Entradas que não sejam ``str`` são devolvidas sem
    alteração.
    """
    if not isinstance(text, str) or not text:
        return text

    placeholder = messages.REDACTED_PLACEHOLDER
    result = text
    # Os segredos mais longos primeiro, para não deixar sobras de um segredo
    # que contenha outro como prefixo.
    for secret in sorted(_secrets, key=len, reverse=True):
        if secret in result:
            result = result.replace(secret, placeholder)

    result = _KEY_VALUE_PATTERN.sub(
        lambda match: f"{match.group(1)}{match.group(2)}{placeholder}", result
    )
    result = _URI_CREDENTIALS_PATTERN.sub(
        lambda match: f"{match.group(1)}{placeholder}{match.group(3)}", result
    )
    return result


# --------------------------------------------------------------------------
# Filtro e formatador
# --------------------------------------------------------------------------


class RedactingFilter(logging.Filter):
    """Suprime credenciais da mensagem e dos argumentos do registro de log."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Reescreve ``record`` no lugar e sempre autoriza sua emissão."""
        record.msg = redact(record.msg)
        if isinstance(record.args, dict):
            record.args = {key: redact(value) for key, value in record.args.items()}
        elif isinstance(record.args, tuple):
            record.args = tuple(redact(value) for value in record.args)
        return True


class RedactingFormatter(logging.Formatter):
    """Formatador que suprime credenciais do texto final, inclusive tracebacks."""

    def format(self, record: logging.LogRecord) -> str:
        """Formata ``record`` e devolve o texto já sanitizado."""
        return redact(super().format(record))


# --------------------------------------------------------------------------
# Configuração
# --------------------------------------------------------------------------


def resolve_level(level: int | str | None, *, key: str = "log_level") -> int:
    """Converte ``level`` em um nível numérico do módulo ``logging``.

    :param level: nome do nível (``"DEBUG"``), valor numérico ou ``None``
        para :data:`DEFAULT_LOG_LEVEL`.
    :param key: chave de configuração citada na mensagem de erro.
    :raises ConfigError: se o nível não for reconhecido.
    """
    if level is None:
        return logging.getLevelNamesMapping()[DEFAULT_LOG_LEVEL]
    if not isinstance(level, bool) and isinstance(level, int):
        return level
    if not isinstance(level, bool) and isinstance(level, str):
        resolved = logging.getLevelNamesMapping().get(level.strip().upper())
        if resolved is not None:
            return resolved
    raise ConfigError(
        messages.ERR_CONFIG_INVALID_VALUE.format(
            key=key, reason=f"nível de log inválido: {level!r}"
        )
    )


def configure_logging(
    level: int | str | None = DEFAULT_LOG_LEVEL,
    log_file: str | None = None,
    *,
    stream: IO[str] | None = None,
    fmt: str = DEFAULT_LOG_FORMAT,
    datefmt: str = DEFAULT_DATE_FORMAT,
) -> logging.Logger:
    """Configura e devolve o logger do pacote ``etl``.

    Chamadas sucessivas substituem os handlers instalados anteriormente, de
    modo que a função é idempotente e não duplica saídas.

    :param level: nível de log como nome (``"DEBUG"``) ou valor numérico.
    :param log_file: caminho de um arquivo de log adicional ao console
        (FR-013); ``None`` desativa a saída em arquivo.
    :param stream: fluxo de console; o padrão é ``sys.stderr``.
    :param fmt: formato das linhas de log.
    :param datefmt: formato do carimbo de data e hora.
    :raises ConfigError: se ``level`` for inválido ou o arquivo de log não
        puder ser aberto.
    """
    resolved_level = resolve_level(level)

    logger = logging.getLogger(PACKAGE_LOGGER_NAME)
    shutdown_logging()
    logger.setLevel(resolved_level)
    # A saída do pacote é autocontida: não repassa para o logger raiz, cujos
    # handlers não aplicam a redação de credenciais.
    logger.propagate = False
    logger.addFilter(RedactingFilter())

    formatter = RedactingFormatter(fmt=fmt, datefmt=datefmt)

    console_handler = logging.StreamHandler(
        stream if stream is not None else sys.stderr
    )
    console_handler.setLevel(resolved_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if log_file:
        try:
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
        except OSError as error:
            raise ConfigError(
                messages.ERR_CONFIG_INVALID_VALUE.format(
                    key="log_file",
                    reason=f"não foi possível abrir o arquivo de log '{log_file}'",
                ),
                cause=error,
            ) from error
        file_handler.setLevel(resolved_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def shutdown_logging() -> None:
    """Fecha e remove os handlers e filtros instalados no logger do pacote."""
    logger = logging.getLogger(PACKAGE_LOGGER_NAME)
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
    for log_filter in list(logger.filters):
        logger.removeFilter(log_filter)


def get_logger(name: str | None = None) -> logging.Logger:
    """Devolve o logger do pacote ou um de seus filhos.

    :param name: nome completo do módulo (``__name__``) ou sufixo; qualquer
        nome fora do pacote é reposicionado sob ``etl``.
    """
    if not name or name == PACKAGE_LOGGER_NAME:
        return logging.getLogger(PACKAGE_LOGGER_NAME)
    if name.startswith(f"{PACKAGE_LOGGER_NAME}."):
        return logging.getLogger(name)
    return logging.getLogger(f"{PACKAGE_LOGGER_NAME}.{name}")
