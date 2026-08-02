"""Carga, sobreposição e validação da configuração do pipeline (FR-011).

O formato do arquivo de configuração é **JSON**, escolhido por ser suportado
pela biblioteca padrão (sem dependência adicional, NFR-008) e por representar
naturalmente as estruturas aninhadas do mapeamento de colunas.

Precedência dos valores, do menor para o maior:

1. valores padrão deste módulo;
2. arquivo de configuração;
3. variáveis de ambiente ``ETL_*`` (FR-011, NFR-004);
4. sobreposições explícitas (usadas pelos argumentos da CLI na Fase 6).

Toda a validação é feita de uma só vez, **antes** de qualquer acesso à
planilha ou ao banco de dados: :func:`load_config` só lê o próprio arquivo de
configuração. A existência da planilha é verificada na extração (FR-001) e a
da tabela de destino, na carga (FR-010).

Exemplo de arquivo::

    {
      "source": {"path": "dados/vendas.xlsx", "sheet": "Vendas"},
      "mapping": {
        "columns": {"Código": "codigo", "Cliente": "cliente"},
        "types": {"codigo": "int"},
        "normalizers": {"cliente": ["upper"]}
      },
      "validation": {"required": ["codigo"], "rejection_threshold": "5%"},
      "database": {"host": "localhost", "database": "vendas", "user": "etl"},
      "load": {"table": "fato_vendas", "mode": "append"},
      "run": {"log_level": "INFO", "rejection_report": "rejeicoes.csv"}
    }
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from etl import logging_setup, messages
from etl.errors import ConfigError

__all__ = [
    "DEFAULT_CHUNK_SIZE",
    "DEFAULT_BATCH_SIZE",
    "DEFAULT_HEADER_ROW",
    "DEFAULT_MYSQL_PORT",
    "DEFAULT_CONNECT_RETRIES",
    "DEFAULT_RETRY_BACKOFF_SECONDS",
    "DEFAULT_LOAD_MODE",
    "DEFAULT_ON_BATCH_ERROR",
    "DEFAULT_ON_DUPLICATE",
    "DEFAULT_REJECTION_REPORT",
    "ENV_PREFIX",
    "ENV_OVERRIDES",
    "LOAD_MODES",
    "ON_BATCH_ERROR_CHOICES",
    "ON_DUPLICATE_CHOICES",
    "KNOWN_TYPES",
    "KNOWN_NORMALIZERS",
    "SourceConfig",
    "MappingConfig",
    "ValidationConfig",
    "DatabaseConfig",
    "LoadConfig",
    "RunConfig",
    "DimensionConfig",
    "EtlConfig",
    "load_config",
    "parse_config",
]

# --------------------------------------------------------------------------
# Valores padrão (tarefa 13 de docs/tasks.md)
# --------------------------------------------------------------------------

#: Linhas lidas por bloco. Mantém o consumo de memória proporcional ao bloco,
#: e não ao tamanho do arquivo (FR-002, NFR-001).
DEFAULT_CHUNK_SIZE = 5_000

#: Registros gravados por lote no MySQL (FR-009, NFR-002).
DEFAULT_BATCH_SIZE = 1_000

#: Posição (base 1) da linha de cabeçalho na aba lida (FR-001).
DEFAULT_HEADER_ROW = 1

#: Porta padrão do MySQL (FR-008).
DEFAULT_MYSQL_PORT = 3306

#: Tentativas adicionais de conexão antes de falhar (FR-008).
DEFAULT_CONNECT_RETRIES = 3

#: Espera inicial, em segundos, entre tentativas de conexão (FR-008).
DEFAULT_RETRY_BACKOFF_SECONDS = 1.0

#: Modo de carga aplicado quando nenhum é informado (FR-010).
DEFAULT_LOAD_MODE = "append"

#: Comportamento padrão diante da falha de um lote (FR-009).
DEFAULT_ON_BATCH_ERROR = "isolate"

#: Comportamento padrão diante de uma chave de negócio repetida (FR-007).
DEFAULT_ON_DUPLICATE = "discard"

#: Arquivo padrão do relatório de rejeições (FR-006).
DEFAULT_REJECTION_REPORT = "rejeicoes.csv"

#: Arquivo padrão para o ponto de controle (FR-015).
DEFAULT_CHECKPOINT_FILE = "checkpoint.json"

#: Prefixo das variáveis de ambiente reconhecidas (FR-011).
ENV_PREFIX = "ETL_"

#: Modos de carga aceitos (FR-010).
LOAD_MODES = ("append", "truncate", "upsert")

#: Ações possíveis quando um lote falha (FR-009).
ON_BATCH_ERROR_CHOICES = ("isolate", "abort")

#: Ações possíveis quando uma chave de negócio se repete (FR-007).
ON_DUPLICATE_CHOICES = ("discard", "report")

#: Tipos que podem ser declarados para as colunas de destino (FR-005).
KNOWN_TYPES = ("str", "int", "decimal", "float", "bool", "date", "datetime")

#: Normalizadores disponíveis para as colunas de destino (FR-004).
KNOWN_NORMALIZERS = ("trim", "upper", "lower", "strip_punctuation", "collapse_spaces")

#: Variável de ambiente -> caminho pontilhado na configuração (FR-011).
ENV_OVERRIDES = {
    "ETL_SOURCE_PATH": "source.path",
    "ETL_SOURCE_SHEET": "source.sheet",
    "ETL_HEADER_ROW": "source.header_row",
    "ETL_CHUNK_SIZE": "source.chunk_size",
    "ETL_REJECTION_THRESHOLD": "validation.rejection_threshold",
    "ETL_DB_HOST": "database.host",
    "ETL_DB_PORT": "database.port",
    "ETL_DB_NAME": "database.database",
    "ETL_DB_USER": "database.user",
    "ETL_DB_PASSWORD": "database.password",
    "ETL_DB_CONNECT_RETRIES": "database.connect_retries",
    "ETL_DB_RETRY_BACKOFF": "database.retry_backoff_seconds",
    "ETL_LOAD_TABLE": "load.table",
    "ETL_LOAD_MODE": "load.mode",
    "ETL_BATCH_SIZE": "load.batch_size",
    "ETL_LOG_LEVEL": "run.log_level",
    "ETL_LOG_FILE": "run.log_file",
    "ETL_REJECTION_REPORT": "run.rejection_report",
    "ETL_CHECKPOINT_FILE": "run.checkpoint_file",
    "ETL_DRY_RUN": "run.dry_run",
    "ETL_RESUME": "run.resume",
}

_TRUE_VALUES = ("1", "true", "t", "yes", "y", "on", "sim", "s")
_FALSE_VALUES = ("0", "false", "f", "no", "n", "off", "nao", "não")

_SECTIONS = ("source", "mapping", "validation", "database", "load", "run", "dimensions")


# --------------------------------------------------------------------------
# Estruturas de configuração (tarefa 9 de docs/tasks.md)
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SourceConfig:
    """Origem dos dados: planilha, aba e tamanho do bloco (FR-001, FR-002)."""

    path: str
    sheet: str | None = None
    header_row: int = DEFAULT_HEADER_ROW
    chunk_size: int = DEFAULT_CHUNK_SIZE


@dataclass(frozen=True, slots=True)
class MappingConfig:
    """Mapeamento origem -> destino, tipos e normalizadores (FR-003 a FR-005)."""

    columns: dict[str, str] = field(default_factory=dict)
    types: dict[str, str] = field(default_factory=dict)
    normalizers: dict[str, tuple[str, ...]] = field(default_factory=dict)

    @property
    def target_columns(self) -> tuple[str, ...]:
        """Colunas de destino, na ordem em que foram declaradas."""
        return tuple(self.columns.values())


@dataclass(frozen=True, slots=True)
class ValidationConfig:
    """Regras de validação, limite de rejeições e chave de negócio (FR-006, FR-007)."""

    required: tuple[str, ...] = ()
    ranges: dict[str, tuple[Any, Any]] = field(default_factory=dict)
    max_lengths: dict[str, int] = field(default_factory=dict)
    max_rejected_rows: int | None = None
    max_rejected_percent: float | None = None
    business_key: tuple[str, ...] = ()
    on_duplicate: str = DEFAULT_ON_DUPLICATE


@dataclass(frozen=True, slots=True)
class DatabaseConfig:
    """Dados de conexão com o MySQL (FR-008).

    A senha é omitida do ``repr`` para não vazar em tracebacks (NFR-004).
    """

    host: str
    database: str
    user: str
    password: str = field(default="", repr=False)
    port: int = DEFAULT_MYSQL_PORT
    connect_retries: int = DEFAULT_CONNECT_RETRIES
    retry_backoff_seconds: float = DEFAULT_RETRY_BACKOFF_SECONDS


@dataclass(frozen=True, slots=True)
class LoadConfig:
    """Tabela de destino, modo de carga e tamanho do lote (FR-009, FR-010)."""

    table: str
    mode: str = DEFAULT_LOAD_MODE
    batch_size: int = DEFAULT_BATCH_SIZE
    unique_key: tuple[str, ...] = ()
    on_batch_error: str = DEFAULT_ON_BATCH_ERROR


@dataclass(frozen=True, slots=True)
class RunConfig:
    """Opções de execução: log, relatório, simulação e retomada (FR-012 a FR-014)."""

    log_level: str = logging_setup.DEFAULT_LOG_LEVEL
    log_file: str | None = None
    rejection_report: str = DEFAULT_REJECTION_REPORT
    checkpoint_file: str = DEFAULT_CHECKPOINT_FILE
    dry_run: bool = False
    resume: bool = False


@dataclass(frozen=True, slots=True)
class DimensionConfig:
    """Configuração para carga de uma tabela de dimensão (FR-016)."""

    mapping: MappingConfig
    validation: ValidationConfig
    load: LoadConfig


@dataclass(frozen=True, slots=True)
class EtlConfig:
    """Configuração completa e já validada do pipeline."""

    source: SourceConfig
    mapping: MappingConfig
    validation: ValidationConfig
    database: DatabaseConfig
    load: LoadConfig
    run: RunConfig
    dimensions: list[DimensionConfig] = field(default_factory=list)


# --------------------------------------------------------------------------
# Leitura auxiliar com mensagens de erro consistentes
# --------------------------------------------------------------------------


class _Reader:
    """Lê e valida os valores de uma seção, citando a origem de cada chave.

    Quando um valor veio de uma variável de ambiente ou de uma sobreposição
    da CLI, a mensagem de erro cita essa origem em vez do caminho no arquivo,
    para que o usuário saiba onde corrigir.
    """

    def __init__(
        self,
        data: Mapping[str, Any],
        prefix: str,
        origins: Mapping[str, str],
    ) -> None:
        self._data = data
        self._prefix = prefix
        self._origins = origins

    def path(self, key: str) -> str:
        """Caminho pontilhado completo da chave."""
        return f"{self._prefix}.{key}" if self._prefix else key

    def label(self, key: str) -> str:
        """Nome da chave conforme sua origem, usado nas mensagens de erro."""
        path = self.path(key)
        return self._origins.get(path, path)

    def invalid(self, key: str, reason: str) -> ConfigError:
        """Cria o erro padrão de valor inválido para ``key``."""
        return ConfigError(
            messages.ERR_CONFIG_INVALID_VALUE.format(key=self.label(key), reason=reason)
        )

    def missing(self, key: str) -> ConfigError:
        """Cria o erro padrão de chave obrigatória ausente."""
        return ConfigError(
            messages.ERR_CONFIG_MISSING_KEY.format(key=self.label(key))
        )

    def check_unknown_keys(self, allowed: Sequence[str]) -> None:
        """Rejeita chaves não reconhecidas, evitando erros de digitação."""
        for key in self._data:
            if key not in allowed:
                raise ConfigError(
                    messages.ERR_CONFIG_UNKNOWN_KEY.format(
                        key=self.path(key), allowed=", ".join(sorted(allowed))
                    )
                )

    def raw(self, key: str) -> Any:
        """Valor bruto, sem conversão."""
        return self._data.get(key)

    def section(self, key: str) -> "_Reader":
        """Sub-seção como novo leitor; ausente equivale a seção vazia."""
        value = self._data.get(key)
        if value is None:
            value = {}
        if not isinstance(value, Mapping):
            raise ConfigError(
                messages.ERR_CONFIG_NOT_AN_OBJECT.format(key=self.path(key))
            )
        return _Reader(value, self.path(key), self._origins)

    def string(
        self,
        key: str,
        *,
        default: str | None = None,
        required: bool = False,
    ) -> str | None:
        """Texto não vazio; ``required`` exige a presença da chave."""
        value = self._data.get(key)
        if value is None or (isinstance(value, str) and not value.strip()):
            if required:
                raise self.missing(key)
            return default
        if not isinstance(value, str):
            raise self.invalid(key, "deve ser um texto")
        return value.strip()

    def secret(self, key: str, *, default: str = "") -> str:
        """Texto sensível: aceita valor vazio e nunca aparece nas mensagens."""
        value = self._data.get(key)
        if value is None:
            return default
        if not isinstance(value, str):
            raise self.invalid(key, "deve ser um texto")
        return value

    def integer(
        self,
        key: str,
        *,
        default: int | None = None,
        required: bool = False,
        minimum: int | None = None,
        maximum: int | None = None,
    ) -> int | None:
        """Inteiro dentro dos limites informados; aceita texto numérico."""
        value = self._data.get(key)
        if value is None or (isinstance(value, str) and not value.strip()):
            if required:
                raise self.missing(key)
            return default
        if isinstance(value, bool) or not isinstance(value, (int, str)):
            raise self.invalid(key, "deve ser um número inteiro")
        try:
            number = int(str(value).strip())
        except ValueError as error:
            raise self.invalid(key, "deve ser um número inteiro") from error
        if minimum is not None and number < minimum:
            raise self.invalid(key, f"deve ser maior ou igual a {minimum}")
        if maximum is not None and number > maximum:
            raise self.invalid(key, f"deve ser menor ou igual a {maximum}")
        return number

    def number(
        self,
        key: str,
        *,
        default: float | None = None,
        minimum: float | None = None,
    ) -> float | None:
        """Número real; aceita texto numérico vindo do ambiente."""
        value = self._data.get(key)
        if value is None or (isinstance(value, str) and not value.strip()):
            return default
        if isinstance(value, bool) or not isinstance(value, (int, float, str)):
            raise self.invalid(key, "deve ser um número")
        try:
            number = float(str(value).strip())
        except ValueError as error:
            raise self.invalid(key, "deve ser um número") from error
        if minimum is not None and number < minimum:
            raise self.invalid(key, f"deve ser maior ou igual a {minimum}")
        return number

    def boolean(self, key: str, *, default: bool = False) -> bool:
        """Booleano; aceita as formas textuais usadas em variáveis de ambiente."""
        value = self._data.get(key)
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in _TRUE_VALUES:
                return True
            if normalized in _FALSE_VALUES:
                return False
        raise self.invalid(key, "deve ser verdadeiro ou falso")

    def choice(self, key: str, allowed: Sequence[str], *, default: str) -> str:
        """Valor restrito a uma lista fechada de opções."""
        value = self.string(key, default=default)
        if value not in allowed:
            raise ConfigError(
                messages.ERR_CONFIG_INVALID_CHOICE.format(
                    value=value, key=self.label(key), allowed=", ".join(allowed)
                )
            )
        return value

    def string_tuple(self, key: str) -> tuple[str, ...]:
        """Lista de textos não vazios; aceita texto único separado por vírgulas."""
        value = self._data.get(key)
        if value is None:
            return ()
        if isinstance(value, str):
            items = [item.strip() for item in value.split(",")]
        elif isinstance(value, Sequence):
            items = []
            for item in value:
                if not isinstance(item, str):
                    raise self.invalid(key, "deve ser uma lista de textos")
                items.append(item.strip())
        else:
            raise self.invalid(key, "deve ser uma lista de textos")
        if any(not item for item in items):
            raise self.invalid(key, "não pode conter itens vazios")
        return tuple(items)

    def string_dict(self, key: str) -> dict[str, str]:
        """Objeto cujos pares chave/valor são textos não vazios."""
        value = self._data.get(key)
        if value is None:
            return {}
        if not isinstance(value, Mapping):
            raise ConfigError(
                messages.ERR_CONFIG_NOT_AN_OBJECT.format(key=self.path(key))
            )
        result: dict[str, str] = {}
        for name, item in value.items():
            if not isinstance(item, str) or not item.strip() or not str(name).strip():
                raise self.invalid(key, "deve associar textos não vazios")
            result[str(name).strip()] = item.strip()
        return result

    def mapping(self, key: str) -> Mapping[str, Any]:
        """Objeto genérico, validado apenas quanto ao tipo."""
        value = self._data.get(key)
        if value is None:
            return {}
        if not isinstance(value, Mapping):
            raise ConfigError(
                messages.ERR_CONFIG_NOT_AN_OBJECT.format(key=self.path(key))
            )
        return value


# --------------------------------------------------------------------------
# Sobreposições (tarefa 11 de docs/tasks.md)
# --------------------------------------------------------------------------


def _set_path(data: dict[str, Any], path: str, value: Any) -> None:
    """Grava ``value`` no caminho pontilhado ``path``, criando as seções."""
    *sections, key = path.split(".")
    target = data
    for section in sections:
        existing = target.get(section)
        if not isinstance(existing, dict):
            existing = {}
            target[section] = existing
        target = existing
    target[key] = value


def _deep_copy_sections(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Copia o primeiro nível de seções para não alterar a entrada do chamador."""
    result: dict[str, Any] = {}
    for key, value in raw.items():
        result[key] = dict(value) if isinstance(value, Mapping) else value
    return result


