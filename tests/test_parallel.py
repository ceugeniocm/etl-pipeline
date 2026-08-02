import os
import tempfile
import unittest
from dataclasses import replace
from etl.pipeline import Pipeline
from etl.config import (
    EtlConfig,
    SourceConfig,
    MappingConfig,
    ValidationConfig,
    DatabaseConfig,
    LoadConfig,
    RunConfig,
)
from test_utils import generate_fixture_workbook

class TestParallelPipeline(unittest.TestCase):
    """Verifica se o pipeline funciona corretamente com múltiplos workers (FR-017)."""

    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.workbook_path = os.path.join(self._dir.name, "test_parallel.xlsx")
        # Gera as 7 linhas padrão
        generate_fixture_workbook(self.workbook_path)
        self.rejection_report = os.path.join(self._dir.name, "rejeicoes_parallel.csv")
        
        self.config = EtlConfig(
            source=SourceConfig(path=self.workbook_path, chunk_size=5),
            mapping=MappingConfig(
                columns={
                    "id": "id_pk",
                    "nome": "nome_cli",
                    "nascimento": "dt_nasc",
                    "salario": "vl_sal",
                    "ativo": "is_ativo",
                },
                types={
                    "id_pk": "int",
                    "dt_nasc": "date",
                    "vl_sal": "decimal",
                },
            ),
            validation=ValidationConfig(
                required=["id_pk", "nome_cli"],
                business_key=["id_pk"],
            ),
            database=DatabaseConfig(host="h", database="db", user="u"),
            load=LoadConfig(table="my_table", batch_size=2),
            run=RunConfig(
                rejection_report=self.rejection_report,
                dry_run=True,
                workers=2  # Ativa o paralelismo
            )
        )

    def test_parallel_execution_counts(self):
        """Verifica se as contagens batem usando 2 workers."""
        pipeline = Pipeline(self.config)
        success = pipeline.run()
        
        self.assertTrue(success)
        self.assertEqual(pipeline.stats.read, 7)
        # Se os dados forem os mesmos do fixture padrão:
        # 1 válido, 5 (salario null), 6 (ativo null), 7 (trim) -> 4 carregados
        self.assertEqual(pipeline.stats.loaded, 4)
        # 2 (data errada), 3 (id null), 4 (duplicado id=1) -> 3 rejeitados
        self.assertEqual(pipeline.stats.rejected, 3)

    def test_compare_sequential_vs_parallel(self):
        """Garante que o resultado é idêntico entre 1 worker e 2 workers."""
        # 1. Sequencial
        cfg_seq = replace(self.config, run=replace(self.config.run, workers=1))
        pipe_seq = Pipeline(cfg_seq)
        pipe_seq.run()
        
        # 2. Paralelo
        cfg_par = replace(self.config, run=replace(self.config.run, workers=2))
        pipe_par = Pipeline(cfg_par)
        pipe_par.run()
        
        # Comparação
        self.assertEqual(pipe_seq.stats.read, pipe_par.stats.read)
        self.assertEqual(pipe_seq.stats.loaded, pipe_par.stats.loaded)
        self.assertEqual(pipe_seq.stats.rejected, pipe_par.stats.rejected)
        self.assertEqual(pipe_seq.stats.transformed, pipe_par.stats.transformed)
        self.assertEqual(pipe_seq.stats.duplicated, pipe_par.stats.duplicated)

if __name__ == "__main__":
    unittest.main()
