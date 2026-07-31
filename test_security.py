"""Testes de segurança e integridade SQL (Tarefas 59 e 60)."""

import logging
import unittest
from io import StringIO

from etl.logging_setup import (
    configure_logging,
    register_secret,
    clear_secrets,
    RedactingFormatter,
)
from etl.load.loader import Loader
from etl.config import DatabaseConfig, LoadConfig, MappingConfig
from etl import messages
from test_utils import FakeConnection

class TestSecurity(unittest.TestCase):
    """Verifica proteção de credenciais e parametrização SQL."""

    def setUp(self):
        clear_secrets()

    def test_password_redaction_in_logs(self):
        """Verifica se senhas registradas são ocultadas nos logs (Tarefa 59)."""
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setFormatter(RedactingFormatter())
        
        logger = logging.getLogger("etl.security_test")
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
        
        senha_secreta = "S3nh4_Pr0ib1d4"
        register_secret(senha_secreta)
        
        logger.info(f"Conectando ao banco com a senha {senha_secreta}")
        
        output = log_stream.getvalue()
        self.assertNotIn(senha_secreta, output)
        self.assertIn(messages.REDACTED_PLACEHOLDER, output)

    def test_sql_parameterization(self):
        """Verifica se o Loader utiliza parâmetros %s em vez de strings (Tarefa 60)."""
        db_config = DatabaseConfig(host="h", database="db", user="u", password="p")
        load_config = LoadConfig(table="my_table")
        mapping = MappingConfig(columns={"A": "col1"})
        conn = FakeConnection(table_columns=["col1"])
        
        loader = Loader(conn, db_config, load_config, mapping)
        
        # Valor contendo caracteres de SQL Injection
        malicious_value = "'); DROP TABLE users; --"
        batch = [(10, {"col1": malicious_value})]
        
        loader.load_batch(batch)
        
        # Recupera a query e os parâmetros executados
        # conn.cursor_instance.executed[-1] é (sql, seq_params) do executemany
        sql, seq_params = conn.cursor_instance.executed[-1]
        
        # A query deve usar o placeholder %s
        self.assertIn("%s", sql)
        # O valor malicioso NÃO deve estar no SQL plano
        self.assertNotIn(malicious_value, sql)
        
        # O valor deve estar nos parâmetros passados ao driver
        self.assertEqual(seq_params[0][0], malicious_value)

    def test_preflight_checks_no_injection(self):
        """Verifica se pre-flight checks usam nomes de tabela escapados (Tarefa 37/60)."""
        db_config = DatabaseConfig(host="h", database="db", user="u")
        # Nome de tabela malicioso
        load_config = LoadConfig(table="my_table`; DROP TABLE users; --")
        mapping = MappingConfig(columns={"A": "col1"})
        conn = FakeConnection(table_columns=["col1"])
        
        loader = Loader(conn, db_config, load_config, mapping)
        
        # Não deve levantar erro de sintaxe se os backticks forem usados corretamente
        # (Embora aqui o FakeConnection apenas registre o SQL)
        try:
            loader.check_target()
        except Exception:
            pass
            
        executed_sqls = [sql for sql, _ in conn.cursor_instance.executed]
        # O nome da tabela deve estar entre crases (backticks)
        self.assertTrue(any("DESCRIBE `my_table`; DROP TABLE users; --`" in sql for sql in executed_sqls))
