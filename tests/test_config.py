"""Testes da carga, sobreposição e validação da configuração.

Cobre a tarefa 14 de ``docs/tasks.md`` (FR-011, NFR-004, NFR-005).
"""

import json
import os
import tempfile
import unittest

from etl import config, logging_setup
from etl.errors import ConfigError


def minimal_raw(**sections):
    """Configuração mínima válida, com as seções indicadas sobrepostas."""
    raw = {
        "source": {"path": "dados/vendas.xlsx"},
        "mapping": {"columns": {"Código": "codigo", "Cliente": "cliente"}},
        "database": {"host": "localhost", "database": "vendas", "user": "etl"},
        "load": {"table": "fato_vendas"},
    }
    for name, value in sections.items():
        if value is None:
            raw.pop(name, None)
        elif isinstance(value, dict) and name in raw:
            raw[name] = {**raw[name], **value}
        else:
            raw[name] = value
    return raw


class ConfigTestCase(unittest.TestCase):
    """Base que isola o ambiente e os segredos registrados."""

    def setUp(self):
        logging_setup.clear_secrets()

    def tearDown(self):
        logging_setup.clear_secrets()

    def parse(self, raw=None, *, env=None, overrides=None):
        """Analisa a configuração sem herdar o ambiente do processo."""
        return config.parse_config(
            minimal_raw() if raw is None else raw,
            env={} if env is None else env,
            overrides=overrides,
        )

    def assert_error_mentions(self, key, callable_object, *args, **kwargs):
        """Verifica que o erro levantado cita ``key``."""
        with self.assertRaises(ConfigError) as context:
            callable_object(*args, **kwargs)
        self.assertIn(key, str(context.exception))
        return context.exception


class TestDefaults(ConfigTestCase):
    """Valores padrão documentados (tarefa 13)."""

    def test_source_defaults(self):
        source = self.parse().source
        self.assertEqual("dados/vendas.xlsx", source.path)
        self.assertIsNone(source.sheet)
        self.assertEqual(config.DEFAULT_HEADER_ROW, source.header_row)
        self.assertEqual(config.DEFAULT_CHUNK_SIZE, source.chunk_size)

    def test_load_defaults(self):
        load = self.parse().load
        self.assertEqual(config.DEFAULT_LOAD_MODE, load.mode)
        self.assertEqual(config.DEFAULT_BATCH_SIZE, load.batch_size)
        self.assertEqual(config.DEFAULT_ON_BATCH_ERROR, load.on_batch_error)
        self.assertEqual((), load.unique_key)

    def test_database_defaults(self):
        database = self.parse().database
        self.assertEqual(config.DEFAULT_MYSQL_PORT, database.port)
        self.assertEqual(config.DEFAULT_CONNECT_RETRIES, database.connect_retries)
        self.assertEqual(
            config.DEFAULT_RETRY_BACKOFF_SECONDS, database.retry_backoff_seconds
        )
        self.assertEqual("", database.password)

    def test_run_defaults(self):
        run = self.parse().run
        self.assertEqual(logging_setup.DEFAULT_LOG_LEVEL, run.log_level)
        self.assertIsNone(run.log_file)
        self.assertEqual(config.DEFAULT_REJECTION_REPORT, run.rejection_report)
        self.assertFalse(run.dry_run)
        self.assertFalse(run.resume)

    def test_validation_defaults(self):
        validation = self.parse().validation
        self.assertEqual((), validation.required)
        self.assertEqual({}, validation.ranges)
        self.assertIsNone(validation.max_rejected_rows)
        self.assertIsNone(validation.max_rejected_percent)
        self.assertEqual(config.DEFAULT_ON_DUPLICATE, validation.on_duplicate)

    def test_documented_default_values(self):
        self.assertEqual(5_000, config.DEFAULT_CHUNK_SIZE)
        self.assertEqual(1_000, config.DEFAULT_BATCH_SIZE)


