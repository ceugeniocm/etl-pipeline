# Implementation Plan

## Introduction

This plan translates `docs/requirements.md` into an ordered, grouped set of implementation items for the
Big Data ETL pipeline (Excel → transform → MySQL). Every item is explicitly linked to the requirement(s)
it satisfies and carries a priority.

Guiding decisions:

- **Language/runtime**: Python 3, no build step, entry point `python3 main.py` (NFR-008).
- **Package layout**: a single `etl/` package with one module per concern, keeping extract, transform,
  load, config, messages and CLI separate (NFR-006).
- **Extraction library**: `openpyxl` in `read_only=True` streaming mode for `.xlsx`; `pandas` is avoided
  as the primary reader because it materializes whole sheets (NFR-001).
- **Database driver**: `mysql-connector-python` (or `PyMySQL`) accessed only through a thin adapter, so the
  driver choice stays swappable and unit tests can inject a fake (NFR-005).
- **Streaming contract**: extraction yields an iterator of chunks; every stage consumes and produces
  iterators, so memory stays proportional to chunk size (NFR-001).
- **Messages**: all user-facing text lives in `etl/messages.py` as `pt_BR` constants; technical strings stay
  in English (NFR-007).
- **Tests**: `unittest`, files `test_<feature>.py` at the project root, no live MySQL needed (NFR-005).

### Target module layout

```
main.py                     # thin CLI bootstrap -> etl.cli
requirements.txt
etl/
    __init__.py
    messages.py             # pt_BR message catalogue
    errors.py               # exception hierarchy
    config.py               # config loading, env overrides, validation
    logging_setup.py        # logging configuration + credential redaction
    extract.py              # streaming Excel reader
    transform/
        __init__.py
        mapping.py          # source -> target column mapping
        cleaning.py         # trim, empty -> NULL, per-column normalizers
        types.py            # type coercion (int, decimal, date, datetime, bool)
        validation.py       # rule evaluation, rejection records
        dedup.py            # business-key deduplication
    load/
        __init__.py
        connection.py       # connection factory, retry/backoff
        loader.py           # batching, commit/rollback, load modes
    pipeline.py             # orchestration extract -> transform -> load
    reporting.py            # progress counters, run summary, rejection report
    cli.py                  # argparse, exit codes, --dry-run
    checkpoint.py           # (deferred) resume support
test_*.py                   # unittest modules
```

---

## Group A — Project Foundation

### A1. Create package skeleton and entry point
Create the `etl/` package with the module layout above (empty but importable), and reduce `main.py` to a
thin bootstrap that delegates to `etl.cli.main()` and propagates its exit code.
- **Requirements**: NFR-006, NFR-008, FR-012
- **Priority**: High

### A2. Declare dependencies
Add `requirements.txt` with the Excel reader and MySQL driver pinned to major versions; document the
install command in the docs.
- **Requirements**: NFR-008
- **Priority**: High

### A3. Message catalogue (`etl/messages.py`)
Centralize every user-facing string as a named `pt_BR` constant/template (errors, CLI help, progress,
summary). Technical tokens stay English.
- **Requirements**: NFR-007, and message-related criteria of FR-001, FR-003, FR-006, FR-008, FR-010, FR-011, FR-012, FR-014
- **Priority**: High

### A4. Exception hierarchy (`etl/errors.py`)
Define `EtlError` and subclasses: `ConfigError`, `ExtractionError`, `MappingError`, `ValidationError`,
`RejectionThresholdExceeded`, `DatabaseConnectionError`, `LoadError`. Each carries a `pt_BR` message and a
stable exit-code hint. The database error is named `DatabaseConnectionError` rather than `ConnectionError`
so it does not shadow the Python builtin of that name (PEP 8, NFR-006).
- **Requirements**: NFR-006, NFR-007, FR-001, FR-006, FR-008, FR-011, FR-012
- **Priority**: High

### A5. Logging setup (`etl/logging_setup.py`)
Configure the standard `logging` module: console handler, optional file handler, configurable level, and a
filter/formatter that redacts password-like values from any record.
- **Requirements**: FR-013, NFR-004
- **Priority**: High

---

## Group B — Configuration

### B1. Configuration model and loader (`etl/config.py`)
Load a configuration file (INI/JSON/YAML — one format, documented) into typed dataclasses:
`SourceConfig` (path, sheet, header row, chunk size), `MappingConfig` (column map, declared types,
normalizers), `ValidationConfig` (required fields, ranges, rejection threshold, business key),
`DatabaseConfig` (host, port, database, user, password, retries), `LoadConfig` (table, load mode, batch
size), `RunConfig` (log level, log file, rejection report path, dry-run).
- **Requirements**: FR-011, FR-002, FR-003, FR-006, FR-007, FR-008, FR-009, FR-010, FR-013
- **Priority**: High

### B2. Environment-variable overrides
Apply environment variables (e.g. `ETL_DB_PASSWORD`) on top of file values, with env taking precedence;
credentials are expected to arrive this way.
- **Requirements**: FR-011, NFR-004
- **Priority**: High

