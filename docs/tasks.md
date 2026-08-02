# Technical Task List

Enumerated implementation tasks derived from `docs/plan.md`, grouped into development phases.
Each task links to its plan item and to the requirement(s) it satisfies in `docs/requirements.md`.

Mark a task complete by changing `[ ]` to `[x]`.

---

## Phase 1 — Setup and Foundation

- [x] **1.** Create the `etl/` package with `__init__.py` and the empty modules `messages.py`, `errors.py`,
  `config.py`, `logging_setup.py`, `extract.py`, `pipeline.py`, `reporting.py`, `cli.py`, plus the
  sub-packages `transform/` and `load/`. — *Plan: A1 · Req: NFR-006*
- [x] **2.** Replace the sample content of `main.py` with a bootstrap that calls `etl.cli.main()` and exits
  with its return code. — *Plan: A1 · Req: FR-012, NFR-008*
- [x] **3.** Create `requirements.txt` declaring `openpyxl` and the MySQL driver (`mysql-connector-python`),
  pinned to major versions. — *Plan: A2 · Req: NFR-008*
- [x] **4.** Implement `etl/messages.py` with named `pt_BR` message constants/templates for errors, CLI help,
  progress lines and the run summary. — *Plan: A3 · Req: NFR-007*
- [x] **5.** Implement `etl/errors.py` with `EtlError` and the subclasses `ConfigError`, `ExtractionError`,
  `MappingError`, `ValidationError`, `RejectionThresholdExceeded`, `DatabaseConnectionError`, `LoadError`,
  each carrying a `pt_BR` message and an exit-code hint. — *Plan: A4 · Req: NFR-006, NFR-007, FR-012*
- [x] **6.** Implement `etl/logging_setup.py`: console handler, optional file handler, configurable level.
  — *Plan: A5 · Req: FR-013*
- [x] **7.** Add a logging filter/formatter that redacts password-like values from every log record.
  — *Plan: A5 · Req: NFR-004, FR-013*
- [x] **8.** Write `../tests/test_logging_setup.py` asserting level handling, file output and password redaction.
  — *Plan: H2, H5 · Req: FR-013, NFR-004, NFR-005*

> **Phase 1 notes**
> - The database exception is named `DatabaseConnectionError` (not `ConnectionError`) to avoid shadowing the
>   Python builtin; `docs/plan.md` items A4 and E1 were updated accordingly.
> - `etl/cli.py` ships a placeholder `main()` that prints `CLI_NOT_IMPLEMENTED` and returns exit code `70`,
>   so `python3 main.py` runs today; task 48 replaces it with the real `argparse` interface.
> - Exit codes are defined in `etl/errors.py`: `0` success, `1` unexpected, `2` config, `3` extraction,
>   `4` mapping, `5` validation, `6` rejection threshold, `7` connection, `8` load, `70` not implemented.
> - Dependencies are declared but not installed; run `python3 -m pip install -r requirements.txt` before
>   Phase 3.

## Phase 2 — Configuration

- [x] **9.** Define the configuration dataclasses `SourceConfig`, `MappingConfig`, `ValidationConfig`,
  `DatabaseConfig`, `LoadConfig` and `RunConfig` in `etl/config.py`. — *Plan: B1 · Req: FR-011*
- [x] **10.** Implement the configuration file parser producing those dataclasses. — *Plan: B1 · Req: FR-011*
- [x] **11.** Implement environment-variable overrides with precedence over file values (including
  `ETL_DB_PASSWORD`). — *Plan: B2 · Req: FR-011, NFR-004*
- [x] **12.** Implement fail-fast validation of all configuration keys (presence, type, range) raising
  `ConfigError` naming the offending key in `pt_BR`, executed before any file or database access.
  — *Plan: B3 · Req: FR-011, NFR-003*
- [x] **13.** Define and document default values for chunk size and batch size. — *Plan: B3 · Req: FR-002, FR-009*
- [x] **14.** Write `../tests/test_config.py` covering parsing, env overrides, defaults and each invalid-key error.
  — *Plan: H2 · Req: FR-011, NFR-005*