def _apply_overrides(
    raw: Mapping[str, Any],
    env: Mapping[str, str] | None,
    overrides: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, str]]:
    """Aplica ambiente e sobreposições sobre ``raw``.

    Devolve a configuração resultante e a origem de cada caminho sobreposto,
    usada para que as mensagens de erro citem a variável de ambiente ou o
    argumento da CLI em vez do caminho no arquivo.
    """
    merged = _deep_copy_sections(raw)
    origins: dict[str, str] = {}

    if env:
        for variable, path in ENV_OVERRIDES.items():
            if variable in env:
                _set_path(merged, path, env[variable])
                origins[path] = variable

    if overrides:
        for path, value in overrides.items():
            if value is None:
                continue
            _set_path(merged, path, value)
            origins[path] = path

    return merged, origins


# --------------------------------------------------------------------------
# Validação por seção (tarefa 12 de docs/tasks.md)
# --------------------------------------------------------------------------


def _parse_source(reader: _Reader) -> SourceConfig:
    """Valida a seção ``source``."""
    reader.check_unknown_keys(("path", "sheet", "header_row", "chunk_size"))
    return SourceConfig(
        path=reader.string("path", required=True),
        sheet=reader.string("sheet"),
        header_row=reader.integer("header_row", default=DEFAULT_HEADER_ROW, minimum=1),
        chunk_size=reader.integer("chunk_size", default=DEFAULT_CHUNK_SIZE, minimum=1),
    )


