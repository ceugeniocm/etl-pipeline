"""Testes da validação e limite de rejeições (tarefa 33).

Cobre as funcionalidades de ``etl/transform/validation.py`` (FR-006).
"""

import unittest

from etl.config import ValidationConfig
from etl.errors import RejectionThresholdExceeded
from etl.transform.types import CoercionFailure
from etl.transform.validation import (
    Rejection,
    RejectionThreshold,
    validate_row,
)


class TestValidation(unittest.TestCase):
    """Testes de regras de validação e controle de limite de erros."""

    def test_validate_row_happy_path(self):
        """Aceita linha que atende a todos os requisitos."""
        config = ValidationConfig(
            required=("id",),
            ranges={"valor": (0.0, 100.0)},
            max_lengths={"nome": 10},
        )
        values = {"id": 1, "valor": 50.0, "nome": "Junie"}
        result = validate_row(values, config, "Sheet1", 1)
        self.assertEqual(values, result)

    def test_validate_required_field_missing(self):
        """Gera rejeição para campo obrigatório ausente."""
        config = ValidationConfig(required=("id",))
        result = validate_row({"valor": 10}, config, "Sheet1", 1)
        self.assertIsInstance(result, list)
        self.assertEqual(1, len(result))
        self.assertEqual("id", result[0].column)
        self.assertIn("obrigatório", result[0].reason)

    def test_validate_value_out_of_range(self):
        """Gera rejeição para valor fora da faixa permitida."""
        config = ValidationConfig(ranges={"valor": (0, 10)})
        result = validate_row({"valor": 15}, config, "Sheet1", 1)
        self.assertIsInstance(result, list)
        self.assertEqual("valor", result[0].column)
        self.assertIn("intervalo", result[0].reason)

    def test_validate_max_length_exceeded(self):
        """Gera rejeição para texto que excede o comprimento máximo."""
        config = ValidationConfig(max_lengths={"nome": 5})
        result = validate_row({"nome": "Muito Longo"}, config, "Sheet1", 1)
        self.assertIsInstance(result, list)
        self.assertEqual("nome", result[0].column)
        self.assertIn("limite", result[0].reason)

    def test_validate_handles_coercion_failure(self):
        """Prioriza o erro de conversão de tipo sobre outras validações."""
        config = ValidationConfig(required=("a",), ranges={"a": (0, 10)})
        # Se 'a' falhou na conversão, reportamos isso primeiro.
        values = {"a": CoercionFailure("texto", "int")}
        result = validate_row(values, config, "Sheet1", 1)
        self.assertIsInstance(result, list)
        self.assertEqual("a", result[0].column)
        self.assertIn("int", result[0].reason)

    def test_multiple_rejections_in_same_row(self):
        """Reporta todos os problemas encontrados em uma única linha."""
        config = ValidationConfig(required=("id",), max_lengths={"nome": 2})
        values = {"nome": "Junie"} # falta 'id' e 'nome' é longo
        result = validate_row(values, config, "Sheet1", 1)
        self.assertIsInstance(result, list)
        self.assertEqual(2, len(result))
        columns = [r.column for r in result]
        self.assertIn("id", columns)
        self.assertIn("nome", columns)

    def test_threshold_absolute_limit(self):
        """Aborta a execução ao atingir o número máximo de linhas rejeitadas."""
        config = ValidationConfig(max_rejected_rows=2)
        threshold = RejectionThreshold(config)
        
        threshold.count(is_rejected=False)
        threshold.count(is_rejected=True)  # 1
        threshold.count(is_rejected=True)  # 2 - no limite, ainda OK
        
        with self.assertRaises(RejectionThresholdExceeded) as context:
            threshold.count(is_rejected=True) # 3 - estoura
        self.assertIn("2", str(context.exception))
        self.assertIn("3", str(context.exception))

    def test_threshold_percent_limit(self):
        """Aborta a execução ao atingir o percentual máximo de rejeições."""
        config = ValidationConfig(max_rejected_percent=10.0)
        threshold = RejectionThreshold(config)
        
        # 1 erro em 10 linhas = 10% (OK)
        for _ in range(9):
            threshold.count(is_rejected=False)
        threshold.count(is_rejected=True)
        
        # Mais um erro = 2/11 = 18% > 10% (Erro)
        with self.assertRaises(RejectionThresholdExceeded):
            threshold.count(is_rejected=True)


if __name__ == "__main__":
    unittest.main()
