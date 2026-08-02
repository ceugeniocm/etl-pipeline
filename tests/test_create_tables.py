import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
from etl.load.connection import execute_sql_script
from etl.pipeline import Pipeline
from etl.config import EtlConfig, DatabaseConfig, RunConfig, SourceConfig, MappingConfig, LoadConfig, ValidationConfig
from test_utils import FakeConnection

class TestCreateTables(unittest.TestCase):
    def test_execute_sql_script_success(self):
        conn = FakeConnection()
        cursor = conn.cursor()
        # Mock execute e nextset
        cursor.execute = MagicMock()
        cursor.nextset = MagicMock(side_effect=[True, False])
        
        script_path = "dummy.sql"
        script_content = "CREATE TABLE t1; CREATE TABLE t2;"
        
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=script_content)):
                execute_sql_script(conn, script_path)
        
        cursor.execute.assert_called_once_with(script_content)
        self.assertEqual(conn.committed, 1)

    def test_execute_sql_script_file_not_found(self):
        conn = FakeConnection()
        with patch("os.path.exists", return_value=False):
            with patch("etl.load.connection.logger") as mock_logger:
                execute_sql_script(conn, "non_existent.sql")
                mock_logger.warning.assert_called()

    @patch("etl.pipeline.get_connection")
    @patch("etl.pipeline.execute_sql_script")
    @patch("etl.pipeline.open_source")
    @patch("etl.pipeline.check_mapping")
    def test_pipeline_calls_create_tables(self, mock_check, mock_open_src, mock_execute_sql, mock_get_conn):
        config = EtlConfig(
            database=DatabaseConfig(host="h", database="db", user="u"),
            run=RunConfig(dry_run=False, rejection_report="rejeicoes.csv"),
            source=SourceConfig(path="p.xlsx"),
            mapping=MappingConfig(columns={"a": "b"}),
            load=LoadConfig(table="t"),
            validation=ValidationConfig()
        )
        
        # O Loader verifica se as colunas existem. Fornecemos as colunas esperadas no alvo.
        conn = FakeConnection(table_columns=["b"])
        mock_get_conn.return_value = conn
        
        # Mock open_source context manager
        mock_sheet = MagicMock()
        mock_sheet.rows.return_value = iter([])
        mock_open_src.return_value.__enter__.return_value = mock_sheet
        
        pipeline = Pipeline(config)
        pipeline.run()
        
        mock_execute_sql.assert_called_once_with(conn, "create_tables.sql")

if __name__ == "__main__":
    unittest.main()