def _parse_mapping(reader: _Reader) -> MappingConfig:
    """Valida a seção ``mapping`` (FR-003 a FR-005)."""
    reader.check_unknown_keys(("columns", "types", "normalizers"))

    columns = reader.string_dict("columns")
    if not columns:
        raise ConfigError(messages.ERR_MAPPING_EMPTY)

    seen: set[str] = set()
    for target in columns.values():
        if target in seen:
            raise ConfigError(
                messages.ERR_CONFIG_DUPLICATE_TARGET_COLUMN.format(column=target)
            )
        seen.add(target)

    types = reader.string_dict("types")
    for column, type_name in types.items():
        if type_name not in KNOWN_TYPES:
            raise ConfigError(
                messages.ERR_UNKNOWN_TYPE.format(type_name=type_name, column=column)
            )

    normalizers: dict[str, tuple[str, ...]] = {}
    raw_normalizers = reader.mapping("normalizers")
    normalizers_reader = reader.section("normalizers")
    for column in raw_normalizers:
        names = normalizers_reader.string_tuple(column)
        for name in names:
            if name not in KNOWN_NORMALIZERS:
                raise ConfigError(
                    messages.ERR_UNKNOWN_NORMALIZER.format(
                        normalizer=name, column=column
                    )
                )
        normalizers[column] = names

    return MappingConfig(columns=columns, types=types, normalizers=normalizers)


