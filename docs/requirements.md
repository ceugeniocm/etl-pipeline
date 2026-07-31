# Requirements Document

## Introduction

This document defines the high-level requirements for a **Big Data ETL pipeline** whose purpose is to
extract data from large Excel spreadsheet files, transform/validate that data, and load it into a
relational MySQL database.

The scope is derived from `docs/vision.md` and the project conventions in `.junie/AGENTS.md`.

Key functionality:

- **Extract**: read very large `.xlsx`/`.xls` workbooks without exhausting memory, using streaming/chunked reads.
- **Transform**: normalize, clean, type-cast, validate and map spreadsheet columns to the target schema.
- **Load**: write records into MySQL in batches, transactionally, with restart/idempotency support.
- **Operate**: configuration, logging, error reporting (messages in `pt_BR`), progress feedback and a CLI entry point.

Conventions that constrain these requirements:

- Python 3, executed via `python3 main.py`.
- Tests use the built-in `unittest` framework (`python3 -m unittest discover`), files named `test_<feature>.py`.
- Code style follows PEP 8.
- User-facing strings and error messages default to Portuguese (`pt_BR`); technical strings (identifiers,
  log level names, SQL, exception class names) remain in English (`en_US`).

Status legend: **Not Started**, **In Progress**, **Completed**, **Deferred**.

---

## Functional Requirements

### FR-001 — Excel file extraction

> **User Story**
> As a user, I want to point the pipeline at an Excel file so that its rows are read into the pipeline
> without me writing any parsing code.

**Acceptance Criteria**

> WHEN a valid `.xlsx` or `.xls` file path is supplied THEN the system SHALL open the workbook and expose its rows to the pipeline.
> WHEN the supplied path does not exist or is not a readable spreadsheet THEN the system SHALL abort with a clear `pt_BR` error message and a non-zero exit code.
> WHEN the workbook contains multiple sheets THEN the system SHALL read the sheet named in the configuration, defaulting to the first sheet when none is named.
> WHEN the first row is a header row THEN the system SHALL use it to derive column names.

- **Priority**: High
- **Status**: Not Started

### FR-002 — Streaming / chunked reading of large files

> **User Story**
> As a user, I want files with millions of rows to be processed in chunks so that the pipeline does not
> exhaust the machine's memory.

**Acceptance Criteria**

> WHEN a workbook larger than available memory is processed THEN the system SHALL read it in read-only/streaming mode and never materialize all rows at once.
> WHEN a chunk size is configured THEN the system SHALL emit batches of at most that many rows.
> WHEN no chunk size is configured THEN the system SHALL apply a documented default chunk size.

- **Priority**: High
- **Status**: Not Started

### FR-003 — Column mapping to the target schema

> **User Story**
> As a user, I want to declare how spreadsheet columns map to database columns so that I can load files
> whose headers do not match my table.

**Acceptance Criteria**

> WHEN a mapping between source column and target column is declared in the configuration THEN the system SHALL apply it to every extracted row.
> WHEN a mapped source column is missing from the workbook THEN the system SHALL abort before loading and report the missing column in `pt_BR`.
> WHEN a source column is not present in the mapping THEN the system SHALL ignore that column.

- **Priority**: High
- **Status**: Not Started

### FR-004 — Data cleaning and normalization

> **User Story**
> As a user, I want raw spreadsheet values to be cleaned automatically so that inconsistent input does not
> corrupt the database.

**Acceptance Criteria**

> WHEN a text value has leading or trailing whitespace THEN the system SHALL trim it.
> WHEN a cell is empty or contains only whitespace THEN the system SHALL convert it to `NULL`.
> WHEN a normalization rule (e.g. uppercase, strip punctuation) is configured for a column THEN the system SHALL apply it to that column only.

- **Priority**: High
- **Status**: Not Started

### FR-005 — Type conversion

> **User Story**
> As a user, I want spreadsheet values converted to the declared target types so that MySQL receives
> well-typed data.

**Acceptance Criteria**

