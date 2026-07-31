"""Ponto de entrada da aplicação (FR-012, NFR-008).

Executar com::

    python3 main.py

O módulo apenas delega para :func:`etl.cli.main` e propaga o código de saída.
"""

import sys

from etl.cli import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
