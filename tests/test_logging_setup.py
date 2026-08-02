"""Testes da configuração de log e da redação de credenciais.

Cobre a tarefa 8 de ``docs/tasks.md`` (FR-013, NFR-004, NFR-005).
"""

import io
import logging
import os
import tempfile
import unittest

from etl import logging_setup, messages
from etl.errors import ConfigError

PLACEHOLDER = messages.REDACTED_PLACEHOLDER


class LoggingSetupTestCase(unittest.TestCase):
    """Base que isola o estado global de log entre os testes."""

    def setUp(self):
        logging_setup.clear_secrets()
        logging_setup.shutdown_logging()
        self.stream = io.StringIO()

    def tearDown(self):
        logging_setup.shutdown_logging()
        logging_setup.clear_secrets()

    def configure(self, level="DEBUG", log_file=None):
        """Configura o log escrevendo o console em um buffer de memória."""
        return logging_setup.configure_logging(
            level=level, log_file=log_file, stream=self.stream
        )

    def console_output(self):
        """Devolve tudo o que foi escrito no console até o momento."""
        for handler in logging.getLogger(logging_setup.PACKAGE_LOGGER_NAME).handlers:
            handler.flush()
        return self.stream.getvalue()


class TestLevelHandling(LoggingSetupTestCase):
    """Nível de log configurável (FR-013)."""

    def test_accepts_level_name(self):
        logger = self.configure(level="WARNING")
        self.assertEqual(logging.WARNING, logger.level)

    def test_level_name_is_case_insensitive(self):
        logger = self.configure(level="warning")
        self.assertEqual(logging.WARNING, logger.level)

    def test_accepts_numeric_level(self):
        logger = self.configure(level=logging.ERROR)
        self.assertEqual(logging.ERROR, logger.level)

    def test_none_falls_back_to_default_level(self):
        logger = self.configure(level=None)
        expected = logging.getLevelNamesMapping()[logging_setup.DEFAULT_LOG_LEVEL]
        self.assertEqual(expected, logger.level)

    def test_invalid_level_raises_config_error(self):
        with self.assertRaises(ConfigError) as context:
            self.configure(level="VERBOSO")
        self.assertIn("log_level", str(context.exception))

    def test_boolean_level_raises_config_error(self):
        with self.assertRaises(ConfigError):
            self.configure(level=True)

    def test_messages_below_level_are_suppressed(self):
        self.configure(level="WARNING")
        logger = logging_setup.get_logger(__name__)
        logger.info("mensagem informativa")
        logger.warning("mensagem de alerta")
        output = self.console_output()
        self.assertNotIn("mensagem informativa", output)
        self.assertIn("mensagem de alerta", output)


class TestHandlers(LoggingSetupTestCase):
    """Saída em console e em arquivo (FR-013)."""

    def test_console_handler_receives_records(self):
        self.configure()
        logging_setup.get_logger(__name__).info("linha de teste")
        self.assertIn("linha de teste", self.console_output())

    def test_writes_to_log_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "../etl.log")
            self.configure(log_file=path)
            logging_setup.get_logger(__name__).info("gravado em arquivo")
            logging_setup.shutdown_logging()
            with open(path, encoding="utf-8") as handle:
                content = handle.read()
        self.assertIn("gravado em arquivo", content)

    def test_log_file_receives_the_same_record_as_the_console(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "../etl.log")
            self.configure(log_file=path)
            logging_setup.get_logger(__name__).warning("duplo destino")
            console = self.console_output()
            logging_setup.shutdown_logging()
            with open(path, encoding="utf-8") as handle:
                content = handle.read()
        self.assertIn("duplo destino", console)
        self.assertIn("duplo destino", content)

    def test_unwritable_log_file_raises_config_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "inexistente", "etl.log")
            with self.assertRaises(ConfigError) as context:
                self.configure(log_file=path)
        self.assertIn("log_file", str(context.exception))

    def test_reconfiguration_does_not_duplicate_handlers(self):
        self.configure()
        first = len(logging.getLogger(logging_setup.PACKAGE_LOGGER_NAME).handlers)
        self.configure()
        second = len(logging.getLogger(logging_setup.PACKAGE_LOGGER_NAME).handlers)
        self.assertEqual(first, second)

    def test_reconfiguration_does_not_duplicate_filters(self):
        self.configure()
        self.configure()
        logger = logging.getLogger(logging_setup.PACKAGE_LOGGER_NAME)
        self.assertEqual(1, len(logger.filters))

    def test_record_is_emitted_only_once(self):
        self.configure()
        self.configure()
        logging_setup.get_logger(__name__).info("única")
        self.assertEqual(1, self.console_output().count("única"))

    def test_package_logger_does_not_propagate(self):
        logger = self.configure()
        self.assertFalse(logger.propagate)

    def test_shutdown_removes_handlers_and_filters(self):
        self.configure()
        logging_setup.shutdown_logging()
        logger = logging.getLogger(logging_setup.PACKAGE_LOGGER_NAME)
        self.assertEqual([], logger.handlers)
        self.assertEqual([], logger.filters)