> WHEN a column is declared as integer, decimal, date, datetime or boolean THEN the system SHALL convert each value to that Python type before loading.
> WHEN a value cannot be converted to the declared type THEN the system SHALL reject that row as invalid and continue processing the remaining rows.
> WHEN a date is stored as an Excel serial number THEN the system SHALL convert it to a proper date value.

- **Priority**: High
- **Status**: Not Started

### FR-006 — Row validation and rejection handling

> **User Story**
> As a user, I want invalid rows to be isolated instead of aborting the run so that a few bad records do
> not block the whole load.

**Acceptance Criteria**

> WHEN a row violates a validation rule (required field missing, bad type, value out of range) THEN the system SHALL not load that row and SHALL record it in a rejection report with the source row number and the reason in `pt_BR`.
> WHEN the run finishes THEN the system SHALL write the rejection report to a configurable output file.
> WHEN the number of rejected rows exceeds a configured threshold THEN the system SHALL abort the run and report the threshold breach.

- **Priority**: High
- **Status**: Not Started

### FR-007 — Deduplication

> **User Story**
> As a user, I want duplicate records detected so that the database is not polluted by repeated rows.

**Acceptance Criteria**

> WHEN a business key is configured THEN the system SHALL detect rows repeating a key already seen in the same run and SHALL discard or report them according to configuration.
> WHEN no business key is configured THEN the system SHALL load all valid rows unchanged.

- **Priority**: Medium
- **Status**: Not Started

### FR-008 — MySQL connection management

> **User Story**
> As a user, I want the pipeline to connect to my MySQL instance using configured credentials so that I do
> not have to hardcode them.

**Acceptance Criteria**

> WHEN host, port, database, user and password are provided by configuration THEN the system SHALL establish a MySQL connection using them.
> WHEN the connection cannot be established THEN the system SHALL abort with a `pt_BR` error message and a non-zero exit code, without printing the password.
> WHEN the connection drops mid-run THEN the system SHALL retry a configurable number of times with backoff before failing.

- **Priority**: High
- **Status**: Not Started

### FR-009 — Batch loading into MySQL

> **User Story**
> As a user, I want rows written in batches so that loading millions of records completes in a reasonable time.

**Acceptance Criteria**

> WHEN valid rows are ready THEN the system SHALL insert them using a multi-row/executemany batch statement of configurable size.
> WHEN a batch is inserted successfully THEN the system SHALL commit that batch.
> WHEN a batch insert fails THEN the system SHALL roll back that batch, report the failure, and either retry row-by-row to isolate the offending row or abort, according to configuration.

- **Priority**: High
- **Status**: Not Started

### FR-010 — Target table preparation and load mode

> **User Story**
> As a user, I want to choose how the target table is populated so that I can do full reloads or incremental loads.

**Acceptance Criteria**

> WHEN load mode is `append` THEN the system SHALL insert rows leaving existing data untouched.
> WHEN load mode is `truncate` THEN the system SHALL empty the target table before inserting.
> WHEN load mode is `upsert` and a unique key exists THEN the system SHALL update existing rows and insert new ones.
> WHEN the target table does not exist THEN the system SHALL abort with a `pt_BR` error naming the missing table.

- **Priority**: Medium
- **Status**: Not Started

### FR-011 — Configuration

> **User Story**
> As a user, I want all pipeline settings in one configuration source so that I can run different loads
> without changing code.

**Acceptance Criteria**

> WHEN a configuration file is supplied THEN the system SHALL load source file path, sheet, mapping, types, validation rules, database settings, chunk/batch sizes and load mode from it.
> WHEN an environment variable overrides a configuration value THEN the system SHALL prefer the environment variable.
> WHEN a required configuration key is missing or invalid THEN the system SHALL abort before any database write and report which key is wrong in `pt_BR`.

- **Priority**: High
- **Status**: Not Started

### FR-012 — Command-line interface

> **User Story**
> As a user, I want to launch the pipeline from the terminal so that I can run and automate it easily.

**Acceptance Criteria**