### B3. Configuration validation with fail-fast
Validate presence, types and ranges of every key **before** opening the source file or the database
connection; raise `ConfigError` naming the offending key in `pt_BR`. Apply documented defaults for chunk
size and batch size.
- **Requirements**: FR-011, FR-002, FR-009, NFR-003
- **Priority**: High

---

## Group C — Extraction

### C1. Streaming workbook reader (`etl/extract.py`)
Open `.xlsx` via `openpyxl` in `read_only=True` / `data_only=True` mode; select the configured sheet or the
first one; read the header row to derive column names; yield `Row` objects carrying values plus sheet name
and source row number.
- **Requirements**: FR-001, NFR-001, NFR-009
- **Priority**: High

### C2. Chunking
Wrap the row iterator so it yields lists of at most `chunk_size` rows; use the documented default when the
configuration omits it.
- **Requirements**: FR-002, NFR-001
- **Priority**: High

### C3. Source error handling
Detect missing path, unreadable/corrupt workbook, unsupported extension, missing configured sheet and
empty sheet; raise `ExtractionError` with the `pt_BR` message and a non-zero exit code.
- **Requirements**: FR-001, NFR-007
- **Priority**: High

### C4. Legacy `.xls` support
Add an alternate reader path for legacy `.xls` (e.g. `xlrd`) behind the same iterator interface, or reject
the format explicitly with a clear message if the dependency is unavailable.
- **Requirements**: FR-001
- **Priority**: Low

---

## Group D — Transformation

### D1. Column mapping (`etl/transform/mapping.py`)
Apply the configured source→target map to each row; drop unmapped source columns; verify at startup (from
the header row) that every mapped source column exists and raise `MappingError` listing the missing ones
before any load begins.
- **Requirements**: FR-003
- **Priority**: High

### D2. Cleaning and normalization (`etl/transform/cleaning.py`)
Trim whitespace on text; convert empty/whitespace-only cells to `None`; provide a registry of per-column
normalizers (uppercase, lowercase, strip punctuation, collapse inner spaces) applied only where configured.
- **Requirements**: FR-004
- **Priority**: High

### D3. Type coercion (`etl/transform/types.py`)
Convert values to the declared target types — `int`, `Decimal`, `date`, `datetime`, `bool`, `str` —
including Excel serial-date conversion and locale-aware decimal separators. A failed conversion produces a
typed conversion failure rather than an exception that kills the run.
- **Requirements**: FR-005
- **Priority**: High

### D4. Validation engine (`etl/transform/validation.py`)
Evaluate required-field, range, length and type-conversion outcomes per row; produce either a clean record
or a `Rejection(sheet, source_row, column, reason_pt_br)`; keep processing subsequent rows.
- **Requirements**: FR-006, FR-005, NFR-009
- **Priority**: High

### D5. Rejection threshold
Track the rejected-row count across the run and abort with `RejectionThresholdExceeded` once the configured
absolute/percentage threshold is crossed.
- **Requirements**: FR-006
- **Priority**: Medium

### D6. Deduplication (`etl/transform/dedup.py`)
When a business key is configured, keep a memory-bounded set of seen keys and discard or flag repeats
according to configuration; no-op when no key is configured.
- **Requirements**: FR-007, NFR-001
- **Priority**: Medium

---

## Group E — Loading

### E1. Connection factory (`etl/load/connection.py`)
Build a MySQL connection from `DatabaseConfig`; on failure raise `DatabaseConnectionError` with a `pt_BR` message
that never contains the password; expose the connection through a small interface so tests can substitute
a fake.
- **Requirements**: FR-008, NFR-004, NFR-005
- **Priority**: High

### E2. Retry with backoff
Retry connection establishment and mid-run reconnection a configurable number of times with exponential
backoff before failing the run.
- **Requirements**: FR-008, NFR-003
- **Priority**: Medium

### E3. Pre-flight target checks
Before loading, verify the target table exists and that every mapped target column exists in it; abort with
a `pt_BR` message naming the missing table/column.
- **Requirements**: FR-010, FR-003, NFR-003
- **Priority**: High

### E4. Batch inserter (`etl/load/loader.py`)
Accumulate validated records into batches of the configured size and insert them with a parameterized
`executemany` / multi-row `INSERT`; commit per successful batch.
- **Requirements**: FR-009, NFR-002, NFR-004
- **Priority**: High

### E5. Batch failure handling
On batch failure, roll back the transaction and then either (a) retry the batch row-by-row to isolate and
reject the offending row, or (b) abort — selected by configuration. Guarantee no partially committed batch.
- **Requirements**: FR-009, NFR-003, FR-006
- **Priority**: High