def _parse_threshold(reader: _Reader) -> tuple[int | None, float | None]:
    """Interpreta ``rejection_threshold`` como número de linhas ou percentual."""
    value = reader.raw("rejection_threshold")
    if value is None:
        return None, None

    if isinstance(value, bool):
        raise ConfigError(
            messages.ERR_CONFIG_INVALID_THRESHOLD.format(
                value=value, key=reader.label("rejection_threshold")
            )
        )

    if isinstance(value, str):
        text = value.strip()
        if text.endswith("%"):
            try:
                percent = float(text[:-1].strip().replace(",", "."))
            except ValueError as error:
                raise ConfigError(
                    messages.ERR_CONFIG_INVALID_THRESHOLD.format(
                        value=value, key=reader.label("rejection_threshold")
                    )
                ) from error
            if not 0.0 <= percent <= 100.0:
                raise reader.invalid(
                    "rejection_threshold", "o percentual deve estar entre 0 e 100"
                )
            return None, percent

    rows = reader.integer("rejection_threshold", minimum=0)
    return rows, None


def _parse_validation(reader: _Reader) -> ValidationConfig:
    """Valida a seção ``validation`` (FR-006, FR-007)."""
    reader.check_unknown_keys(
        (
            "required",
            "ranges",
            "max_lengths",
            "rejection_threshold",
            "business_key",
            "on_duplicate",
        )
    )

    ranges: dict[str, tuple[Any, Any]] = {}
    ranges_reader = reader.section("ranges")
    for column in reader.mapping("ranges"):
        bounds = ranges_reader.section(column)
        bounds.check_unknown_keys(("minimum", "maximum"))
        minimum = bounds.number("minimum")
        maximum = bounds.number("maximum")
        if minimum is None and maximum is None:
            raise ranges_reader.invalid(
                column, "informe ao menos 'minimum' ou 'maximum'"
            )
        if minimum is not None and maximum is not None and minimum > maximum:
            raise ranges_reader.invalid(
                column, "'minimum' não pode ser maior que 'maximum'"
            )
        ranges[column] = (minimum, maximum)

    max_lengths: dict[str, int] = {}
    lengths_reader = reader.section("max_lengths")
    for column in reader.mapping("max_lengths"):
        max_lengths[column] = lengths_reader.integer(column, minimum=1, required=True)

    max_rejected_rows, max_rejected_percent = _parse_threshold(reader)

    return ValidationConfig(
        required=reader.string_tuple("required"),
        ranges=ranges,
        max_lengths=max_lengths,
        max_rejected_rows=max_rejected_rows,
        max_rejected_percent=max_rejected_percent,
        business_key=reader.string_tuple("business_key"),
        on_duplicate=reader.choice(
            "on_duplicate", ON_DUPLICATE_CHOICES, default=DEFAULT_ON_DUPLICATE
        ),
    )


