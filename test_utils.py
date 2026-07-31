"""Utilitários compartilhados para os testes (Phase 7)."""

import datetime
import os
from typing import Any

try:
    import openpyxl
except ImportError:
    openpyxl = None

def write_workbook(path, sheets):
    """Grava uma planilha .xlsx a partir de {aba: [linhas]}."""
    if openpyxl is None:
        raise ImportError("openpyxl não instalado")
    workbook = openpyxl.Workbook()
    workbook.remove(workbook.active)
    for name, rows in sheets.items():
        worksheet = workbook.create_sheet(title=name)
        for row in rows:
            worksheet.append(list(row))
    workbook.save(path)
    return path

def generate_fixture_workbook(path):
    """
    Gera uma planilha .xlsx com diversos cenários de teste (Tarefa 55):
    - Linhas válidas
    - Tipos inválidos
    - Campos obrigatórios ausentes
    - Chaves duplicadas
    - Células vazias
    """
    sheets = {
        "Sheet1": [
            ("id", "nome", "nascimento", "salario", "ativo"), # Header
            (1, "Alice", datetime.date(1990, 5, 20), 5000.50, "Sim"), # 1. Válido
            (2, "Bob", "data-errada", 3000.00, "Não"), # 2. Tipo inválido (nascimento)
            (None, "Sem ID", datetime.date(2000, 1, 1), 1000.00, "Sim"), # 3. Rejeitado (id obrigatório)
            (1, "Alice Repetida", datetime.date(1990, 5, 20), 5000.50, "Sim"), # 4. Duplicado (id=1)
            (4, "Carlos", datetime.date(1985, 10, 10), None, "Sim"), # 5. Célula vazia (salario)
            (5, "Diana", datetime.date(1995, 12, 12), 4000.00, ""), # 6. Vazia (ativo)
            (6, "  Espaçoso  ", datetime.date(1980, 1, 1), 2500.00, "Sim"), # 7. Trim
        ]
    }
    return write_workbook(path, sheets)

class FakeCursor:
    """Dublê de teste para o cursor do MySQL (tarefa 44)."""

    def __init__(self, table_columns: list[str] = None):
        self.executed: list[tuple[str, Any]] = []
        self.table_columns = table_columns or []
        self._results = []

    def execute(self, sql: str, params: Any = None):
        self.executed.append((sql, params))
        if "DESCRIBE" in sql:
            # Extrai o nome da tabela do DESCRIBE `tabela`
            self._results = [[col] for col in self.table_columns]

    def executemany(self, sql: str, seq_params: Any):
        self.executed.append((sql, seq_params))

    def fetchall(self) -> list[Any]:
        return self._results

    def close(self):
        pass

class FakeConnection:
    """Dublê de teste para a conexão do MySQL (tarefa 44)."""

    def __init__(self, table_columns: list[str] = None):
        self.cursor_instance = FakeCursor(table_columns)
        self.committed = 0
        self.rolled_back = 0
        self.closed = False

    def cursor(self, **kwargs):
        return self.cursor_instance

    def commit(self):
        self.committed += 1

    def rollback(self):
        self.rolled_back += 1

    def close(self):
        self.closed = True

    def is_connected(self):
        return True