> **Phase 2 notes**
> - The configuration file format is **JSON**: it is covered by the standard library, so it adds no
>   dependency (NFR-008), and it represents the nested column mapping directly.
> - Precedence is defaults < file < `ETL_*` environment variables < explicit overrides. The override
>   dictionary uses dotted paths (`{"load.batch_size": 500}`) and ignores `None`, so the Phase 6 CLI can
>   forward optional arguments unchanged.
> - Error messages name the environment variable (`ETL_DB_PORT`) rather than the file path when the bad
>   value came from the environment, so the user knows where to fix it.
> - Unknown keys are rejected rather than ignored, which turns typos into fail-fast configuration errors.
> - `parse_config` calls `logging_setup.register_secret` on the database password, so the password is
>   redacted from every log line from that point on (NFR-004); `DatabaseConfig` also hides it from `repr`.
> - Defaults (task 13): chunk size `5000` rows, batch size `1000` records, header row `1`, MySQL port
>   `3306`, `3` connection retries with `1.0 s` initial backoff, load mode `append`, `isolate` on batch
>   error, `discard` on duplicate key, `rejeicoes.csv` as the rejection report.

## Phase 3 — Extraction

- [x] **15.** Implement the streaming `.xlsx` reader in `etl/extract.py` using `openpyxl`
  `read_only=True, data_only=True`. — *Plan: C1 · Req: FR-001, NFR-001*
- [x] **16.** Implement sheet selection: configured sheet name, defaulting to the first sheet.
  — *Plan: C1 · Req: FR-001*
- [x] **17.** Derive column names from the header row and expose rows as objects carrying values, sheet name
  and source row number. — *Plan: C1 · Req: FR-001, NFR-009*
- [x] **18.** Implement the chunking wrapper yielding lists of at most `chunk_size` rows.
  — *Plan: C2 · Req: FR-002, NFR-001*
- [x] **19.** Implement source error handling for missing path, unreadable/corrupt workbook, unsupported
  extension, missing sheet and empty sheet, raising `ExtractionError`. — *Plan: C3 · Req: FR-001, NFR-007*
- [x] **20.** Write `../tests/test_extract.py` with generated fixtures covering happy path, chunk boundaries, header
  derivation and every error case. — *Plan: H1, H2 · Req: FR-001, FR-002, NFR-005*
- [x] **21.** Add legacy `.xls` support behind the same iterator interface, or an explicit unsupported-format
  error when the dependency is absent. — *Plan: C4 · Req: FR-001*

> **Phase 3 notes**
> - Dependencies are installed in the project virtual environment; run the suite with
>   `.venv/bin/python -m unittest discover`. Under a bare `python3` the `.xlsx`/`.xls` tests skip instead
>   of failing, so a green run there does not mean full coverage.
> - `SourceRow` carries `sheet`, `number` (the row number as shown in Excel, 1-based) and `values` keyed by
>   source column name, which is what the rejection report needs (NFR-009).
> - Rows shorter than the header are padded with `None` and values past the last header column are dropped,
>   so every row exposes exactly the header's columns.
> - Fully blank rows are skipped without consuming a row number; a sheet whose data rows are all blank is
>   reported as empty.
> - Blank header cells receive the reserved name `__coluna_N__` (they cannot be mapped, but they keep the
>   following columns aligned); trailing blank headers are dropped; a repeated header name is rejected as
>   `ExtractionError` because it would make the mapping ambiguous.
> - An empty sheet is reported as `ERR_SHEET_EMPTY`, while a sheet that has rows but nothing at the
>   configured `header_row` is reported as `ERR_HEADER_MISSING`.
> - The empty-sheet error surfaces when the row iterator is consumed, not when the file is opened, because
>   the reader is lazy by design (NFR-001).
> - Legacy `.xls` (task 21) is read through `xlrd`, which converts date serials and booleans at read time so
>   both formats hand the same Python types to Phase 4. `xlrd` cannot *write* `.xls`, and the project does
>   not depend on a BIFF writer, so the `.xls` tests cover extension routing, unreadable files, the absent
>   dependency message and cell conversion, but not a full round trip.
> - `.junie/AGENTS.md` was updated with the virtual-environment commands; task 65 stays open for any further
>   layout change.

## Phase 4 — Transformation

- [x] **22.** Implement source→target column mapping in `etl/transform/mapping.py`, dropping unmapped columns.
  — *Plan: D1 · Req: FR-003*
- [x] **23.** Implement the startup check that every mapped source column exists in the header, raising
  `MappingError` listing all missing columns before any load. — *Plan: D1 · Req: FR-003*
- [x] **24.** Implement whitespace trimming and empty/whitespace-only → `None` conversion in
  `etl/transform/cleaning.py`. — *Plan: D2 · Req: FR-004*
- [x] **25.** Implement the per-column normalizer registry (uppercase, lowercase, strip punctuation, collapse
  spaces) applied only where configured. — *Plan: D2 · Req: FR-004*
