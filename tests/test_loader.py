"""Testes da carga de dados (tarefas 44 e 45).

Cobre pre-flight checks, batching, commit/rollback e modos de carga
(FR-008 a FR-010, FR-015).
"""

import unittest
from typing import Any

import mysql.connector
from mysql.connector import errorcode

from etl.config import DatabaseConfig, LoadConfig, MappingConfig
from etl.errors import DatabaseConnectionError, LoadError
from etl.load.loader import Loader


class FakeCursor:
    """Dublê de teste para o cursor do MySQL (tarefa 44)."""

    def __init__(self, table_columns: list[str] = None):
        self.executed: list[tuple[str, Any]] = []
        self.table_columns = table_columns or []
        self._results = []

    def execute(self, sql: str, params: Any = None):
        self.executed.append((sql, params))
        if "DESCRIBE" in sql:
            self._results = [[col] for col in self.table_columns]

    def executemany(self, sql: str, seq_params: Any):
        self.executed.append((sql, seq_params))

    def fetchall(self) -> list[Any]:
        return self._results

    def close(self):
        pass


class FakeConnection:
    """Dublê de teste para a conexão do MySQL (tarefa 44)."""

    def __init__(self, table_columns: list[str] = None):
        self.cursor_instance = FakeCursor(table_columns)
        self.committed = 0
        self.rolled_back = 0
        self.closed = False

    def cursor(self, **kwargs):
        return self.cursor_instance

    def commit(self):
        self.committed += 1

    def rollback(self):
        self.rolled_back += 1

    def close(self):
        self.closed = True

    def is_connected(self):
        return True


class TestLoader(unittest.TestCase):
    """Testes da lógica de carga e persistência."""

    def setUp(self):
        self.db_config = DatabaseConfig(host="h", database="db", user="u")
        self.mapping_config = MappingConfig(columns={"A": "col1", "B": "col2"})
        self.load_config = LoadConfig(table="my_table", mode="append", batch_size=2)
        self.conn = FakeConnection(table_columns=["col1", "col2"])
        self.loader = Loader(
            self.conn, self.db_config, self.load_config, self.mapping_config
        )

    def test_check_target_success(self):
        """Passa se a tabela e as colunas existem."""
        self.loader.check_target()
        executed_sqls = [sql for sql, _ in self.conn.cursor_instance.executed]
        self.assertTrue(any("DESCRIBE `my_table`" in sql for sql in executed_sqls))

    def test_check_target_missing_table(self):
        """Erro se a tabela não for encontrada."""

        def fail_describe(sql, params=None):
            if "DESCRIBE" in sql:
                raise mysql.connector.Error(errno=errorcode.ER_NO_SUCH_TABLE)

        self.conn.cursor_instance.execute = fail_describe

        with self.assertRaises(LoadError) as context:
            self.loader.check_target()
        self.assertIn("não existe na base", str(context.exception))

    def test_check_target_missing_columns(self):
        """Erro se colunas mapeadas não existirem na tabela."""
        self.conn.cursor_instance.table_columns = ["col1"]  # col2 faltando
        with self.assertRaises(LoadError) as context:
            self.loader.check_target()
        self.assertIn("col2", str(context.exception))

    def test_prepare_truncate(self):
        """Executa TRUNCATE no modo apropriado."""
        self.load_config = LoadConfig(table="my_table", mode="truncate")
        self.loader = Loader(
            self.conn, self.db_config, self.load_config, self.mapping_config
        )

        self.loader.prepare()

        executed = [sql for sql, _ in self.conn.cursor_instance.executed]
        self.assertTrue(any("TRUNCATE TABLE `my_table`" in sql for sql in executed))
        self.assertEqual(self.conn.committed, 1)

    def test_load_batch_success(self):
        """Carrega um lote com sucesso e faz commit."""
        batch = [(1, {"col1": "v1", "col2": "v2"}), (2, {"col1": "v3", "col2": "v4"})]

        loaded, failed = self.loader.load_batch(batch)

        self.assertEqual(loaded, 2)
        self.assertEqual(failed, 0)
        self.assertEqual(self.conn.committed, 1)

        # Verifica se usou executemany
        found_executemany = False
        for sql, params in self.conn.cursor_instance.executed:
            if "INSERT INTO `my_table`" in sql and isinstance(params, list):
                found_executemany = True
                self.assertEqual(len(params), 2)
        self.assertTrue(found_executemany)

    def test_load_batch_failure_isolate(self):
        """Lote falha e entra em modo isolamento (linha a linha)."""

        def fail_executemany(sql, seq_params):
            raise mysql.connector.Error("Erro no lote")

        self.conn.cursor_instance.executemany = fail_executemany
        batch = [(1, {"col1": "v1", "col2": "v2"}), (2, {"col1": "v3", "col2": "v4"})]

        loaded, failed = self.loader.load_batch(batch)

        self.assertEqual(loaded, 2)
        self.assertEqual(failed, 0)
        # 1 rollback do lote + 2 commits individuais
        self.assertEqual(self.conn.rolled_back, 1)
        self.assertEqual(self.conn.committed, 2)

    def test_load_batch_failure_row_fails_in_isolate(self):
        """Linha falha mesmo no modo isolamento."""

        def fail_all(sql, params=None):
            raise mysql.connector.Error("Erro total")

        self.conn.cursor_instance.executemany = fail_all
        self.conn.cursor_instance.execute = fail_all

        batch = [(1, {"col1": "v1"})]
        loaded, failed = self.loader.load_batch(batch)

        self.assertEqual(loaded, 0)
        self.assertEqual(failed, 1)
        self.assertEqual(self.conn.rolled_back, 2)  # Um do lote, um da linha

    def test_load_batch_failure_abort(self):
        """Lote falha e aborta a execução conforme configuração."""
        self.load_config = LoadConfig(table="t", on_batch_error="abort")
        self.loader = Loader(
            self.conn, self.db_config, self.load_config, self.mapping_config
        )

        def fail_executemany(sql, seq_params):
            raise mysql.connector.Error("Erro Fatal")

        self.conn.cursor_instance.executemany = fail_executemany

        with self.assertRaises(LoadError):
            self.loader.load_batch([(1, {"col1": "v1"})])
        self.assertEqual(self.conn.rolled_back, 1)

    def test_upsert_sql_generation(self):
        """Gera SQL com ON DUPLICATE KEY UPDATE."""
        self.load_config = LoadConfig(table="t", mode="upsert", unique_key=("col1",))
        self.loader = Loader(
            self.conn, self.db_config, self.load_config, self.mapping_config
        )

        sql = self.loader._get_insert_sql()
        self.assertIn("ON DUPLICATE KEY UPDATE", sql)
        self.assertIn("`col2` = VALUES(`col2`)", sql)
        self.assertNotIn("`col1` = VALUES(`col1`)", sql)