def _parse_database(reader: _Reader) -> DatabaseConfig:
    """Valida a seção ``database`` (FR-008)."""
    reader.check_unknown_keys(
        (
            "host",
            "port",
            "database",
            "user",
            "password",
            "connect_retries",
            "retry_backoff_seconds",
        )
    )
    return DatabaseConfig(
        host=reader.string("host", required=True),
        database=reader.string("database", required=True),
        user=reader.string("user", required=True),
        password=reader.secret("password"),
        port=reader.integer(
            "port", default=DEFAULT_MYSQL_PORT, minimum=1, maximum=65535
        ),
        connect_retries=reader.integer(
            "connect_retries", default=DEFAULT_CONNECT_RETRIES, minimum=0
        ),
        retry_backoff_seconds=reader.number(
            "retry_backoff_seconds",
            default=DEFAULT_RETRY_BACKOFF_SECONDS,
            minimum=0.0,
        ),
    )


def _parse_load(reader: _Reader) -> LoadConfig:
    """Valida a seção ``load`` (FR-009, FR-010)."""
    reader.check_unknown_keys(
        ("table", "mode", "batch_size", "unique_key", "on_batch_error")
    )

    mode = reader.string("mode", default=DEFAULT_LOAD_MODE)
    if mode not in LOAD_MODES:
        raise ConfigError(
            messages.ERR_CONFIG_UNKNOWN_LOAD_MODE.format(
                mode=mode, allowed=", ".join(LOAD_MODES)
            )
        )

    unique_key = reader.string_tuple("unique_key")
    if mode == "upsert" and not unique_key:
        raise ConfigError(messages.ERR_UPSERT_WITHOUT_KEY)

    return LoadConfig(
        table=reader.string("table", required=True),
        mode=mode,
        batch_size=reader.integer("batch_size", default=DEFAULT_BATCH_SIZE, minimum=1),
        unique_key=unique_key,
        on_batch_error=reader.choice(
            "on_batch_error", ON_BATCH_ERROR_CHOICES, default=DEFAULT_ON_BATCH_ERROR
        ),
    )


