"""Testes de ponto de controle e retomada (Tarefa 68)."""

import os
import tempfile
import unittest
from etl.checkpoint import save_checkpoint, load_checkpoint, delete_checkpoint
from etl.config import EtlConfig, SourceConfig, MappingConfig, DatabaseConfig, LoadConfig, RunConfig, ValidationConfig
from etl.pipeline import Pipeline
from test_utils import generate_fixture_workbook, FakeConnection

class TestCheckpoint(unittest.TestCase):
    """Verifica persistência de checkpoints e lógica de retomada."""

    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.checkpoint_path = os.path.join(self._dir.name, "ckpt.json")

    def test_save_load_checkpoint(self):
        """Verifica as funções básicas de persistência."""
        save_checkpoint(self.checkpoint_path, 123)
        self.assertTrue(os.path.exists(self.checkpoint_path))
        
        row = load_checkpoint(self.checkpoint_path)
        self.assertEqual(row, 123)
        
        delete_checkpoint(self.checkpoint_path)
        self.assertFalse(os.path.exists(self.checkpoint_path))
        
        # Carregar inexistente
        self.assertIsNone(load_checkpoint(self.checkpoint_path))

    def test_pipeline_resume_skips_rows(self):
        """Verifica se o pipeline pula linhas quando resume está ativo."""
        workbook_path = os.path.join(self._dir.name, "test.xlsx")
        # Gera planilha com 7 linhas de dados (Alice, Bob, Sem ID, Alice Repetida, Carlos, Diana, Espaçoso)
        # Ver test_utils.generate_fixture_workbook
        generate_fixture_workbook(workbook_path)
        
        # Simula que já processamos até a linha 3 (Sem ID)
        save_checkpoint(self.checkpoint_path, 3)
        
        config = EtlConfig(
            source=SourceConfig(path=workbook_path, chunk_size=10),
            mapping=MappingConfig(columns={"id": "id", "nome": "nome"}),
            database=DatabaseConfig(host="h", database="db", user="u"),
            load=LoadConfig(table="t"),
            run=RunConfig(
                dry_run=True, 
                resume=True, 
                checkpoint_file=self.checkpoint_path,
                rejection_report=os.devnull
            ),
            validation=ValidationConfig()
        )
        
        pipeline = Pipeline(config)
        pipeline.run()
        
        # Se pulou as 3 primeiras linhas de DADOS:
        # Originalmente tem 7 linhas de dados.
        # Linha 2: Alice (row.number=2) -> Pula
        # Linha 3: Bob (row.number=3) -> Pula
        # Linha 4: Sem ID (row.number=4) -> PROCESSA
        # Espera ai, row.number 1 é o header. Alice é row.number 2.
        # Se salvei checkpoint 3, Alice (2) e Bob (3) devem ser pulados.
        # Restam: Sem ID (4), Alice Repetida (5), Carlos (6), Diana (7), Espaçoso (8) -> 5 linhas.
        
        # Vamos conferir generate_fixture_workbook em test_utils.py:
        # row 1: header
        # row 2: Alice
        # row 3: Bob
        # row 4: Sem ID
        # row 5: Alice Repetida
        # row 6: Carlos
        # row 7: Diana
        # row 8: Espaçoso
        
        # Se checkpoint é 3, pula row.number 2 e 3.
        # Processa row.number 4, 5, 6, 7, 8.
        # stats.read deve ser 5.
        
        self.assertEqual(pipeline.stats.read, 5)
        # O checkpoint deve ter sido removido ao final do sucesso
        self.assertFalse(os.path.exists(self.checkpoint_path))

    def test_loader_calls_on_success(self):
        """Verifica se o Loader chama o callback de sucesso para cada lote."""
        db_config = DatabaseConfig(host="h", database="db", user="u")
        load_config = LoadConfig(table="t", batch_size=2)
        mapping = MappingConfig(columns={"A": "col1"})
        conn = FakeConnection(table_columns=["col1"])
        
        from etl.load.loader import Loader
        loader = Loader(conn, db_config, load_config, mapping)
        
        batch = [
            (10, {"col1": "v1"}),
            (11, {"col1": "v2"}),
            (12, {"col1": "v3"}),
        ]
        
        checkpoints = []
        def cb(row):
            checkpoints.append(row)
            
        loader.load_batch(batch, on_success=cb)
        
        # Com batch_size=2:
        # Sub-lote 1: (10, 11) -> commit -> cb(11)
        # Sub-lote 2: (12) -> commit -> cb(12)
        self.assertEqual(checkpoints, [11, 12])

    def test_upsert_no_duplicates_on_resume(self):
        """
        Garante que o modo upsert evita duplicatas se o checkpoint falhar 
        e reprocessarmos o último lote. (Tarefa 68).
        """
        # Este teste é mais conceitual no FakeConnection, mas validamos a query gerada.
        db_config = DatabaseConfig(host="h", database="db", user="u")
        load_config = LoadConfig(table="t", mode="upsert", unique_key=("id",))
        mapping = MappingConfig(columns={"id": "id", "nome": "nome"})
        conn = FakeConnection(table_columns=["id", "nome"])
        
        from etl.load.loader import Loader
        loader = Loader(conn, db_config, load_config, mapping)
        
        batch = [(2, {"id": 1, "nome": "Alice"})]
        loader.load_batch(batch)
        
        sql, _ = conn.cursor_instance.executed[-1]
        self.assertIn("ON DUPLICATE KEY UPDATE", sql)
        self.assertIn("`nome` = VALUES(`nome`)", sql)
        self.assertNotIn("`id` = VALUES(`id`)", sql)