> WHEN `python3 main.py` is invoked with the configuration and/or input arguments THEN the system SHALL run the full extract–transform–load cycle.
> WHEN `--help` is passed THEN the system SHALL print usage information in `pt_BR`.
> WHEN a `--dry-run` flag is passed THEN the system SHALL execute extraction, transformation and validation but perform no database writes.
> WHEN the run completes successfully THEN the system SHALL exit with code `0`, otherwise with a non-zero code.

- **Priority**: High
- **Status**: Not Started

### FR-013 — Logging

> **User Story**
> As a user, I want the pipeline to log what it is doing so that I can diagnose problems after the fact.

**Acceptance Criteria**

> WHEN the pipeline runs THEN the system SHALL log start, per-stage progress, warnings, errors and completion using the standard `logging` module.
> WHEN a log verbosity level is configured THEN the system SHALL honour it.
> WHEN a log file path is configured THEN the system SHALL write logs to that file in addition to the console.
> WHEN credentials are part of the configuration THEN the system SHALL never write them to the logs.

- **Priority**: High
- **Status**: In Progress

### FR-014 — Progress reporting and run summary

> **User Story**
> As a user, I want progress feedback and a final summary so that I know how a long-running load is going
> and how it ended.

**Acceptance Criteria**

> WHEN a chunk finishes processing THEN the system SHALL report the number of rows read, transformed, loaded and rejected so far.
> WHEN the run ends THEN the system SHALL print a summary with total rows read, loaded, rejected and total elapsed time, in `pt_BR`.

- **Priority**: Medium
- **Status**: Not Started

### FR-015 — Restartability / idempotency

> **User Story**
> As a user, I want to resume an interrupted load so that I do not have to reprocess an entire huge file.

**Acceptance Criteria**

> WHEN a run is interrupted after committing N batches THEN the system SHALL record the last committed source row position.
> WHEN the same run is relaunched with a resume option THEN the system SHALL restart from the recorded position instead of the beginning.
> WHEN the same file is fully reloaded in `upsert` mode THEN the system SHALL not create duplicate rows.

- **Priority**: Low
- **Status**: Deferred

---

## Non-Functional Requirements

### NFR-001 — Memory efficiency

> **User Story**
> As a user, I want memory usage to stay bounded regardless of file size so that the pipeline runs on
> ordinary hardware.

**Acceptance Criteria**

> WHEN a file of any supported size is processed THEN the system SHALL keep resident memory proportional to the chunk size and not to the total row count.

- **Priority**: High
- **Status**: Not Started

### NFR-002 — Throughput

> **User Story**
> As a user, I want the load to be fast so that large files finish within an acceptable window.

**Acceptance Criteria**

> WHEN loading a well-formed dataset on reference hardware THEN the system SHALL sustain at least 10,000 rows per minute end to end.
> WHEN batch size is increased within configured limits THEN the system SHALL not degrade throughput.

- **Priority**: Medium
- **Status**: Not Started

### NFR-003 — Reliability and data integrity

> **User Story**
> As a user, I want failures to leave the database in a consistent state so that I can trust partial loads.

**Acceptance Criteria**

> WHEN a batch fails THEN the system SHALL ensure no partially applied batch remains committed.
> WHEN the pipeline reports N rows loaded THEN the target table SHALL contain exactly N new/updated rows for that run.

- **Priority**: High
- **Status**: Not Started

### NFR-004 — Security of credentials

> **User Story**
> As a user, I want database credentials handled safely so that they are not leaked.

**Acceptance Criteria**

> WHEN credentials are supplied THEN the system SHALL accept them via environment variables or a non-versioned configuration file.
> WHEN any log, error message, traceback or summary is produced THEN the system SHALL redact the password.
> WHEN SQL is executed THEN the system SHALL use parameterized statements only, never string interpolation of data values.

- **Priority**: High
- **Status**: In Progress

### NFR-005 — Testability and test coverage

> **User Story**
> As a developer, I want the pipeline covered by automated tests so that changes do not silently break it.

**Acceptance Criteria**

> WHEN `python3 -m unittest discover` is run from the project root THEN the system SHALL execute all tests and report success or failure.
> WHEN a new feature is added THEN it SHALL be accompanied by a `test_<feature>.py` test module.
> WHEN unit tests run THEN they SHALL not require a live MySQL server, using fakes/mocks instead.