def _parse_run(reader: _Reader) -> RunConfig:
    """Valida a seção ``run`` (FR-012 a FR-014)."""
    reader.check_unknown_keys(
        (
            "log_level",
            "log_file",
            "rejection_report",
            "checkpoint_file",
            "dry_run",
            "resume",
        )
    )
    log_level = reader.string("log_level", default=logging_setup.DEFAULT_LOG_LEVEL)
    # Falha aqui, e não na configuração do log, para manter a validação única.
    logging_setup.resolve_level(log_level, key=reader.label("log_level"))
    return RunConfig(
        log_level=log_level.upper(),
        log_file=reader.string("log_file"),
        rejection_report=reader.string(
            "rejection_report", default=DEFAULT_REJECTION_REPORT
        ),
        checkpoint_file=reader.string(
            "checkpoint_file", default=DEFAULT_CHECKPOINT_FILE
        ),
        dry_run=reader.boolean("dry_run"),
        resume=reader.boolean("resume"),
    )


def _check_column_references(
    mapping: MappingConfig, validation: ValidationConfig, load: LoadConfig
) -> None:
    """Garante que toda coluna citada exista no mapeamento (FR-003)."""
    known = set(mapping.columns.values())
    references: list[tuple[str, Sequence[str]]] = [
        ("mapping.types", tuple(mapping.types)),
        ("mapping.normalizers", tuple(mapping.normalizers)),
        ("validation.required", validation.required),
        ("validation.ranges", tuple(validation.ranges)),
        ("validation.max_lengths", tuple(validation.max_lengths)),
        ("validation.business_key", validation.business_key),
        ("load.unique_key", load.unique_key),
    ]
    for key, columns in references:
        for column in columns:
            if column not in known:
                raise ConfigError(
                    messages.ERR_CONFIG_UNKNOWN_COLUMN.format(key=key, column=column)
                )