class TestParsing(ConfigTestCase):
    """Leitura de uma configuração completa (FR-011)."""

    def setUp(self):
        super().setUp()
        self.raw = minimal_raw(
            source={"sheet": "Vendas", "header_row": 2, "chunk_size": 100},
            mapping={
                "types": {"codigo": "int", "cliente": "str"},
                "normalizers": {"cliente": ["upper", "collapse_spaces"]},
            },
            validation={
                "required": ["codigo"],
                "ranges": {"codigo": {"minimum": 1, "maximum": 999}},
                "max_lengths": {"cliente": 120},
                "rejection_threshold": 50,
                "business_key": ["codigo"],
                "on_duplicate": "report",
            },
            database={"password": "s3nh4", "port": 3307, "connect_retries": 5},
            load={
                "mode": "upsert",
                "batch_size": 250,
                "unique_key": ["codigo"],
                "on_batch_error": "abort",
            },
            run={"log_level": "debug", "log_file": "etl.log", "dry_run": True},
        )

    def test_source_section(self):
        source = self.parse(self.raw).source
        self.assertEqual("Vendas", source.sheet)
        self.assertEqual(2, source.header_row)
        self.assertEqual(100, source.chunk_size)

    def test_mapping_section(self):
        mapping = self.parse(self.raw).mapping
        self.assertEqual({"Código": "codigo", "Cliente": "cliente"}, mapping.columns)
        self.assertEqual({"codigo": "int", "cliente": "str"}, mapping.types)
        self.assertEqual(("upper", "collapse_spaces"), mapping.normalizers["cliente"])
        self.assertEqual(("codigo", "cliente"), mapping.target_columns)

    def test_validation_section(self):
        validation = self.parse(self.raw).validation
        self.assertEqual(("codigo",), validation.required)
        self.assertEqual((1.0, 999.0), validation.ranges["codigo"])
        self.assertEqual(120, validation.max_lengths["cliente"])
        self.assertEqual(50, validation.max_rejected_rows)
        self.assertEqual(("codigo",), validation.business_key)
        self.assertEqual("report", validation.on_duplicate)

    def test_database_section(self):
        database = self.parse(self.raw).database
        self.assertEqual("s3nh4", database.password)
        self.assertEqual(3307, database.port)
        self.assertEqual(5, database.connect_retries)

    def test_load_section(self):
        load = self.parse(self.raw).load
        self.assertEqual("upsert", load.mode)
        self.assertEqual(250, load.batch_size)
        self.assertEqual(("codigo",), load.unique_key)
        self.assertEqual("abort", load.on_batch_error)

    def test_run_section(self):
        run = self.parse(self.raw).run
        self.assertEqual("DEBUG", run.log_level)
        self.assertEqual("etl.log", run.log_file)
        self.assertTrue(run.dry_run)

    def test_configuration_objects_are_immutable(self):
        parsed = self.parse(self.raw)
        with self.assertRaises(Exception):
            parsed.source.chunk_size = 10

    def test_input_mapping_is_not_modified(self):
        original = json.loads(json.dumps(self.raw))
        self.parse(self.raw, env={"ETL_DB_HOST": "outro"})
        self.assertEqual(original, self.raw)

    def test_comma_separated_list_is_accepted(self):
        raw = minimal_raw(validation={"required": "codigo, cliente"})
        self.assertEqual(("codigo", "cliente"), self.parse(raw).validation.required)

    def test_percentage_threshold(self):
        raw = minimal_raw(validation={"rejection_threshold": "5%"})
        validation = self.parse(raw).validation
        self.assertIsNone(validation.max_rejected_rows)
        self.assertEqual(5.0, validation.max_rejected_percent)

    def test_range_with_only_one_bound(self):
        raw = minimal_raw(validation={"ranges": {"codigo": {"minimum": 0}}})
        self.assertEqual((0.0, None), self.parse(raw).validation.ranges["codigo"])