- **Priority**: High
- **Status**: In Progress

### NFR-006 — Maintainability and code style

> **User Story**
> As a developer, I want a clean modular codebase so that extract, transform and load concerns can evolve
> independently.

**Acceptance Criteria**

> WHEN code is written THEN it SHALL follow PEP 8 and separate extract, transform, load, configuration and CLI into distinct modules.
> WHEN a public function or class is added THEN it SHALL carry a docstring.

- **Priority**: High
- **Status**: In Progress

### NFR-007 — Internationalization of messages

> **User Story**
> As a Brazilian user, I want messages in Portuguese so that the tool is understandable to my team.

**Acceptance Criteria**

> WHEN a user-facing message or error is emitted THEN the system SHALL render it in `pt_BR`.
> WHEN a technical string (SQL, identifier, exception class, log level) is emitted THEN the system SHALL keep it in `en_US`.
> WHEN a message is defined THEN it SHALL live in a central message catalogue rather than being scattered as inline literals.

- **Priority**: Medium
- **Status**: In Progress

### NFR-008 — Portability and dependencies

> **User Story**
> As a user, I want a simple, documented dependency set so that installation is straightforward.

**Acceptance Criteria**

> WHEN the project is installed THEN its third-party dependencies SHALL be declared in a `requirements.txt`.
> WHEN the application is started THEN it SHALL run on Python 3 via `python3 main.py` with no build step.

- **Priority**: Medium
- **Status**: In Progress

### NFR-009 — Observability of failures

> **User Story**
> As a user, I want failures to be traceable to a specific source row so that I can fix the spreadsheet.

**Acceptance Criteria**

> WHEN a row is rejected or a batch fails THEN the system SHALL report the originating sheet name and source row number.

- **Priority**: Medium
- **Status**: Not Started

### NFR-010 — Documentation

> **User Story**
> As a developer, I want the `docs/` directory to stay current so that the specification matches the code.

**Acceptance Criteria**

> WHEN a requirement, plan item or task changes THEN `docs/requirements.md`, `docs/plan.md` and `docs/tasks.md` SHALL be updated in the same change.

- **Priority**: Medium
- **Status**: In Progress

---

## Traceability Summary

| ID      | Title                                  | Priority | Status      |
|---------|----------------------------------------|----------|-------------|
| FR-001  | Excel file extraction                  | High     | Not Started |
| FR-002  | Streaming / chunked reading            | High     | Not Started |
| FR-003  | Column mapping                         | High     | Not Started |
| FR-004  | Data cleaning and normalization        | High     | Not Started |
| FR-005  | Type conversion                        | High     | Not Started |
| FR-006  | Row validation and rejection handling  | High     | Not Started |
| FR-007  | Deduplication                          | Medium   | Not Started |
| FR-008  | MySQL connection management            | High     | Not Started |
| FR-009  | Batch loading into MySQL               | High     | Not Started |
| FR-010  | Target table preparation and load mode | Medium   | Not Started |
| FR-011  | Configuration                          | High     | Not Started |
| FR-012  | Command-line interface                 | High     | Not Started |
| FR-013  | Logging                                | High     | In Progress |
| FR-014  | Progress reporting and run summary     | Medium   | Not Started |
| FR-015  | Restartability / idempotency           | Low      | Deferred    |
| NFR-001 | Memory efficiency                      | High     | Not Started |
| NFR-002 | Throughput                             | Medium   | Not Started |
| NFR-003 | Reliability and data integrity         | High     | Not Started |
| NFR-004 | Security of credentials                | High     | In Progress |
| NFR-005 | Testability and test coverage          | High     | In Progress |
| NFR-006 | Maintainability and code style         | High     | In Progress |
| NFR-007 | Internationalization of messages       | Medium   | In Progress |
| NFR-008 | Portability and dependencies           | Medium   | In Progress |
| NFR-009 | Observability of failures              | Medium   | Not Started |
| NFR-010 | Documentation                          | Medium   | In Progress |