# --------------------------------------------------------------------------
# API pública
# --------------------------------------------------------------------------


def parse_config(
    raw: Mapping[str, Any],
    *,
    env: Mapping[str, str] | None = None,
    overrides: Mapping[str, Any] | None = None,
) -> EtlConfig:
    """Valida ``raw`` e devolve a configuração completa do pipeline.

    Aplica, nesta ordem, as variáveis de ambiente e as sobreposições
    explícitas sobre os valores do arquivo, valida tudo de uma vez e registra
    a senha do banco para redação nos logs (NFR-004).

    :param raw: configuração já desserializada.
    :param env: mapa de variáveis de ambiente; ``None`` usa ``os.environ``.
    :param overrides: valores de maior precedência, com chaves em caminho
        pontilhado (por exemplo ``{"load.batch_size": 500}``); valores ``None``
        são ignorados, o que permite repassar argumentos opcionais da CLI.
    :raises ConfigError: na primeira inconsistência encontrada.
    """
    if not isinstance(raw, Mapping):
        raise ConfigError(messages.ERR_CONFIG_NOT_AN_OBJECT.format(key="(raiz)"))

    merged, origins = _apply_overrides(
        raw, os.environ if env is None else env, overrides
    )

    root = _Reader(merged, "", origins)
    root.check_unknown_keys(_SECTIONS)

    mapping = _parse_mapping(root.section("mapping"))
    validation = _parse_validation(root.section("validation"))
    load = _parse_load(root.section("load"))
    _check_column_references(mapping, validation, load)

    database = _parse_database(root.section("database"))
    logging_setup.register_secret(database.password)

    dimensions: list[DimensionConfig] = []
    # A seção 'dimensions' é opcional e deve ser uma lista de objetos
    raw_dimensions = root.raw("dimensions")
    if raw_dimensions:
        if not isinstance(raw_dimensions, Sequence):
            raise ConfigError(
                messages.ERR_CONFIG_INVALID_VALUE.format(
                    key="dimensions", reason="deve ser uma lista"
                )
            )
        for i, raw_dim in enumerate(raw_dimensions):
            if not isinstance(raw_dim, Mapping):
                raise ConfigError(
                    messages.ERR_CONFIG_INVALID_VALUE.format(
                        key=f"dimensions[{i}]", reason="deve ser um objeto"
                    )
                )
            dim_reader = _Reader(raw_dim, f"dimensions[{i}]", origins)
            dim_reader.check_unknown_keys(("mapping", "validation", "load"))
            
            dim_mapping = _parse_mapping(dim_reader.section("mapping"))
            dim_validation = _parse_validation(dim_reader.section("validation"))
            dim_load = _parse_load(dim_reader.section("load"))
            _check_column_references(dim_mapping, dim_validation, dim_load)
            
            dimensions.append(
                DimensionConfig(
                    mapping=dim_mapping,
                    validation=dim_validation,
                    load=dim_load,
                )
            )

    return EtlConfig(
        source=_parse_source(root.section("source")),
        mapping=mapping,
        validation=validation,
        database=database,
        load=load,
        run=_parse_run(root.section("run")),
        dimensions=dimensions,
    )