class TestEnvironmentOverrides(ConfigTestCase):
    """Precedência das variáveis de ambiente (FR-011, NFR-004)."""

    def test_environment_overrides_file_value(self):
        raw = minimal_raw(database={"host": "do-arquivo"})
        parsed = self.parse(raw, env={"ETL_DB_HOST": "do-ambiente"})
        self.assertEqual("do-ambiente", parsed.database.host)

    def test_environment_supplies_password(self):
        parsed = self.parse(env={"ETL_DB_PASSWORD": "s3nh4"})
        self.assertEqual("s3nh4", parsed.database.password)

    def test_numeric_environment_values_are_converted(self):
        parsed = self.parse(
            env={"ETL_DB_PORT": "3307", "ETL_CHUNK_SIZE": "250", "ETL_BATCH_SIZE": "10"}
        )
        self.assertEqual(3307, parsed.database.port)
        self.assertEqual(250, parsed.source.chunk_size)
        self.assertEqual(10, parsed.load.batch_size)

    def test_boolean_environment_values_are_converted(self):
        for value, expected in (
            ("1", True),
            ("true", True),
            ("sim", True),
            ("0", False),
            ("nao", False),
            ("off", False),
        ):
            with self.subTest(value=value):
                parsed = self.parse(env={"ETL_DRY_RUN": value})
                self.assertEqual(expected, parsed.run.dry_run)

    def test_invalid_boolean_environment_value_is_rejected(self):
        self.assert_error_mentions(
            "ETL_DRY_RUN", self.parse, env={"ETL_DRY_RUN": "talvez"}
        )

    def test_environment_creates_missing_section(self):
        raw = minimal_raw(run=None)
        parsed = self.parse(raw, env={"ETL_LOG_LEVEL": "WARNING"})
        self.assertEqual("WARNING", parsed.run.log_level)

    def test_error_names_the_environment_variable(self):
        error = self.assert_error_mentions(
            "ETL_DB_PORT", self.parse, env={"ETL_DB_PORT": "porta"}
        )
        self.assertNotIn("database.port", str(error))

    def test_unrelated_environment_variables_are_ignored(self):
        parsed = self.parse(env={"PATH": "/usr/bin", "ETL_DESCONHECIDA": "x"})
        self.assertEqual("localhost", parsed.database.host)

    def test_process_environment_is_used_by_default(self):
        os.environ["ETL_DB_HOST"] = "do-processo"
        try:
            parsed = config.parse_config(minimal_raw())
        finally:
            del os.environ["ETL_DB_HOST"]
        self.assertEqual("do-processo", parsed.database.host)


class TestExplicitOverrides(ConfigTestCase):
    """Sobreposições explícitas, usadas pelos argumentos da CLI."""

    def test_override_wins_over_environment(self):
        parsed = self.parse(
            env={"ETL_BATCH_SIZE": "10"}, overrides={"load.batch_size": 99}
        )
        self.assertEqual(99, parsed.load.batch_size)

    def test_none_override_is_ignored(self):
        parsed = self.parse(
            env={"ETL_BATCH_SIZE": "10"}, overrides={"load.batch_size": None}
        )
        self.assertEqual(10, parsed.load.batch_size)

    def test_override_is_validated(self):
        self.assert_error_mentions(
            "load.batch_size", self.parse, overrides={"load.batch_size": 0}
        )


class TestRequiredKeys(ConfigTestCase):
    """Chaves obrigatórias ausentes (FR-011)."""

    def test_missing_source_path(self):
        raw = minimal_raw()
        del raw["source"]["path"]
        self.assert_error_mentions("source.path", self.parse, raw)

    def test_missing_source_section(self):
        self.assert_error_mentions(
            "source.path", self.parse, minimal_raw(source=None)
        )

    def test_missing_database_host(self):
        raw = minimal_raw()
        del raw["database"]["host"]
        self.assert_error_mentions("database.host", self.parse, raw)

    def test_missing_database_name(self):
        raw = minimal_raw()
        del raw["database"]["database"]
        self.assert_error_mentions("database.database", self.parse, raw)

    def test_missing_database_user(self):
        raw = minimal_raw()
        del raw["database"]["user"]
        self.assert_error_mentions("database.user", self.parse, raw)

    def test_missing_load_table(self):
        raw = minimal_raw()
        del raw["load"]["table"]
        self.assert_error_mentions("load.table", self.parse, raw)

    def test_missing_column_mapping(self):
        self.assert_error_mentions(
            "mapeamento", self.parse, minimal_raw(mapping={"columns": {}})
        )

    def test_blank_value_counts_as_missing(self):
        self.assert_error_mentions(
            "source.path", self.parse, minimal_raw(source={"path": "   "})
        )