### E6. Load modes
Implement `append`, `truncate` (empty target inside the run's transaction boundary before inserting) and
`upsert` (`INSERT ... ON DUPLICATE KEY UPDATE` against the declared unique key).
- **Requirements**: FR-010, FR-015
- **Priority**: Medium

---

## Group F — Orchestration, CLI and Reporting

### F1. Pipeline orchestrator (`etl/pipeline.py`)
Wire extract → chunk → map → clean → coerce → validate → dedup → load as a lazy iterator chain; own the
run lifecycle, counters, error propagation and final teardown.
- **Requirements**: FR-001…FR-010, NFR-001, NFR-003
- **Priority**: High

### F2. CLI (`etl/cli.py`)
`argparse`-based interface accepting the config path plus overrides (source file, table, chunk/batch size,
log level, `--dry-run`, `--verbose`); `pt_BR` help text; exit `0` on success and documented non-zero codes
on each failure class.
- **Requirements**: FR-012, FR-011, NFR-007
- **Priority**: High

### F3. Dry-run mode
Run extraction, transformation and validation with the loader replaced by a no-op that only counts, so no
database write occurs; still produce the rejection report and summary.
- **Requirements**: FR-012, FR-006
- **Priority**: Medium

### F4. Progress reporting (`etl/reporting.py`)
Maintain counters for rows read / transformed / loaded / rejected and emit a progress line after each chunk.
- **Requirements**: FR-014, FR-013
- **Priority**: Medium

### F5. Run summary
On completion (success or failure), print a `pt_BR` summary: totals per counter and elapsed time.
- **Requirements**: FR-014, NFR-007
- **Priority**: Medium

### F6. Rejection report writer
Write all `Rejection` records to the configured output file (CSV) with sheet, source row, column and reason.
- **Requirements**: FR-006, NFR-009
- **Priority**: Medium

---

## Group G — Restartability

### G1. Checkpointing (`etl/checkpoint.py`)
Persist the last committed source row position after each successful batch commit.
- **Requirements**: FR-015
- **Priority**: Completed

### G2. Resume option
A `--resume` flag that reads the checkpoint and skips source rows up to the recorded position.
- **Requirements**: FR-015
- **Priority**: Completed

---

## Group H — Testing and Quality Assurance

### H1. Test fixtures
Generate small `.xlsx` fixtures programmatically (valid rows, bad types, missing required fields, duplicate
keys, empty cells) plus a fake MySQL connection/cursor recording executed statements.
- **Requirements**: NFR-005
- **Priority**: High

### H2. Unit tests per module
`test_config.py`, `test_extract.py`, `test_mapping.py`, `test_cleaning.py`, `test_types.py`,
`test_validation.py`, `test_dedup.py`, `test_connection.py`, `test_loader.py`, `test_reporting.py`,
`test_cli.py` — each covering happy path and the failure criteria of its requirements.
- **Requirements**: NFR-005, and the FR it covers
- **Priority**: High

### H3. Integration test with fake database
End-to-end `test_pipeline.py` running a fixture workbook through the whole chain against the fake
connection, asserting loaded/rejected counts and exit code.
- **Requirements**: NFR-005, NFR-003, FR-001…FR-014
- **Priority**: High

### H4. Memory and throughput checks
A generated large-fixture test asserting bounded memory growth and measuring rows/minute against the
NFR-002 target; marked slow/optional so the default suite stays fast.
- **Requirements**: NFR-001, NFR-002
- **Priority**: Medium

### H5. Security assertions
Tests proving passwords never appear in logs/messages/tracebacks and that all SQL carrying data uses
parameter placeholders.
- **Requirements**: NFR-004
- **Priority**: High

### H6. Style and docstring pass
PEP 8 review of the whole package and docstrings on all public functions/classes.
- **Requirements**: NFR-006
- **Priority**: Medium

---

## Group I — Documentation

### I1. Usage documentation
Document installation, configuration keys, environment variables, CLI options, exit codes and load modes.
- **Requirements**: NFR-008, FR-011, FR-012
- **Priority**: Medium

### I2. Keep specification documents in sync
Update `docs/requirements.md` statuses and `docs/tasks.md` checkboxes as work lands.
- **Requirements**: NFR-010
- **Priority**: Medium

---

## Requirement Coverage Matrix

| Requirement | Plan items |
|---|---|
| FR-001 | C1, C3, C4, F1, H2 |
| FR-002 | B1, B3, C2, F1 |
| FR-003 | B1, D1, E3, F1, H2 |
| FR-004 | D2, F1, H2 |
| FR-005 | D3, D4, F1, H2 |
| FR-006 | B1, D4, D5, E5, F3, F6, H2 |
| FR-007 | B1, D6, H2 |
| FR-008 | A4, B1, E1, E2, H2 |
| FR-009 | B1, B3, E4, E5, H2 |
| FR-010 | B1, E3, E6, H2 |
| FR-011 | A4, B1, B2, B3, F2, I1 |
| FR-012 | A1, A4, F2, F3, I1 |
| FR-013 | A5, B1, F4 |
| FR-014 | A3, F4, F5 |
| FR-015 | E6, G1, G2 |
| NFR-001 | C1, C2, D6, F1, H4 |
| NFR-002 | E4, H4 |
| NFR-003 | B3, E2, E3, E5, F1, H3 |
| NFR-004 | A5, B2, E1, E4, H5 |
| NFR-005 | E1, H1, H2, H3 |
| NFR-006 | A1, A4, H6 |
| NFR-007 | A3, A4, C3, F2, F5 |
| NFR-008 | A1, A2, I1 |
| NFR-009 | C1, D4, F6 |
| NFR-010 | I2 |