def load_config(
    path: str | os.PathLike[str],
    *,
    env: Mapping[str, str] | None = None,
    overrides: Mapping[str, Any] | None = None,
) -> EtlConfig:
    """Lê o arquivo JSON em ``path`` e devolve a configuração validada.

    Nenhum outro arquivo é aberto e nenhuma conexão é estabelecida: a
    validação é concluída antes de qualquer acesso à planilha ou ao banco
    (FR-011).

    :raises ConfigError: se o arquivo não existir, não puder ser lido, não for
        um JSON válido ou contiver valores inconsistentes.
    """
    try:
        with open(path, encoding="utf-8") as handle:
            raw = json.load(handle)
    except FileNotFoundError as error:
        raise ConfigError(
            messages.ERR_CONFIG_FILE_NOT_FOUND.format(path=path), cause=error
        ) from error
    except json.JSONDecodeError as error:
        raise ConfigError(
            messages.ERR_CONFIG_INVALID_FORMAT.format(path=path, reason=error.msg),
            cause=error,
        ) from error
    except OSError as error:
        raise ConfigError(
            messages.ERR_CONFIG_FILE_UNREADABLE.format(
                path=path, reason=error.strerror or str(error)
            ),
            cause=error,
        ) from error

    if isinstance(raw, Mapping):
        # Se a seção 'mapping' for uma string, carregamos o mapeamento do arquivo
        # indicado (FR-011, eliminando redundância entre config.json e full_mapping.json).
        mapping_ref = raw.get("mapping")
        if isinstance(mapping_ref, str):
            mapping_path = os.path.join(
                os.path.dirname(os.path.abspath(path)), mapping_ref
            )
            try:
                with open(mapping_path, encoding="utf-8") as m_handle:
                    raw["mapping"] = json.load(m_handle)
            except FileNotFoundError as error:
                raise ConfigError(
                    messages.ERR_CONFIG_FILE_NOT_FOUND.format(path=mapping_path),
                    cause=error,
                ) from error
            except json.JSONDecodeError as error:
                raise ConfigError(
                    messages.ERR_CONFIG_INVALID_FORMAT.format(
                        path=mapping_path, reason=error.msg
                    ),
                    cause=error,
                ) from error
            except OSError as error:
                raise ConfigError(
                    messages.ERR_CONFIG_FILE_UNREADABLE.format(
                        path=mapping_path, reason=error.strerror or str(error)
                    ),
                    cause=error,
                ) from error

    return parse_config(raw, env=env, overrides=overrides)