class TestInvalidValues(ConfigTestCase):
    """Valores presentes, porém inválidos (FR-011)."""

    def test_chunk_size_must_be_positive(self):
        self.assert_error_mentions(
            "source.chunk_size", self.parse, minimal_raw(source={"chunk_size": 0})
        )

    def test_chunk_size_must_be_an_integer(self):
        raw = minimal_raw(source={"chunk_size": "muitas"})
        self.assert_error_mentions("source.chunk_size", self.parse, raw)

    def test_header_row_must_be_positive(self):
        self.assert_error_mentions(
            "source.header_row", self.parse, minimal_raw(source={"header_row": 0})
        )

    def test_batch_size_must_be_positive(self):
        self.assert_error_mentions(
            "load.batch_size", self.parse, minimal_raw(load={"batch_size": -1})
        )

    def test_port_out_of_range(self):
        self.assert_error_mentions(
            "database.port", self.parse, minimal_raw(database={"port": 70000})
        )

    def test_retry_backoff_must_not_be_negative(self):
        self.assert_error_mentions(
            "database.retry_backoff_seconds",
            self.parse,
            minimal_raw(database={"retry_backoff_seconds": -1}),
        )

    def test_boolean_is_not_accepted_as_integer(self):
        self.assert_error_mentions(
            "source.chunk_size", self.parse, minimal_raw(source={"chunk_size": True})
        )

    def test_unknown_load_mode(self):
        self.assert_error_mentions(
            "substituir", self.parse, minimal_raw(load={"mode": "substituir"})
        )

    def test_upsert_requires_unique_key(self):
        self.assert_error_mentions(
            "upsert", self.parse, minimal_raw(load={"mode": "upsert"})
        )

    def test_unknown_on_batch_error(self):
        self.assert_error_mentions(
            "load.on_batch_error", self.parse, minimal_raw(load={"on_batch_error": "x"})
        )

    def test_unknown_on_duplicate(self):
        self.assert_error_mentions(
            "validation.on_duplicate",
            self.parse,
            minimal_raw(validation={"on_duplicate": "x"}),
        )

    def test_unknown_declared_type(self):
        self.assert_error_mentions(
            "moeda", self.parse, minimal_raw(mapping={"types": {"codigo": "moeda"}})
        )

    def test_unknown_normalizer(self):
        self.assert_error_mentions(
            "acentuar",
            self.parse,
            minimal_raw(mapping={"normalizers": {"cliente": ["acentuar"]}}),
        )

    def test_invalid_log_level(self):
        self.assert_error_mentions(
            "run.log_level", self.parse, minimal_raw(run={"log_level": "VERBOSO"})
        )

    def test_inverted_range(self):
        raw = minimal_raw(
            validation={"ranges": {"codigo": {"minimum": 10, "maximum": 1}}}
        )
        self.assert_error_mentions("validation.ranges.codigo", self.parse, raw)

    def test_empty_range(self):
        self.assert_error_mentions(
            "validation.ranges.codigo",
            self.parse,
            minimal_raw(validation={"ranges": {"codigo": {}}}),
        )

    def test_invalid_percentage_threshold(self):
        self.assert_error_mentions(
            "validation.rejection_threshold",
            self.parse,
            minimal_raw(validation={"rejection_threshold": "150%"}),
        )

    def test_non_numeric_threshold(self):
        self.assert_error_mentions(
            "validation.rejection_threshold",
            self.parse,
            minimal_raw(validation={"rejection_threshold": "muitas"}),
        )

    def test_section_must_be_an_object(self):
        self.assert_error_mentions("database", self.parse, minimal_raw(database="x"))

    def test_columns_must_map_text_to_text(self):
        self.assert_error_mentions(
            "mapping.columns",
            self.parse,
            minimal_raw(mapping={"columns": {"Código": 10}}),
        )

    def test_duplicate_target_column(self):
        self.assert_error_mentions(
            "codigo",
            self.parse,
            minimal_raw(mapping={"columns": {"Código": "codigo", "Cod": "codigo"}}),
        )


class TestUnknownKeys(ConfigTestCase):
    """Chaves não reconhecidas indicam erro de digitação (FR-011)."""

    def test_unknown_top_level_section(self):
        raw = minimal_raw()
        raw["destino"] = {}
        self.assert_error_mentions("destino", self.parse, raw)

    def test_unknown_key_inside_section(self):
        self.assert_error_mentions(
            "source.caminho", self.parse, minimal_raw(source={"caminho": "x.xlsx"})
        )

    def test_unknown_key_inside_range(self):
        self.assert_error_mentions(
            "validation.ranges.codigo.minimo",
            self.parse,
            minimal_raw(validation={"ranges": {"codigo": {"minimo": 1}}}),
        )


