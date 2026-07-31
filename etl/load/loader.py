"""Carga de dados no MySQL com suporte a lotes e diferentes modos (FR-009, FR-010).

Este módulo implementa a gravação dos registros transformados, lidando com
transações, erros de lote (isolamento de linhas) e os modos de inserção:
append, truncate e upsert.
"""

import logging
from typing import Any

import mysql.connector
from mysql.connector import errorcode

from etl import messages
from etl.config import DatabaseConfig, LoadConfig, MappingConfig
from etl.errors import DatabaseConnectionError, LoadError
from etl.load.connection import Connection

logger = logging.getLogger(__name__)


class Loader:
    """Gerencia a persistência dos dados no MySQL (tarefa 38)."""

    def __init__(
        self,
        conn: Connection,
        db_config: DatabaseConfig,
        load_config: LoadConfig,
        mapping_config: MappingConfig,
    ) -> None:
        self._conn = conn
        self._db_config = db_config
        self._load_config = load_config
        self._mapping_config = mapping_config
        self._table = load_config.table
        self._columns = mapping_config.target_columns

    def check_target(self) -> None:
        """Verifica se a tabela e todas as colunas mapeadas existem (FR-010, tarefa 37)."""
        cursor = self._conn.cursor()
        try:
            # DESCRIBE é eficiente para obter os nomes das colunas no MySQL
            cursor.execute(f"DESCRIBE `{self._table}`")
            existing_columns = {row[0] for row in cursor.fetchall()}
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_NO_SUCH_TABLE:
                raise LoadError(
                    messages.ERR_DB_TABLE_NOT_FOUND.format(
                        table=self._table, database=self._db_config.database
                    ),
                    cause=err,
                )
            raise DatabaseConnectionError(messages.ERR_DB_CONNECTION_LOST, cause=err)
        finally:
            cursor.close()

        missing = [col for col in self._columns if col not in existing_columns]
        if missing:
            raise LoadError(
                messages.ERR_DB_COLUMNS_NOT_FOUND.format(
                    table=self._table, columns=", ".join(sorted(missing))
                )
            )

    def prepare(self) -> None:
        """Executa ações prévias à carga, como o truncate (FR-010, tarefa 42)."""
        if self._load_config.mode == "truncate":
            logger.info(messages.INFO_TRUNCATING_TABLE.format(table=self._table))
            cursor = self._conn.cursor()
            try:
                # TRUNCATE no MySQL causa commit implícito
                cursor.execute(f"TRUNCATE TABLE `{self._table}`")
                self._conn.commit()
            except mysql.connector.Error as err:
                self._conn.rollback()
                raise DatabaseConnectionError(messages.ERR_DB_CONNECTION_LOST, cause=err)
            finally:
                cursor.close()

    def load_batch(
        self, batch_data: list[tuple[int, dict[str, Any]]]
    ) -> tuple[int, int]:
        """Grava um lote de registros no banco (FR-009, tarefa 38).

        :param batch_data: lista de tuplas (número_da_linha, valores).
        :return: tupla com (quantidade_carregada, quantidade_falhada).
        """
        if not batch_data:
            return 0, 0

        sql = self._get_insert_sql()
        rows_to_insert = [
            tuple(values.get(col) for col in self._columns)
            for _, values in batch_data
        ]

        cursor = self._conn.cursor()
        try:
            # Parameterized executemany (Task 38)
            cursor.executemany(sql, rows_to_insert)
            self._conn.commit()  # Commit após sucesso do lote (Task 39)
            return len(batch_data), 0
        except mysql.connector.Error as err:
            self._conn.rollback()
            if self._load_config.on_batch_error == "abort":
                first_row = batch_data[0][0]
                raise LoadError(
                    messages.ERR_LOAD_BATCH_FAILED.format(
                        first_row=first_row, size=len(batch_data), reason=str(err)
                    ),
                    cause=err,
                )

            # Modo isolate: tenta linha a linha (Task 40)
            logger.warning(
                messages.ERR_LOAD_BATCH_FAILED.format(
                    first_row=batch_data[0][0], size=len(batch_data), reason=str(err)
                )
            )
            return self._load_row_by_row(batch_data)
        finally:
            cursor.close()

    def _load_row_by_row(
        self, batch_data: list[tuple[int, dict[str, Any]]]
    ) -> tuple[int, int]:
        """Tenta inserir cada linha individualmente após falha do lote (tarefa 40)."""
        loaded = 0
        failed = 0
        sql = self._get_insert_sql()
        cursor = self._conn.cursor()
        for row_number, values in batch_data:
            data = tuple(values.get(col) for col in self._columns)
            try:
                cursor.execute(sql, data)
                self._conn.commit()
                loaded += 1
            except mysql.connector.Error as err:
                self._conn.rollback()
                failed += 1
                logger.error(
                    messages.ERR_LOAD_ROW_FAILED.format(row=row_number, reason=str(err))
                )
        return loaded, failed

    def _get_insert_sql(self) -> str:
        """Gera o comando SQL de inserção conforme o modo (tarefas 41, 43)."""
        cols_str = ", ".join(f"`{col}`" for col in self._columns)
        placeholders = ", ".join(["%s"] * len(self._columns))
        
        base_sql = f"INSERT INTO `{self._table}` ({cols_str}) VALUES ({placeholders})"

        if self._load_config.mode == "upsert":
            # ON DUPLICATE KEY UPDATE (Task 43)
            # Atualiza todas as colunas que não fazem parte da chave única
            update_parts = []
            unique_key = set(self._load_config.unique_key)
            for col in self._columns:
                if col not in unique_key:
                    update_parts.append(f"`{col}` = VALUES(`{col}`)")
            
            if update_parts:
                base_sql += " ON DUPLICATE KEY UPDATE " + ", ".join(update_parts)
        
        return base_sql