- [x] **26.** Implement type coercion for `int`, `Decimal`, `date`, `datetime`, `bool` and `str` in
  `etl/transform/types.py`. — *Plan: D3 · Req: FR-005*
- [x] **27.** Implement Excel serial-number → date/datetime conversion and locale-aware decimal separators.
  — *Plan: D3 · Req: FR-005*
- [x] **28.** Make conversion failures return a typed failure result instead of raising, so the run continues.
  — *Plan: D3, D4 · Req: FR-005, FR-006*
- [x] **29.** Implement the validation engine in `etl/transform/validation.py` (required fields, ranges,
  lengths, conversion outcomes) producing a clean record or a `Rejection`. — *Plan: D4 · Req: FR-006*
- [x] **30.** Define the `Rejection` record with sheet name, source row number, column and `pt_BR` reason.
  — *Plan: D4 · Req: FR-006, NFR-009*
- [x] **31.** Implement the rejection threshold counter aborting the run with `RejectionThresholdExceeded`
  when the configured absolute/percentage limit is crossed. — *Plan: D5 · Req: FR-006*
- [x] **32.** Implement business-key deduplication in `etl/transform/dedup.py` with a memory-bounded seen-key
  set, and a no-op path when no key is configured. — *Plan: D6 · Req: FR-007, NFR-001*
- [x] **33.** Write `../tests/test_mapping.py`, `../tests/test_cleaning.py`, `../tests/test_types.py`, `../tests/test_validation.py` and
  `../tests/test_dedup.py` covering happy paths and every rejection reason. — *Plan: H2 · Req: FR-003…FR-007, NFR-005*

## Phase 5 — Loading

- [x] **34.** Implement the MySQL connection factory in `etl/load/connection.py` behind a small interface that
  tests can substitute. — *Plan: E1 · Req: FR-008, NFR-005*
- [x] **35.** Ensure connection failures raise `ConnectionError` with a `pt_BR` message that never contains
  the password. — *Plan: E1 · Req: FR-008, NFR-004*
- [x] **36.** Implement configurable retry with exponential backoff for initial connection and mid-run
  reconnection. — *Plan: E2 · Req: FR-008, NFR-003*
- [x] **37.** Implement pre-flight checks that the target table and all mapped target columns exist, aborting
  with a `pt_BR` message naming what is missing. — *Plan: E3 · Req: FR-010, FR-003*
- [x] **38.** Implement the batch inserter in `etl/load/loader.py` using parameterized `executemany` /
  multi-row `INSERT` with the configured batch size. — *Plan: E4 · Req: FR-009, NFR-002, NFR-004*
- [x] **39.** Commit after each successfully inserted batch. — *Plan: E4 · Req: FR-009, NFR-003*
- [x] **40.** Implement batch failure handling: rollback, then row-by-row isolation of the offending row or
  abort, per configuration. — *Plan: E5 · Req: FR-009, FR-006, NFR-003*
- [x] **41.** Implement load mode `append`. — *Plan: E6 · Req: FR-010*
- [x] **42.** Implement load mode `truncate` (empty the target before inserting). — *Plan: E6 · Req: FR-010*
- [x] **43.** Implement load mode `upsert` via `INSERT ... ON DUPLICATE KEY UPDATE` on the declared unique key.
  — *Plan: E6 · Req: FR-010, FR-015*
- [x] **44.** Build the fake connection/cursor test double recording executed statements and parameters.
  — *Plan: H1 · Req: NFR-005*
- [x] **45.** Write `../tests/test_connection.py` and `../tests/test_loader.py` covering retries, pre-flight checks, batching,
  commit/rollback and all three load modes. — *Plan: H2 · Req: FR-008…FR-010, NFR-003, NFR-005*

## Phase 6 — Orchestration, CLI and Reporting

- [x] **46.** Implement `etl/pipeline.py` wiring extract → chunk → map → clean → coerce → validate → dedup → load as a lazy iterator chain. — *Plan: F1 · Req: FR-001…FR-010, NFR-001*
- [x] **47.** Implement run lifecycle handling in the pipeline: counters, error propagation, connection
  teardown. — *Plan: F1 · Req: NFR-003, FR-014*
- [x] **48.** Implement the `argparse` CLI in `etl/cli.py` with the config path and overrides (source file,
  table, chunk/batch size, log level, `--verbose`) and `pt_BR` help text. — *Plan: F2 · Req: FR-012, FR-011*
