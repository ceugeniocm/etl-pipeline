# Project Development Guide

## 1. Build/Configuration Instructions
This is a standard Python project. No complex build process is required. Ensure you have Python 3 installed.

Third-party dependencies (`openpyxl`, `mysql-connector-python`, `xlrd`) are declared in `requirements.txt`
and installed in the project virtual environment:

```bash
.venv/bin/python -m pip install -r requirements.txt
```

You can then run the application directly:

```bash
.venv/bin/python main.py
```

## 2. Testing Information
The project uses the built-in `unittest` framework.

### Running Tests
To run all tests in the project, use the following command from the root directory:

```bash
.venv/bin/python -m unittest discover
```

Use the virtual environment's interpreter: tests that need `openpyxl` or `xlrd` are **skipped**, not failed,
when the dependency is missing, so a bare `python3 -m unittest discover` reports a green run while silently
skipping the spreadsheet tests.

### Adding New Tests
When adding new features, create a corresponding test file named `test_<feature>.py` in the root directory. Use the `unittest` library to define your test cases.

Example test structure:
```python
import unittest
from main import print_hi

class TestMyFeature(unittest.TestCase):
    def test_something(self):
        # Your test logic here
        self.assertTrue(True)
```

## 3. Internationalization
- **Portuguese (pt_BR)**: Default language for UI strings and error messages.
- **English (en_US)**: Do not translate technical strings.

## 4. Additional Development Information
- **Code Style**: Follow PEP 8 guidelines.
- **Documentation**: Keep the `docs/` directory updated with relevant design and requirement information.

