# Technical Task List

Enumerated implementation tasks derived from `docs/plan.md`, grouped into development phases.
Each task links to its plan item and to the requirement(s) it satisfies in `docs/requirements.md`.

Mark a task complete by changing `[ ]` to `[x]`.

---

## Phase 1 — Setup and Foundation

- [ ] **1.** Create the `etl/` package with `__init__.py` and the empty modules `messages.py`, `errors.py`,
  `config.py`, `logging_setup.py`, `extract.py`, `pipeline.py`, `reporting.py`, `cli.py`, plus the
  sub-packages `transform/` and `load/`. — *Plan: A1 · Req: NFR-006*
- [ ] **2.** Replace the sample content of `main.py` with a bootstrap that calls `etl.cli.main()` and exits
  with its return code. — *Plan: A1 · Req: FR-012, NFR-008*
- [ ] **3.** Create `requirements.txt` declaring `openpyxl` and the MySQL driver (`mysql-connector-python`),
  pinned to major versions. — *Plan: A2 · Req: NFR-008*
- [ ] **4.** Implement `etl/messages.py` with named `pt_BR` message constants/templates for errors, CLI help,
  progress lines and the run summary. — *Plan: A3 · Req: NFR-007*
- [ ] **5.** Implement `etl/errors.py` with `EtlError` and the subclasses `ConfigError`, `ExtractionError`,
  `MappingError`, `ValidationError`, `RejectionThresholdExceeded`, `ConnectionError`, `LoadError`, each
  carrying a `pt_BR` message and an exit-code hint. — *Plan: A4 · Req: NFR-006, NFR-007, FR-012*
- [ ] **6.** Implement `etl/logging_setup.py`: console handler, optional file handler, configurable level.
  — *Plan: A5 · Req: FR-013*
- [ ] **7.** Add a logging filter/formatter that redacts password-like values from every log record.
  — *Plan: A5 · Req: NFR-004, FR-013*
- [ ] **8.** Write `test_logging_setup.py` asserting level handling, file output and password redaction.
  — *Plan: H2, H5 · Req: FR-013, NFR-004, NFR-005*

## Phase 2 — Configuration

- [ ] **9.** Define the configuration dataclasses `SourceConfig`, `MappingConfig`, `ValidationConfig`,
  `DatabaseConfig`, `LoadConfig` and `RunConfig` in `etl/config.py`. — *Plan: B1 · Req: FR-011*
- [ ] **10.** Implement the configuration file parser producing those dataclasses. — *Plan: B1 · Req: FR-011*
- [ ] **11.** Implement environment-variable overrides with precedence over file values (including
  `ETL_DB_PASSWORD`). — *Plan: B2 · Req: FR-011, NFR-004*
- [ ] **12.** Implement fail-fast validation of all configuration keys (presence, type, range) raising
  `ConfigError` naming the offending key in `pt_BR`, executed before any file or database access.
  — *Plan: B3 · Req: FR-011, NFR-003*
- [ ] **13.** Define and document default values for chunk size and batch size. — *Plan: B3 · Req: FR-002, FR-009*
- [ ] **14.** Write `test_config.py` covering parsing, env overrides, defaults and each invalid-key error.
  — *Plan: H2 · Req: FR-011, NFR-005*

## Phase 3 — Extraction

- [ ] **15.** Implement the streaming `.xlsx` reader in `etl/extract.py` using `openpyxl`
  `read_only=True, data_only=True`. — *Plan: C1 · Req: FR-001, NFR-001*
- [ ] **16.** Implement sheet selection: configured sheet name, defaulting to the first sheet.
  — *Plan: C1 · Req: FR-001*
- [ ] **17.** Derive column names from the header row and expose rows as objects carrying values, sheet name
  and source row number. — *Plan: C1 · Req: FR-001, NFR-009*
- [ ] **18.** Implement the chunking wrapper yielding lists of at most `chunk_size` rows.
  — *Plan: C2 · Req: FR-002, NFR-001*
- [ ] **19.** Implement source error handling for missing path, unreadable/corrupt workbook, unsupported
  extension, missing sheet and empty sheet, raising `ExtractionError`. — *Plan: C3 · Req: FR-001, NFR-007*
- [ ] **20.** Write `test_extract.py` with generated fixtures covering happy path, chunk boundaries, header
  derivation and every error case. — *Plan: H1, H2 · Req: FR-001, FR-002, NFR-005*
