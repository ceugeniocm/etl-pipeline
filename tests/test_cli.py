"""Testes da interface de linha de comando (tarefa 54)."""

import json
import os
import unittest
from unittest.mock import MagicMock, patch

from etl.cli import main
from etl.errors import EXIT_CONFIG_ERROR, EXIT_SUCCESS, EXIT_EXTRACTION_ERROR


class TestCli(unittest.TestCase):
    """Testes de argumentos, sobreposições e códigos de saída."""

    def setUp(self):
        self.config_path = "test_config.json"
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump({
                "source": {"path": "src.xlsx"},
                "mapping": {
                    "columns": {"A": "col1"}
                },
                "database": {"host": "h", "database": "d", "user": "u"},
                "load": {"table": "t"}
            }, f)

    def tearDown(self):
        if os.path.exists(self.config_path):
            os.remove(self.config_path)

    @patch("etl.cli.Pipeline")
    def test_cli_success(self, mock_pipeline_cls):
        """Execução básica com sucesso."""
        mock_pipeline = mock_pipeline_cls.return_value
        mock_pipeline.run.return_value = True

        exit_code = main([self.config_path])

        self.assertEqual(exit_code, EXIT_SUCCESS)
        mock_pipeline_cls.assert_called_once()
        # Verifica se o config foi carregado
        config = mock_pipeline_cls.call_args[0][0]
        self.assertEqual(config.source.path, "src.xlsx")

    @patch("etl.cli.Pipeline")
    def test_cli_overrides(self, mock_pipeline_cls):
        """Verifica se os argumentos da CLI sobrepõem o arquivo."""
        mock_pipeline = mock_pipeline_cls.return_value
        mock_pipeline.run.return_value = True

        main([
            self.config_path,
            "--source", "overridden.xlsx",
            "--table", "new_table",
            "--chunk-size", "100",
            "--dry-run"
        ])

        config = mock_pipeline_cls.call_args[0][0]
        self.assertEqual(config.source.path, "overridden.xlsx")
        self.assertEqual(config.load.table, "new_table")
        self.assertEqual(config.source.chunk_size, 100)
        self.assertTrue(config.run.dry_run)

    @patch("etl.cli.Pipeline")
    def test_cli_verbose(self, mock_pipeline_cls):
        """Verifica se --verbose ativa o nível DEBUG."""
        mock_pipeline = mock_pipeline_cls.return_value
        mock_pipeline.run.return_value = True

        main([self.config_path, "--verbose"])

        config = mock_pipeline_cls.call_args[0][0]
        self.assertEqual(config.run.log_level, "DEBUG")

    def test_cli_config_error(self):
        """Arquivo de configuração inexistente deve retornar erro de config."""
        exit_code = main(["non_existent.json"])
        self.assertEqual(exit_code, EXIT_CONFIG_ERROR)

    @patch("etl.cli.Pipeline")
    def test_cli_pipeline_error(self, mock_pipeline_cls):
        """Exceções do pipeline devem ser mapeadas para códigos de saída."""
        from etl.errors import ExtractionError
        mock_pipeline = mock_pipeline_cls.return_value
        mock_pipeline.run.side_effect = ExtractionError("Falha na extração")

        exit_code = main([self.config_path])

        self.assertEqual(exit_code, EXIT_EXTRACTION_ERROR)
