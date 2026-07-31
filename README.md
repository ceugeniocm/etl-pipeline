# Big Data ETL Pipeline

This project is a high-performance ETL pipeline designed to extract data from large Excel files (.xlsx, .xls), transform and validate it, and load it into a MySQL database.

## Key Features
- **Memory Efficient**: Uses streaming and chunked reads to handle millions of rows without high memory consumption.
- **Robust Validation**: Configurable validation rules and rejection thresholds.
- **Flexible Loading**: Supports `append`, `truncate`, and `upsert` modes with batching and retry logic.
- **Observable**: Detailed logging and CSV rejection reports.

## Quick Start
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the pipeline with a configuration file:
   ```bash
   python3 main.py config.json
   ```

## Documentation
For detailed information on installation, configuration, and usage, see [docs/usage.md](docs/usage.md).

## Requirements
See [docs/requirements.md](docs/requirements.md) for the full specification.
