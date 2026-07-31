"""Teste de consumo de memória (Tarefa 57)."""

import os
import tempfile
import unittest
import resource

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
class TestMemory(unittest.TestCase):
    """
    Verifica se a memória permanece estável ao processar muitos registros (NFR-001).
    Este teste é lento pois gera e lê um arquivo grande.
    """

    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.path = os.path.join(self._dir.name, "large.xlsx")

    def _generate_large_workbook(self, rows=20000):
        """Gera um arquivo .xlsx grande de forma eficiente."""
        wb = openpyxl.Workbook(write_only=True)
        ws = wb.create_sheet()
        ws.append(["id", "nome"])
        for i in range(rows):
            ws.append([i, f"Registro de Teste Número {i}"])
        wb.save(self.path)

    def _get_peak_memory_kb(self):
        """Retorna o pico de memória residente (RSS) em KB."""
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

    def test_memory_usage_is_bounded(self):
        # 1. Gera o arquivo
        self._generate_large_workbook(20000)
        
        # 2. Mede memória antes
        mem_before = self._get_peak_memory_kb()
        
        # 3. Executa o pipeline (dry-run)
        config = EtlConfig(
            source=SourceConfig(path=self.path, chunk_size=500),
            mapping=MappingConfig(columns={"id": "id", "nome": "nome"}),
            database=DatabaseConfig(host="h", database="db", user="u"),
            load=LoadConfig(table="t"),
            run=RunConfig(dry_run=True, rejection_report=os.devnull),
            validation=ValidationConfig()
        )
        
        pipeline = Pipeline(config)
        success = pipeline.run()
        
        self.assertTrue(success)
        self.assertEqual(pipeline.stats.read, 20000)
        
        # 4. Mede memória depois
        mem_after = self._get_peak_memory_kb()
        
        # Diferença de pico
        growth_kb = mem_after - mem_before
        
        # Se o pipeline fosse carregar tudo em memória, 20 mil linhas do openpyxl
        # pesariam vários megabytes (estimado > 20MB).
        # Com streaming e chunks de 500, o crescimento do PICO deve ser mínimo
        # (overhead fixo do iterador do openpyxl e caches internos do Python).
        
        # No Linux, ru_maxrss é o pico. O crescimento aqui reflete o quanto o pico 
        # aumentou durante o run.
        # Definimos um limite conservador de 50MB de crescimento de pico para 20k rows.
        # (Se carregar tudo, passaria disso facilmente em implementações ingênuas).
        self.assertLess(growth_kb, 50 * 1024, f"Crescimento de memória excessivo: {growth_kb} KB")
