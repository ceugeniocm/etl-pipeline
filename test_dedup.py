"""Testes da deduplicação (tarefa 33).

Cobre as funcionalidades de ``etl/transform/dedup.py`` (FR-007).
"""

import unittest

from etl.config import ValidationConfig
from etl.transform.dedup import Deduplicator
from etl.transform.validation import Rejection


class TestDedup(unittest.TestCase):
    """Testes de identificação de registros duplicados."""

    def test_no_business_key_configured(self):
        """Não rejeita nada se não houver chave de negócio."""
        config = ValidationConfig(business_key=())
        dedup = Deduplicator(config)
        
        self.assertIsNone(dedup.check({"id": 1}, "Sheet1", 1))
        self.assertIsNone(dedup.check({"id": 1}, "Sheet1", 2))

    def test_single_column_business_key(self):
        """Identifica duplicados com base em uma única coluna."""
        config = ValidationConfig(business_key=("id",))
        dedup = Deduplicator(config)
        
        # Primeira aparição
        self.assertIsNone(dedup.check({"id": 101, "valor": 50}, "Sheet1", 10))
        
        # Segunda aparição
        result = dedup.check({"id": 101, "valor": 60}, "Sheet1", 20)
        self.assertIsInstance(result, Rejection)
        self.assertEqual(20, result.row)
        self.assertIn("101", result.reason)
        self.assertIn("10", result.reason) # Linha da primeira aparição

    def test_composite_business_key(self):
        """Identifica duplicados com base em múltiplas colunas."""
        config = ValidationConfig(business_key=("loja", "sku"))
        dedup = Deduplicator(config)
        
        # Diferentes
        self.assertIsNone(dedup.check({"loja": 1, "sku": "A"}, "Sheet1", 1))
        self.assertIsNone(dedup.check({"loja": 1, "sku": "B"}, "Sheet1", 2))
        self.assertIsNone(dedup.check({"loja": 2, "sku": "A"}, "Sheet1", 3))
        
        # Duplicado
        result = dedup.check({"loja": 1, "sku": "A"}, "Sheet1", 4)
        self.assertIsInstance(result, Rejection)
        self.assertEqual(4, result.row)
        self.assertIn("(1, 'A')", result.reason)

    def test_clear_state(self):
        """Limpa o estado do deduplicador."""
        config = ValidationConfig(business_key=("id",))
        dedup = Deduplicator(config)
        
        dedup.check({"id": 1}, "Sheet1", 1)
        dedup.clear()
        
        # Após o clear, o mesmo ID é aceito novamente como primeira aparição
        self.assertIsNone(dedup.check({"id": 1}, "Sheet1", 2))


if __name__ == "__main__":
    unittest.main()
