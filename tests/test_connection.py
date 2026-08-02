"""Testes da conexão com o banco de dados (tarefa 45).

Cobre retentativas, backoff exponencial e tratamento de erros de conexão
(FR-008, NFR-004).
"""

import unittest
from unittest.mock import MagicMock, patch

import mysql.connector

from etl.config import DatabaseConfig
from etl.errors import DatabaseConnectionError
from etl.load.connection import get_connection


class TestConnection(unittest.TestCase):
    """Testes da fábrica de conexões e política de retentativas."""

    def setUp(self):
        self.config = DatabaseConfig(
            host="mysql.exemplo.com",
            database="prod_db",
            user="etl_user",
            password="secret_password",
            port=3306,
            connect_retries=2,
            retry_backoff_seconds=0.01,
        )

    @patch("mysql.connector.connect")
    def test_get_connection_success(self, mock_connect):
        """Conecta com sucesso na primeira tentativa."""
        mock_conn = MagicMock()
        mock_conn.is_connected.return_value = True
        mock_connect.return_value = mock_conn

        conn = get_connection(self.config)

        self.assertEqual(conn, mock_conn)
        mock_connect.assert_called_once_with(
            host="mysql.exemplo.com",
            port=3306,
            user="etl_user",
            password="secret_password",
            database="prod_db",
            connect_timeout=10,
            compress=True,
        )

    @patch("mysql.connector.connect")
    @patch("time.sleep")
    def test_get_connection_retry_then_success(self, mock_sleep, mock_connect):
        """Conecta após uma falha inicial."""
        mock_conn = MagicMock()
        mock_conn.is_connected.return_value = True
        mock_connect.side_effect = [mysql.connector.Error("Temporário"), mock_conn]

        conn = get_connection(self.config)

        self.assertEqual(conn, mock_conn)
        self.assertEqual(mock_connect.call_count, 2)
        mock_sleep.assert_called_once_with(0.01)

    @patch("mysql.connector.connect")
    @patch("time.sleep")
    def test_get_connection_exhaust_retries(self, mock_sleep, mock_connect):
        """Falha após esgotar todas as tentativas configuradas."""
        mock_connect.side_effect = mysql.connector.Error("Falha Crítica")

        with self.assertRaises(DatabaseConnectionError) as context:
            get_connection(self.config)

        # Mensagem não deve conter a senha (NFR-004)
        self.assertIn("mysql.exemplo.com", str(context.exception))
        self.assertIn("etl_user", str(context.exception))
        self.assertNotIn("secret_password", str(context.exception))
        
        # 1 tentativa inicial + 2 retentativas = 3 chamadas
        self.assertEqual(mock_connect.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)

    @patch("mysql.connector.connect")
    @patch("time.sleep")
    def test_exponential_backoff(self, mock_sleep, mock_connect):
        """Verifica se o tempo de espera dobra a cada tentativa."""
        self.config = DatabaseConfig(
            host="h", database="d", user="u", connect_retries=3, retry_backoff_seconds=1.0
        )
        mock_connect.side_effect = mysql.connector.Error("Erro")

        with self.assertRaises(DatabaseConnectionError):
            get_connection(self.config)

        # Esperas: 1.0s, 2.0s, 4.0s
        self.assertEqual(mock_sleep.call_count, 3)
        calls = [c.args[0] for c in mock_sleep.call_args_list]
        self.assertEqual(calls, [1.0, 2.0, 4.0])
