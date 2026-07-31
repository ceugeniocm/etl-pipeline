"""Teste de desempenho/throughput (Tarefa 58)."""

import os
import tempfile
import unittest
import time

try:
    import openpyxl
except ImportError:
    openpyxl = None

from etl.pipeline import Pipeline
from etl.config import (
    EtlConfig,
    SourceConfig,
    MappingConfig,
    DatabaseConfig,
    LoadConfig,
    RunConfig,
    ValidationConfig,
)

@unittest.skipUnless(openpyxl is not None, "openpyxl não instalado")
class TestPerformance(unittest.TestCase):
    """Verifica se o throughput atinge os objetivos de NFR-002."""

    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.path = os.path.join(self._dir.name, "perf.xlsx")

    def _generate_workbook(self, rows=5000):
        """Gera um arquivo .xlsx para teste de performance."""
        wb = openpyxl.Workbook(write_only=True)
        ws = wb.create_sheet()
        ws.append(["id", "nome"])
        for i in range(rows):
            ws.append([i, f"Nome {i}"])
        wb.save(self.path)

    def test_throughput_dry_run(self):
        # Objetivo: 10.000 linhas/minuto (NFR-002)
        rows = 5000
        self._generate_workbook(rows)
        
        config = EtlConfig(
            source=SourceConfig(path=self.path, chunk_size=1000),
            mapping=MappingConfig(columns={"id": "id", "nome": "nome"}),
            database=DatabaseConfig(host="h", database="db", user="u"),
            load=LoadConfig(table="t"),
            run=RunConfig(dry_run=True, rejection_report=os.devnull),
            validation=ValidationConfig()
        )
        
        start_time = time.time()
        pipeline = Pipeline(config)
        pipeline.run()
        duration = time.time() - start_time
        
        rows_per_minute = (rows / duration) * 60
        
        print(f"\nThroughput: {rows_per_minute:.2f} rows/min")
        self.assertGreaterEqual(
            rows_per_minute, 
            10000, 
            f"Throughput de {rows_per_minute:.2f} rows/min abaixo do alvo de 10.000"
        )
