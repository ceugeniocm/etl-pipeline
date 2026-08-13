"""Fábrica de conexões MySQL e gerenciamento de retentativas (FR-008).

Este módulo centraliza a criação de conexões com o MySQL, garantindo que
falhas sejam tratadas com retentativas configuráveis e que credenciais
nunca vazem nas mensagens de erro.
"""

import logging
import os
import time
from typing import Any, Protocol, runtime_checkable

import mysql.connector
from mysql.connector import errorcode

from etl import messages
from etl.config import DatabaseConfig
from etl.errors import DatabaseConnectionError

logger = logging.getLogger(__name__)


@runtime_checkable
class Cursor(Protocol):
    """Interface mínima para um cursor de banco de dados (NFR-005)."""

    def execute(self, operation: str, params: Any = None) -> Any:
        ...

    def executemany(self, operation: str, seq_params: Any) -> Any:
        ...

    def fetchall(self) -> list[Any]:
        ...

    def fetchone(self) -> Any:
        ...

    def nextset(self) -> bool | None:
        ...

    def close(self) -> None:
        ...


@runtime_checkable
class Connection(Protocol):
    """Interface mínima para uma conexão de banco de dados (NFR-005)."""

    def cursor(self, **kwargs: Any) -> Cursor:
        ...

    def commit(self) -> None:
        ...

    def rollback(self) -> None:
        ...

    def close(self) -> None:
        ...

    def is_connected(self) -> bool:
        ...

    def ping(self, **kwargs: Any) -> None:
        ...


def get_connection(config: DatabaseConfig) -> Connection:
    """Cria uma conexão com o MySQL aplicando retentativas (FR-008).

    :param config: configuração de banco de dados.
    :return: uma conexão ativa.
    :raises DatabaseConnectionError: se falhar após todas as tentativas.
    """
    attempts = config.connect_retries + 1
    delay = config.retry_backoff_seconds

    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            conn = mysql.connector.connect(
                host=config.host,
                port=config.port,
                user=config.user,
                password=config.password,
                database=config.database,
                connect_timeout=10,
                compress=True,
            )
            # No mysql-connector, se connect() não lançar exceção, a conexão está aberta.
            # Mas ping() ou is_connected() garantem que está ativa.
            if conn.is_connected():
                return conn
        except (mysql.connector.Error, IOError) as err:
            last_error = err
            if attempt < attempts:
                logger.warning(
                    messages.ERR_DB_RETRY.format(
                        attempt=attempt, total=config.connect_retries, delay=delay
                    )
                )
                time.sleep(delay)
                delay *= 2  # Backoff exponencial (Task 36)
            else:
                break

    # Se chegou aqui, falhou (Task 35)
    raise DatabaseConnectionError(
        messages.ERR_DB_CONNECTION_FAILED.format(
            host=config.host,
            port=config.port,
            database=config.database,
            user=config.user,
        ),
        cause=last_error,
    )


def execute_sql_script(conn: Connection, script_path: str) -> None:
    """Executa um script SQL a partir de um arquivo (Tarefa adicionada).

    :param conn: conexão ativa com o banco.
    :param script_path: caminho para o arquivo .sql.
    """
    if not os.path.exists(script_path):
        logger.warning(f"Script SQL não encontrado: {script_path}")
        return

    logger.info(f"Executando script SQL: {script_path}")
    try:
        with open(script_path, "r", encoding="utf-8") as f:
            content = f.read()

        cursor = conn.cursor()
        # Executa múltiplos statements separadamente para evitar problemas de timeout/protocolo
        statements = [s.strip() for s in content.split(";") if s.strip()]
        for statement in statements:
            cursor.execute(statement)
            while cursor.nextset():
                pass
        cursor.close()
        conn.commit()
    except Exception as e:
        logger.error(f"Erro ao executar script SQL {script_path}: {e}")
        # Não relançamos para não interromper o pipeline se as tabelas já existirem
        # ou se houver um erro menor, mas no nosso caso o script usa IF NOT EXISTS.
        # No entanto, se o requisito for "deve ser realizado", talvez devêssemos relançar.
        # Dada a descrição, parece ser uma etapa de preparação.
        raise DatabaseConnectionError(f"Falha ao preparar banco de dados com {script_path}", cause=e)
