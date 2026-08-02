"""Testes de carga de tabelas de dimensão (FR-016, Tarefa 72)."""

import os
import tempfile
import unittest
from unittest.mock import patch
from etl.pipeline import Pipeline
from etl.config import (
    EtlConfig, SourceConfig, MappingConfig, ValidationConfig,
    DatabaseConfig, LoadConfig, RunConfig, DimensionConfig
)
from tests.test_utils import write_workbook, FakeConnection

class TestDimensionLoading(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.workbook_path = os.path.join(self._dir.name, "dimensions.xlsx")
        
        # Workbook com dados repetidos para as dimensões
        sheets = {
            "Agenda": [
                ("AGM_ID", "PROF_ID", "PROF_NOME", "ESP_ID", "ESP_DESCRICAO"),
                (101, 10, "Dr. House", 1, "Diagnóstico"),
                (102, 10, "Dr. House", 1, "Diagnóstico"), # Prof 10 repetido
                (103, 11, "Dra. Cuddy", 2, "Endocrinologia"),
            ]
        }
        write_workbook(self.workbook_path, sheets)
        
        self.config = EtlConfig(
            source=SourceConfig(path=self.workbook_path, chunk_size=10),
            database=DatabaseConfig(host="h", database="db", user="u"),
            run=RunConfig(rejection_report=os.path.join(self._dir.name, "rej.csv")),
            # Fato
            mapping=MappingConfig(columns={"AGM_ID": "agm_id"}),
            validation=ValidationConfig(business_key=["agm_id"]),
            load=LoadConfig(table="tb_agendamentos"),
            # Dimensões
            dimensions=[
                DimensionConfig(
                    mapping=MappingConfig(columns={"PROF_ID": "id_profissional", "PROF_NOME": "nome"}),
                    validation=ValidationConfig(required=["id_profissional"]),
                    load=LoadConfig(table="tb_profissionais", mode="upsert", unique_key=["id_profissional"])
                ),
                DimensionConfig(
                    mapping=MappingConfig(columns={"ESP_ID": "id_especialidade", "ESP_DESCRICAO": "descricao"}),
                    validation=ValidationConfig(required=["id_especialidade"]),
                    load=LoadConfig(table="tb_especialidades", mode="upsert", unique_key=["id_especialidade"])
                )
            ]
        )

    @patch("etl.pipeline.get_connection")
    def test_dimension_loading_sequence_and_deduplication(self, mock_get_conn):
        """Verifica se as dimensões são carregadas antes da fato e deduplicadas."""
        conn = FakeConnection(
            table_columns=["id_profissional", "nome", "id_especialidade", "descricao", "agm_id"]
        )
        mock_get_conn.return_value = conn
        
        pipeline = Pipeline(self.config)
        success = pipeline.run()
        
        self.assertTrue(success)
        
        # Verifica se as dimensões foram carregadas
        executed_sqls = [sql for sql, _ in conn.cursor_instance.executed]
        
        # Encontra os índices das primeiras inserções de cada tabela
        idx_prof = -1
        idx_esp = -1
        idx_fato = -1
        
        for i, sql in enumerate(executed_sqls):
            if "INSERT INTO `tb_profissionais`" in sql and idx_prof == -1:
                idx_prof = i
            elif "INSERT INTO `tb_especialidades`" in sql and idx_esp == -1:
                idx_esp = i
            elif "INSERT INTO `tb_agendamentos`" in sql and idx_fato == -1:
                idx_fato = i
        
        # As dimensões devem vir antes da fato no primeiro bloco
        self.assertNotEqual(idx_prof, -1)
        self.assertNotEqual(idx_esp, -1)
        self.assertNotEqual(idx_fato, -1)
        self.assertLess(idx_prof, idx_fato)
        self.assertLess(idx_esp, idx_fato)
        
        # Verifica deduplicação (apenas 2 profissionais e 2 especialidades únicos)
        all_profs = []
        for sql, batch in conn.cursor_instance.executed:
            if "INSERT INTO `tb_profissionais`" in sql:
                all_profs.extend(batch)
        self.assertEqual(len(all_profs), 2)
        
        all_esps = []
        for sql, batch in conn.cursor_instance.executed:
            if "INSERT INTO `tb_especialidades`" in sql:
                all_esps.extend(batch)
        self.assertEqual(len(all_esps), 2)

    @patch("etl.pipeline.get_connection")
    def test_dimension_with_multiple_mappings_same_table(self, mock_get_conn):
        """Verifica se múltiplas dimensões para a mesma tabela (ex: usuários) funcionam."""
        sheets = {
            "Agenda": [
                ("AGM_ID", "USER1_ID", "USER1_NOME", "USER2_ID", "USER2_NOME"),
                (1, 10, "User A", 20, "User B"),
                (2, 20, "User B", 10, "User A"), # Invertido, mas IDs já vistos
                (3, 30, "User C", 10, "User A"), # Novo user 30
            ]
        }
        write_workbook(self.workbook_path, sheets)
        
        self.config = replace(self.config, dimensions=[
            DimensionConfig(
                mapping=MappingConfig(columns={"USER1_ID": "id_user", "USER1_NOME": "nome"}),
                validation=ValidationConfig(required=["id_user"]),
                load=LoadConfig(table="tb_users", mode="upsert", unique_key=["id_user"])
            ),
            DimensionConfig(
                mapping=MappingConfig(columns={"USER2_ID": "id_user", "USER2_NOME": "nome"}),
                validation=ValidationConfig(required=["id_user"]),
                load=LoadConfig(table="tb_users", mode="upsert", unique_key=["id_user"])
            )
        ])
        
        conn = FakeConnection(table_columns=["id_user", "nome", "agm_id"])
        mock_get_conn.return_value = conn
        
        pipeline = Pipeline(self.config)
        pipeline.run()
        
        all_users = []
        for sql, batch in conn.cursor_instance.executed:
            if "INSERT INTO `tb_users`" in sql:
                all_users.extend(batch)
        
        # Devem ser 3 usuários únicos: 10, 20, 30
        self.assertEqual(len(all_users), 3)
        user_ids = {u[0] for u in all_users}
        self.assertEqual(user_ids, {10, 20, 30})

from dataclasses import replace
