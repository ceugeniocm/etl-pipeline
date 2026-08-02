"""Testes da coerção de tipos (tarefa 33).

Cobre as funcionalidades de ``etl/transform/types.py`` (FR-005).
"""

import unittest
from datetime import date, datetime
from decimal import Decimal

from etl.config import MappingConfig
from etl.transform.types import CoercionFailure, coerce_row


class TestTypes(unittest.TestCase):
    """Testes de conversão para int, decimal, bool, date e datetime."""

    def test_coerce_int(self):
        """Converte números e textos para inteiro."""
        config = MappingConfig(types={"a": "int"})
        self.assertEqual(10, coerce_row({"a": 10}, config)["a"])
        self.assertEqual(10, coerce_row({"a": "10"}, config)["a"])
        self.assertEqual(10, coerce_row({"a": 10.9}, config)["a"])
        # Separadores de milhar brasileiros (tarefa 27)
        self.assertEqual(1234, coerce_row({"a": "1.234"}, config)["a"])

    def test_coerce_decimal(self):
        """Converte para Decimal tratando separadores brasileiros."""
        config = MappingConfig(types={"a": "decimal"})
        self.assertEqual(Decimal("10.5"), coerce_row({"a": 10.5}, config)["a"])
        # Tarefa 27
        self.assertEqual(Decimal("1234.56"), coerce_row({"a": "1.234,56"}, config)["a"])
        self.assertEqual(Decimal("1234.56"), coerce_row({"a": "1234,56"}, config)["a"])

    def test_coerce_float(self):
        """Converte para float com suporte a separadores brasileiros."""
        config = MappingConfig(types={"a": "float"})
        self.assertEqual(1234.56, coerce_row({"a": "1.234,56"}, config)["a"])

    def test_coerce_bool(self):
        """Converte diversas formas de verdadeiro/falso."""
        config = MappingConfig(types={"a": "bool"})
        self.assertTrue(coerce_row({"a": True}, config)["a"])
        self.assertTrue(coerce_row({"a": "sim"}, config)["a"])
        self.assertTrue(coerce_row({"a": "S"}, config)["a"])
        self.assertTrue(coerce_row({"a": 1}, config)["a"])
        self.assertFalse(coerce_row({"a": False}, config)["a"])
        self.assertFalse(coerce_row({"a": "não"}, config)["a"])
        self.assertFalse(coerce_row({"a": "0"}, config)["a"])

    def test_coerce_date_and_datetime_from_serial(self):
        """Converte números de série do Excel (tarefa 27)."""
        config = MappingConfig(types={"d": "date", "dt": "datetime"})
        # 45138 é 2023-07-31
        values = {"d": 45138, "dt": 45138.75}
        result = coerce_row(values, config)
        self.assertEqual(date(2023, 7, 31), result["d"])
        self.assertEqual(datetime(2023, 7, 31, 18, 0), result["dt"])

    def test_coerce_date_and_datetime_from_iso(self):
        """Converte strings em formato ISO."""
        config = MappingConfig(types={"d": "date", "dt": "datetime"})
        values = {"d": "2023-07-31", "dt": "2023-07-31T18:00:00"}
        result = coerce_row(values, config)
        self.assertEqual(date(2023, 7, 31), result["d"])
        self.assertEqual(datetime(2023, 7, 31, 18, 0), result["dt"])

    def test_coerce_historical_dates(self):
        """Garante que datas anteriores a 1970 são tratadas corretamente (Tarefa 65)."""
        config = MappingConfig(types={"d": "date", "dt": "datetime"})
        # Caso reportado pelo usuário
        values = {"d": "1940-07-26", "dt": "1940-07-26T00:00:00"}
        result = coerce_row(values, config)
        self.assertEqual(date(1940, 7, 26), result["d"])
        self.assertEqual(datetime(1940, 7, 26, 0, 0), result["dt"])

    def test_coerce_date_from_datetime_object(self):
        """Extrai apenas a data se o destino for date e a origem for datetime."""
        config = MappingConfig(types={"d": "date"})
        values = {"d": datetime(2023, 7, 31, 18, 0)}
        result = coerce_row(values, config)
        self.assertEqual(date(2023, 7, 31), result["d"])
        self.assertNotIsInstance(result["d"], datetime)

    def test_coercion_failure_result(self):
        """Retorna CoercionFailure em vez de lançar exceção (tarefa 28)."""
        config = MappingConfig(types={"a": "int", "b": "date"})
        values = {"a": "texto", "b": "data-invalida"}
        result = coerce_row(values, config)
        
        self.assertIsInstance(result["a"], CoercionFailure)
        self.assertEqual("texto", result["a"].value)
        self.assertEqual("int", result["a"].target_type)
        
        self.assertIsInstance(result["b"], CoercionFailure)
        self.assertEqual("data-invalida", result["b"].value)
        self.assertEqual("date", result["b"].target_type)

    def test_none_is_preserved(self):
        """Mantém None sem tentar converter."""
        config = MappingConfig(types={"a": "int"})
        self.assertIsNone(coerce_row({"a": None}, config)["a"])


if __name__ == "__main__":
    unittest.main()