class TestColumnReferences(ConfigTestCase):
    """Toda coluna citada deve existir no mapeamento (FR-003)."""

    def test_unknown_column_in_types(self):
        raw = minimal_raw(mapping={"types": {"total": "int"}})
        self.assert_error_mentions("mapping.types", self.parse, raw)

    def test_unknown_column_in_required(self):
        raw = minimal_raw(validation={"required": ["total"]})
        self.assert_error_mentions("validation.required", self.parse, raw)

    def test_unknown_column_in_business_key(self):
        self.assert_error_mentions(
            "validation.business_key",
            self.parse,
            minimal_raw(validation={"business_key": ["total"]}),
        )

    def test_unknown_column_in_unique_key(self):
        self.assert_error_mentions(
            "load.unique_key",
            self.parse,
            minimal_raw(load={"mode": "upsert", "unique_key": ["total"]}),
        )

    def test_source_column_name_is_not_a_valid_reference(self):
        self.assert_error_mentions(
            "Código", self.parse, minimal_raw(validation={"required": ["Código"]})
        )


class TestCredentialSafety(ConfigTestCase):
    """A senha não pode vazar por repr nem por log (NFR-004)."""

    def test_password_is_absent_from_repr(self):
        parsed = self.parse(env={"ETL_DB_PASSWORD": "s3nh4-secreta"})
        self.assertNotIn("s3nh4-secreta", repr(parsed))
        self.assertNotIn("s3nh4-secreta", repr(parsed.database))

    def test_password_is_registered_for_redaction(self):
        self.parse(env={"ETL_DB_PASSWORD": "s3nh4-secreta"})
        self.assertEqual(
            "conectando com ***", logging_setup.redact("conectando com s3nh4-secreta")
        )

    def test_empty_password_is_not_registered(self):
        self.parse()
        self.assertEqual("qualquer texto", logging_setup.redact("qualquer texto"))

    def test_password_keeps_surrounding_spaces(self):
        parsed = self.parse(env={"ETL_DB_PASSWORD": " s3nh4 "})
        self.assertEqual(" s3nh4 ", parsed.database.password)


class TestLoadConfigFromFile(ConfigTestCase):
    """Leitura do arquivo JSON (FR-011)."""

    def write_config(self, directory, content, name="config.json"):
        """Grava ``content`` como arquivo de configuração e devolve o caminho."""
        path = os.path.join(directory, name)
        with open(path, "w", encoding="utf-8") as handle:
            if isinstance(content, str):
                handle.write(content)
            else:
                json.dump(content, handle)
        return path

    def test_reads_a_valid_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_config(directory, minimal_raw())
            parsed = config.load_config(path, env={})
        self.assertEqual("fato_vendas", parsed.load.table)

    def test_reads_accented_content(self):
        with tempfile.TemporaryDirectory() as directory:
            raw = minimal_raw(mapping={"columns": {"Descrição": "descricao"}})
            path = self.write_config(directory, raw)
            parsed = config.load_config(path, env={})
        self.assertEqual({"Descrição": "descricao"}, parsed.mapping.columns)

    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "inexistente.json")
            self.assert_error_mentions(path, config.load_config, path, env={})

    def test_invalid_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_config(directory, "{isto não é json}")
            self.assert_error_mentions(path, config.load_config, path, env={})

    def test_directory_instead_of_file(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assert_error_mentions(
                directory, config.load_config, directory, env={}
            )

    def test_root_must_be_an_object(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_config(directory, [1, 2, 3])
            self.assert_error_mentions("raiz", config.load_config, path, env={})

    def test_environment_overrides_are_applied_to_the_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_config(directory, minimal_raw())
            parsed = config.load_config(path, env={"ETL_LOAD_TABLE": "outra_tabela"})
        self.assertEqual("outra_tabela", parsed.load.table)


class TestNoSideEffects(ConfigTestCase):
    """A validação não acessa a planilha nem o banco (FR-011)."""

    def test_nonexistent_source_file_is_accepted(self):
        raw = minimal_raw(source={"path": "/caminho/que/nao/existe.xlsx"})
        self.assertEqual("/caminho/que/nao/existe.xlsx", self.parse(raw).source.path)

    def test_unreachable_database_is_accepted(self):
        raw = minimal_raw(database={"host": "servidor-inexistente.invalid"})
        self.assertEqual("servidor-inexistente.invalid", self.parse(raw).database.host)


if __name__ == "__main__":
    unittest.main()
