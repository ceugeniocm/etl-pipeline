"""Testes de ponta a ponta do pipeline (Tarefa 56)."""

import os
import tempfile
import unittest
from dataclasses import replace
from unittest.mock import patch

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
from etl.errors import RejectionThresholdExceeded
from test_utils import generate_fixture_workbook, FakeConnection

class TestPipeline(unittest.TestCase):
    """Cobre a integração de todas as fases no Pipeline."""

    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.workbook_path = os.path.join(self._dir.name, "test.xlsx")
        generate_fixture_workbook(self.workbook_path)
        self.rejection_report = os.path.join(self._dir.name, "rejeicoes.csv")
        
        # Configuração padrão para os testes
        self.config = EtlConfig(
            source=SourceConfig(path=self.workbook_path, chunk_size=10),
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
            run=RunConfig(rejection_report=self.rejection_report)
        )

    def test_pipeline_dry_run_full_cycle(self):
        """Executa o ciclo completo em dry-run e verifica contadores (Tarefa 50, 56)."""
        self.config = replace(self.config, run=replace(self.config.run, dry_run=True))
        pipeline = Pipeline(self.config)
        
        success = pipeline.run()
        
        self.assertTrue(success)
        # O fixture tem 7 linhas de dados + header
        self.assertEqual(pipeline.stats.read, 7)
        # 1 válido, 5 (salario null), 6 (ativo null), 7 (trim) -> 4 carregados
        self.assertEqual(pipeline.stats.loaded, 4)
        # 2 (data errada), 3 (id null), 4 (duplicado id=1) -> 3 rejeitados
        self.assertEqual(pipeline.stats.rejected, 3)
        self.assertEqual(pipeline.stats.duplicated, 1)
        
        # Verifica se o relatório de rejeições foi gerado
        self.assertTrue(os.path.exists(self.rejection_report))
        with open(self.rejection_report, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("data-errada", content)
            self.assertIn("id_pk", content)
            self.assertIn("Registro duplicado", content)

    @patch("etl.pipeline.get_connection")
    def test_pipeline_real_load(self, mock_get_conn):
        """Executa carga real usando a conexão falsa e verifica batching (Tarefa 38, 56)."""
        conn = FakeConnection(
            table_columns=["id_pk", "nome_cli", "dt_nasc", "vl_sal", "is_ativo"]
        )
        mock_get_conn.return_value = conn
        
        pipeline = Pipeline(self.config)
        success = pipeline.run()
        
        self.assertTrue(success)
        self.assertEqual(pipeline.stats.loaded, 4)
        
        # Com batch_size=2 e 4 linhas carregadas, devemos ter 2 commits de lote
        self.assertEqual(conn.committed, 2)
        
        # Verifica se as queries foram geradas corretamente
        executed_sqls = [sql for sql, _ in conn.cursor_instance.executed]
        self.assertTrue(any("INSERT INTO `my_table`" in sql for sql in executed_sqls))

    def test_pipeline_rejection_threshold_absolute(self):
        """Aborta se o limite absoluto de rejeições for ultrapassado (Tarefa 31)."""
        # Limite de 1 rejeição. Como temos 3 no fixture, deve abortar.
        self.config = replace(
            self.config, 
            validation=replace(self.config.validation, max_rejected_rows=1),
            run=replace(self.config.run, dry_run=True)
        )
        pipeline = Pipeline(self.config)
        
        with self.assertRaises(RejectionThresholdExceeded):
            pipeline.run()
            
    def test_pipeline_rejection_threshold_percentage(self):
        """Aborta se o limite percentual de rejeições for ultrapassado (Tarefa 31)."""
        # Limite de 10%. 3/7 ~ 42%, deve abortar.
        self.config = replace(
            self.config, 
            validation=replace(self.config.validation, max_rejected_percent=10.0),
            run=replace(self.config.run, dry_run=True)
        )
        pipeline = Pipeline(self.config)
        
        with self.assertRaises(RejectionThresholdExceeded):
            pipeline.run()