- [ ] **21.** Add legacy `.xls` support behind the same iterator interface, or an explicit unsupported-format
  error when the dependency is absent. — *Plan: C4 · Req: FR-001*

## Phase 4 — Transformation

- [ ] **22.** Implement source→target column mapping in `etl/transform/mapping.py`, dropping unmapped columns.
  — *Plan: D1 · Req: FR-003*
- [ ] **23.** Implement the startup check that every mapped source column exists in the header, raising
  `MappingError` listing all missing columns before any load. — *Plan: D1 · Req: FR-003*
- [ ] **24.** Implement whitespace trimming and empty/whitespace-only → `None` conversion in
  `etl/transform/cleaning.py`. — *Plan: D2 · Req: FR-004*
- [ ] **25.** Implement the per-column normalizer registry (uppercase, lowercase, strip punctuation, collapse
  spaces) applied only where configured. — *Plan: D2 · Req: FR-004*
- [ ] **26.** Implement type coercion for `int`, `Decimal`, `date`, `datetime`, `bool` and `str` in
  `etl/transform/types.py`. — *Plan: D3 · Req: FR-005*
- [ ] **27.** Implement Excel serial-number → date/datetime conversion and locale-aware decimal separators.
  — *Plan: D3 · Req: FR-005*
- [ ] **28.** Make conversion failures return a typed failure result instead of raising, so the run continues.
  — *Plan: D3, D4 · Req: FR-005, FR-006*
- [ ] **29.** Implement the validation engine in `etl/transform/validation.py` (required fields, ranges,
  lengths, conversion outcomes) producing a clean record or a `Rejection`. — *Plan: D4 · Req: FR-006*
- [ ] **30.** Define the `Rejection` record with sheet name, source row number, column and `pt_BR` reason.
  — *Plan: D4 · Req: FR-006, NFR-009*
- [ ] **31.** Implement the rejection threshold counter aborting the run with `RejectionThresholdExceeded`
  when the configured absolute/percentage limit is crossed. — *Plan: D5 · Req: FR-006*
- [ ] **32.** Implement business-key deduplication in `etl/transform/dedup.py` with a memory-bounded seen-key
  set, and a no-op path when no key is configured. — *Plan: D6 · Req: FR-007, NFR-001*
- [ ] **33.** Write `test_mapping.py`, `test_cleaning.py`, `test_types.py`, `test_validation.py` and
  `test_dedup.py` covering happy paths and every rejection reason. — *Plan: H2 · Req: FR-003…FR-007, NFR-005*

## Phase 5 — Loading

- [ ] **34.** Implement the MySQL connection factory in `etl/load/connection.py` behind a small interface that
  tests can substitute. — *Plan: E1 · Req: FR-008, NFR-005*
- [ ] **35.** Ensure connection failures raise `ConnectionError` with a `pt_BR` message that never contains
  the password. — *Plan: E1 · Req: FR-008, NFR-004*
- [ ] **36.** Implement configurable retry with exponential backoff for initial connection and mid-run
  reconnection. — *Plan: E2 · Req: FR-008, NFR-003*
- [ ] **37.** Implement pre-flight checks that the target table and all mapped target columns exist, aborting
  with a `pt_BR` message naming what is missing. — *Plan: E3 · Req: FR-010, FR-003*
- [ ] **38.** Implement the batch inserter in `etl/load/loader.py` using parameterized `executemany` /
  multi-row `INSERT` with the configured batch size. — *Plan: E4 · Req: FR-009, NFR-002, NFR-004*
- [ ] **39.** Commit after each successfully inserted batch. — *Plan: E4 · Req: FR-009, NFR-003*
- [ ] **40.** Implement batch failure handling: rollback, then row-by-row isolation of the offending row or
  abort, per configuration. — *Plan: E5 · Req: FR-009, FR-006, NFR-003*
- [ ] **41.** Implement load mode `append`. — *Plan: E6 · Req: FR-010*
- [ ] **42.** Implement load mode `truncate` (empty the target before inserting). — *Plan: E6 · Req: FR-010*
- [ ] **43.** Implement load mode `upsert` via `INSERT ... ON DUPLICATE KEY UPDATE` on the declared unique key.
  — *Plan: E6 · Req: FR-010, FR-015*
- [ ] **44.** Build the fake connection/cursor test double recording executed statements and parameters.
  — *Plan: H1 · Req: NFR-005*
- [ ] **45.** Write `test_connection.py` and `test_loader.py` covering retries, pre-flight checks, batching,
  commit/rollback and all three load modes. — *Plan: H2 · Req: FR-008…FR-010, NFR-003, NFR-005*

