# Usage Documentation

This document describes how to install, configure, and run the ETL pipeline.

## Installation

### Prerequisites
- Python 3.8 or higher.
- Access to a MySQL database.

### Setup
1. Clone the repository.
2. Create and activate a virtual environment (optional but recommended):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Basic Usage

The pipeline is executed via `main.py` using a configuration file:

```bash
python3 main.py config.json
```

## CLI Options

The CLI supports several arguments that override the configuration file values:

| Option | Description |
|--------|-------------|
| `config` | Path to the JSON configuration file (positional, required). |
| `--source` | Path to the source Excel file (`.xlsx` or `.xls`). |
| `--sheet` | Name of the sheet to read (defaults to the first sheet). |
| `--table` | Name of the target MySQL table. |
| `--chunk-size` | Number of rows to read per chunk (memory efficiency). |
| `--batch-size` | Number of records to load per batch (performance). |
| `--mode` | Load mode (`append`, `truncate`, `upsert`). |
| `--log-level` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`). |
| `--log-file` | Path to a file to save logs. |
| `--dry-run` | Execute extraction, transformation, and validation without writing to the database. |
| `--verbose` | Shortcut for `--log-level DEBUG`. |
| `--resume` | Resume execution from the last recorded position in the checkpoint file. |
| `--help` | Show help message. |

## Configuration File

The configuration is a JSON file with the following sections:

### `source`
- `path` (string, required): Path to the Excel file.
- `sheet` (string, optional): Sheet name.
- `header_row` (integer, optional): 1-based index of the header row (default: 1).
- `chunk_size` (integer, optional): Rows per chunk (default: 5000).

### `mapping`
- `columns` (object, required): Map of source column names to target database column names.
- `types` (object, optional): Map of target column names to types (`str`, `int`, `decimal`, `float`, `bool`, `date`, `datetime`).
- `normalizers` (object, optional): Map of target column names to lists of normalizers (`trim`, `upper`, `lower`, `strip_punctuation`, `collapse_spaces`).

### `validation`
- `required` (array, optional): List of target column names that must not be null.
- `ranges` (object, optional): Map of target column names to `{ "minimum": X, "maximum": Y }`.
- `max_lengths` (object, optional): Map of target column names to maximum string length.
- `rejection_threshold` (string or integer, optional): Max absolute number of rejected rows (e.g., `100`) or percentage (e.g., `"5%"`).
- `business_key` (array, optional): List of target columns forming a business key for deduplication.
- `on_duplicate` (string, optional): Action for duplicate business keys (`discard` or `report`). Default: `discard`.

### `database`
- `host` (string, required): MySQL host.
- `port` (integer, optional): MySQL port (default: 3306).
- `database` (string, required): Database name.
- `user` (string, required): Database user.
- `password` (string, optional): Database password.
- `connect_retries` (integer, optional): Connection retry attempts (default: 3).
- `retry_backoff_seconds` (float, optional): Initial backoff in seconds (default: 1.0).

### `load`
- `table` (string, required): Target table name.
- `mode` (string, optional): Load mode (`append`, `truncate`, `upsert`). Default: `append`.
- `batch_size` (integer, optional): Records per batch (default: 1000).
- `unique_key` (array, optional): Columns for `ON DUPLICATE KEY UPDATE` in `upsert` mode.
- `on_batch_error` (string, optional): Action on batch failure (`isolate` or `abort`). Default: `isolate`.

### `run`
- `log_level` (string, optional): Default: `INFO`.
- `log_file` (string, optional): Path to log file.
- `rejection_report` (string, optional): Path to CSV rejection report (default: `rejeicoes.csv`).
- `checkpoint_file` (string, optional): Path to the JSON checkpoint file (default: `checkpoint.json`).
- `dry_run` (boolean, optional): Default: `false`.
- `resume` (boolean, optional): Default: `false`.

## Environment Variables

Environment variables can be used to override configuration values. They take precedence over the JSON file.

- `ETL_DB_PASSWORD`: Database password.
- `ETL_DB_USER`: Database user.
- `ETL_DB_HOST`: Database host.
- `ETL_DB_PORT`: Database port.
- `ETL_DB_NAME`: Database name.
- `ETL_SOURCE_PATH`: Source file path.
- `ETL_LOAD_TABLE`: Target table name.
- `ETL_LOG_LEVEL`: Log level.
- `ETL_DRY_RUN`: Enable dry run (`true`/`1`).
- `ETL_RESUME`: Enable resume mode (`true`/`1`).
- `ETL_CHECKPOINT_FILE`: Path to the checkpoint file.

## Load Modes

| Mode | Description |
|------|-------------|
| `append` | Inserts rows into the target table. Does not affect existing data. |
| `truncate` | Deletes all data from the target table before starting the load. |
| `upsert` | Updates existing rows if a unique key matches, otherwise inserts. Requires `unique_key` to be configured. |

## Exit Codes

The application returns the following exit codes:

| Code | Meaning |
|------|---------|
| 0 | SUCCESS |
| 1 | UNEXPECTED_ERROR |
| 2 | CONFIG_ERROR (Invalid or missing configuration) |
| 3 | EXTRACTION_ERROR (Failed to read source file) |
| 4 | MAPPING_ERROR (Mapping inconsistent with header) |
| 5 | VALIDATION_ERROR (Structural validation failure) |
| 6 | REJECTION_THRESHOLD (Rejection limit reached) |
| 7 | DATABASE_CONNECTION_ERROR (Failed to connect to MySQL) |
| 8 | LOAD_ERROR (Failed to write to database) |
| 70 | NOT_IMPLEMENTED (Feature not yet implemented) |