class TestGetLogger(LoggingSetupTestCase):
    """Obtenção de loggers filhos do pacote."""

    def test_returns_package_logger_without_name(self):
        self.assertEqual(
            logging_setup.PACKAGE_LOGGER_NAME, logging_setup.get_logger().name
        )

    def test_keeps_names_already_inside_the_package(self):
        self.assertEqual("etl.extract", logging_setup.get_logger("etl.extract").name)

    def test_reparents_external_names_under_the_package(self):
        logger = logging_setup.get_logger("test_module")
        self.assertEqual("etl.test_module", logger.name)


class TestRedact(LoggingSetupTestCase):
    """Função de redação isolada (NFR-004)."""

    def test_registered_secret_is_removed(self):
        logging_setup.register_secret("s3nh4-secreta")
        self.assertEqual(
            f"conectando com {PLACEHOLDER}",
            logging_setup.redact("conectando com s3nh4-secreta"),
        )

    def test_all_occurrences_are_removed(self):
        logging_setup.register_secret("abc123")
        self.assertNotIn("abc123", logging_setup.redact("abc123 e abc123"))

    def test_longest_secret_wins(self):
        logging_setup.register_secret("senha")
        logging_setup.register_secret("senha-longa")
        self.assertEqual(PLACEHOLDER, logging_setup.redact("senha-longa"))

    def test_empty_secret_is_ignored(self):
        logging_setup.register_secret("")
        self.assertEqual("texto qualquer", logging_setup.redact("texto qualquer"))

    def test_non_string_secret_is_ignored(self):
        logging_setup.register_secret(None)
        logging_setup.register_secret(42)
        self.assertEqual("texto qualquer", logging_setup.redact("texto qualquer"))

    def test_clear_secrets_stops_redaction(self):
        logging_setup.register_secret("abc123")
        logging_setup.clear_secrets()
        self.assertEqual("abc123", logging_setup.redact("abc123"))

    def test_key_value_patterns_are_removed(self):
        for text in (
            "password=abc123",
            "passwd = abc123",
            "pwd:abc123",
            "senha = 'abc123'",
            'PASSWORD="abc123"',
            "token=abc123",
            "secret: abc123",
        ):
            with self.subTest(text=text):
                self.assertNotIn("abc123", logging_setup.redact(text))

    def test_key_value_redaction_preserves_the_key(self):
        self.assertEqual(
            f"password={PLACEHOLDER}", logging_setup.redact("password=abc123")
        )

    def test_key_value_redaction_stops_at_the_separator(self):
        self.assertEqual(
            f"user=carlos, password={PLACEHOLDER}, host=localhost",
            logging_setup.redact("user=carlos, password=abc123, host=localhost"),
        )

    def test_uri_credentials_are_removed(self):
        self.assertEqual(
            f"mysql://carlos:{PLACEHOLDER}@localhost:3306/vendas",
            logging_setup.redact("mysql://carlos:abc123@localhost:3306/vendas"),
        )

    def test_non_string_values_pass_through(self):
        self.assertIsNone(logging_setup.redact(None))
        self.assertEqual(42, logging_setup.redact(42))

    def test_text_without_secrets_is_unchanged(self):
        text = "Linhas carregadas: 1000"
        self.assertEqual(text, logging_setup.redact(text))


class TestRedactionInLogOutput(LoggingSetupTestCase):
    """A credencial não pode alcançar nenhuma saída de log (NFR-004)."""

    def setUp(self):
        super().setUp()
        logging_setup.register_secret("abc123")
        self.configure()
        self.logger = logging_setup.get_logger(__name__)

    def test_secret_in_message_is_redacted(self):
        self.logger.info("conectando com a senha abc123")
        output = self.console_output()
        self.assertNotIn("abc123", output)
        self.assertIn(PLACEHOLDER, output)

    def test_secret_in_positional_args_is_redacted(self):
        self.logger.info("usuário=%s senha=%s", "carlos", "abc123")
        output = self.console_output()
        self.assertNotIn("abc123", output)
        self.assertIn("carlos", output)

    def test_secret_in_mapping_args_is_redacted(self):
        self.logger.info("senha=%(password)s", {"password": "abc123"})
        self.assertNotIn("abc123", self.console_output())

    def test_key_value_pattern_in_message_is_redacted(self):
        self.logger.info("dsn: user=carlos password=outra-senha")
        self.assertNotIn("outra-senha", self.console_output())

    def test_secret_in_exception_message_is_redacted(self):
        try:
            raise RuntimeError("falha ao autenticar com abc123")
        except RuntimeError:
            self.logger.exception("erro de conexão")
        self.assertNotIn("abc123", self.console_output())

    def test_secret_in_traceback_is_redacted(self):
        try:
            raise ConfigError("senha inválida: abc123")
        except ConfigError:
            self.logger.exception("erro de configuração")
        output = self.console_output()
        self.assertNotIn("abc123", output)
        self.assertIn("Traceback", output)

    def test_secret_reaching_the_log_file_is_redacted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "../etl.log")
            logging_setup.configure_logging(
                level="DEBUG", log_file=path, stream=self.stream
            )
            logging_setup.get_logger(__name__).info("senha abc123")
            logging_setup.shutdown_logging()
            with open(path, encoding="utf-8") as handle:
                content = handle.read()
        self.assertNotIn("abc123", content)
        self.assertIn(PLACEHOLDER, content)


if __name__ == "__main__":
    unittest.main()