## Phase 6 — Orchestration, CLI and Reporting

- [ ] **46.** Implement `etl/pipeline.py` wiring extract → chunk → map → clean → coerce → validate → dedup →
  load as a lazy iterator chain. — *Plan: F1 · Req: FR-001…FR-010, NFR-001*
- [ ] **47.** Implement run lifecycle handling in the pipeline: counters, error propagation, connection
  teardown. — *Plan: F1 · Req: NFR-003, FR-014*
- [ ] **48.** Implement the `argparse` CLI in `etl/cli.py` with the config path and overrides (source file,
  table, chunk/batch size, log level, `--verbose`) and `pt_BR` help text. — *Plan: F2 · Req: FR-012, FR-011*
- [ ] **49.** Define and implement the exit codes: `0` on success and a distinct non-zero code per failure
  class. — *Plan: F2 · Req: FR-012*
- [ ] **50.** Implement `--dry-run`, replacing the loader with a counting no-op while still producing the
  rejection report and summary. — *Plan: F3 · Req: FR-012, FR-006*
- [ ] **51.** Implement the counters and per-chunk progress line in `etl/reporting.py` (read / transformed /
  loaded / rejected). — *Plan: F4 · Req: FR-014, FR-013*
- [ ] **52.** Implement the end-of-run `pt_BR` summary with totals and elapsed time, printed on success and on
  failure. — *Plan: F5 · Req: FR-014, NFR-007*
- [ ] **53.** Implement the CSV rejection-report writer (sheet, source row, column, reason) to the configured
  path. — *Plan: F6 · Req: FR-006, NFR-009*
- [ ] **54.** Write `test_cli.py` and `test_reporting.py` covering argument parsing, exit codes, dry-run,
  progress output and report contents. — *Plan: H2 · Req: FR-012, FR-014, NFR-005*

## Phase 7 — Testing and Quality Assurance

- [ ] **55.** Implement the fixture generator producing `.xlsx` workbooks with valid rows, bad types, missing
  required fields, duplicate keys and empty cells. — *Plan: H1 · Req: NFR-005*
- [ ] **56.** Write the end-to-end `test_pipeline.py` running a fixture workbook through the whole chain
  against the fake connection, asserting loaded/rejected counts and exit code. — *Plan: H3 · Req: NFR-005, NFR-003*
- [ ] **57.** Write the optional/slow memory test asserting bounded memory growth on a large generated file.
  — *Plan: H4 · Req: NFR-001*
- [ ] **58.** Write the optional/slow throughput test measuring rows/minute against the NFR-002 target.
  — *Plan: H4 · Req: NFR-002*
- [ ] **59.** Write security tests proving passwords never appear in logs, messages, summaries or tracebacks.
  — *Plan: H5 · Req: NFR-004*
- [ ] **60.** Write a test asserting every data-carrying SQL statement uses parameter placeholders rather than
  interpolated values. — *Plan: H5 · Req: NFR-004*
- [ ] **61.** Verify `python3 -m unittest discover` runs the full suite green from the project root.
  — *Plan: H2, H3 · Req: NFR-005*
- [ ] **62.** Perform the PEP 8 pass over the whole package and add docstrings to all public functions and
  classes. — *Plan: H6 · Req: NFR-006*

## Phase 8 — Documentation

- [ ] **63.** Write usage documentation: installation, configuration keys, environment variables, CLI options,
  exit codes and load modes. — *Plan: I1 · Req: NFR-008, FR-011, FR-012*
- [ ] **64.** Update requirement statuses in `docs/requirements.md` to reflect delivered functionality.
  — *Plan: I2 · Req: NFR-010*
- [ ] **65.** Update `.junie/AGENTS.md` if the run/test commands change as a result of the new package layout.
  — *Plan: I2 · Req: NFR-010*

## Phase 9 — Restartability (Deferred)

- [ ] **66.** Implement `etl/checkpoint.py` persisting the last committed source row position after each
  batch commit. — *Plan: G1 · Req: FR-015*
- [ ] **67.** Implement the `--resume` flag skipping source rows up to the recorded checkpoint.
  — *Plan: G2 · Req: FR-015*
- [ ] **68.** Write `test_checkpoint.py` covering checkpoint persistence, resume and the no-duplicate
  guarantee under `upsert`. — *Plan: H2 · Req: FR-015, NFR-005*