- [x] **49.** Define and implement the exit codes: `0` on success and a distinct non-zero code per failure
  class. — *Plan: F2 · Req: FR-012*
- [x] **50.** Implement `--dry-run`, replacing the loader with a counting no-op while still producing the
  rejection report and summary. — *Plan: F3 · Req: FR-012, FR-006*
- [x] **51.** Implement the counters and per-chunk progress line in `etl/reporting.py` (read / transformed /
  loaded / rejected). — *Plan: F4 · Req: FR-014, FR-013*
- [x] **52.** Implement the end-of-run `pt_BR` summary with totals and elapsed time, printed on success and on
  failure. — *Plan: F5 · Req: FR-014, NFR-007*
- [x] **53.** Implement the CSV rejection-report writer (sheet, source row, column, reason) to the configured
  path. — *Plan: F6 · Req: FR-006, NFR-009*
- [x] **54.** Write `../tests/test_cli.py` and `../tests/test_reporting.py` covering argument parsing, exit codes, dry-run,
  progress output and report contents. — *Plan: H2 · Req: FR-012, FR-014, NFR-005*

## Phase 7 — Testing and Quality Assurance

- [x] **55.** Implement the fixture generator producing `.xlsx` workbooks with valid rows, bad types, missing
  required fields, duplicate keys and empty cells. — *Plan: H1 · Req: NFR-005*
- [x] **56.** Write the end-to-end `../tests/test_pipeline.py` running a fixture workbook through the whole chain
  against the fake connection, asserting loaded/rejected counts and exit code. — *Plan: H3 · Req: NFR-005, NFR-003*
- [x] **57.** Write the optional/slow memory test asserting bounded memory growth on a large generated file.
  — *Plan: H4 · Req: NFR-001*
- [x] **58.** Write the optional/slow throughput test measuring rows/minute against the NFR-002 target.
  — *Plan: H4 · Req: NFR-002*
- [x] **59.** Write security tests proving passwords never appear in logs, messages, summaries or tracebacks.
  — *Plan: H5 · Req: NFR-004*
- [x] **60.** Write a test asserting every data-carrying SQL statement uses parameter placeholders rather than
  interpolated values. — *Plan: H5 · Req: NFR-004*
- [x] **61.** Verify `python3 -m unittest discover` runs the full suite green from the project root.
  — *Plan: H2, H3 · Req: NFR-005*
- [x] **62.** Perform the PEP 8 pass over the whole package and add docstrings to all public functions and
  classes. — *Plan: H6 · Req: NFR-006*

## Phase 8 — Documentation

- [x] **63.** Write usage documentation: installation, configuration keys, environment variables, CLI options,
  exit codes and load modes. — *Plan: I1 · Req: NFR-008, FR-011, FR-012*
- [x] **64.** Update requirement statuses in `docs/requirements.md` to reflect delivered functionality.
  — *Plan: I2 · Req: NFR-010*
- [x] **65.** Update `.junie/AGENTS.md` if the run/test commands change as a result of the new package layout.
  — *Plan: I2 · Req: NFR-010*

## Phase 9 — Restartability

- [x] **66.** Implement `etl/checkpoint.py` persisting the last committed source row position after each
  batch commit. — *Plan: G1 · Req: FR-015*
- [x] **67.** Implement the `--resume` flag skipping source rows up to the recorded checkpoint.
  — *Plan: G2 · Req: FR-015*
- [x] **68.** Write `../tests/test_checkpoint.py` covering checkpoint persistence, resume and the no-duplicate
  guarantee under `upsert`. — *Plan: H2 · Req: FR-015, NFR-005*

## Phase 10 — Dimension Tables Loading

- [x] **69.** Create configuration mappings for `tb_beneficiarios`, `tb_especialidades`, `tb_profissionais`, and `tb_usuarios`. — *Plan: J1 · Req: FR-016, FR-003*
- [x] **70.** Implement logic to extract unique records for each dimension table from the source data. — *Plan: J2 · Req: FR-016, FR-007*
- [x] **71.** Update the pipeline to sequence the loading of dimension tables before or alongside the main fact table. — *Plan: J3 · Req: FR-016*
- [x] **72.** Add unit tests for the new dimension table loading logic, ensuring correct deduplication and mapping. — *Plan: H2 · Req: FR-016, NFR-005*
- [x] **73.** Run integration tests to verify the full ETL process with multiple target tables. — *Plan: H3 · Req: FR-016, NFR-003*
