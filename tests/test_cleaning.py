"""Testes da limpeza e normalização (tarefa 33).

Cobre as funcionalidades de ``etl/transform/cleaning.py`` (FR-004).
"""

import unittest

from etl.config import MappingConfig
from etl.transform.cleaning import clean_row


class TestCleaning(unittest.TestCase):
    """Testes de trim, conversão para None e normalizadores."""

    def test_global_cleaning(self):
        """Aplica trim e converte vazios em None para qualquer string."""
        config = MappingConfig()
        values = {
            "espacos": "  texto  ",
            "vazio": "   ",
            "nulo": None,
            "numero": 100,
        }
        result = clean_row(values, config)
        self.assertEqual("texto", result["espacos"])
        self.assertIsNone(result["vazio"])
        self.assertIsNone(result["nulo"])
        self.assertEqual(100, result["numero"])

    def test_upper_lower_normalizers(self):
        """Converte para maiúsculas e minúsculas."""
        config = MappingConfig(
            normalizers={"a": ("upper",), "b": ("lower",)}
        )
        values = {"a": "caixa alta", "b": "CAIXA BAIXA"}
        result = clean_row(values, config)
        self.assertEqual("CAIXA ALTA", result["a"])
        self.assertEqual("caixa baixa", result["b"])

    def test_strip_punctuation(self):
        """Remove pontuação conforme configurado."""
        config = MappingConfig(normalizers={"a": ("strip_punctuation",)})
        values = {"a": "Olá, Mundo!"}
        result = clean_row(values, config)
        self.assertEqual("Olá Mundo", result["a"])

    def test_collapse_spaces(self):
        """Reduz múltiplos espaços para um só."""
        config = MappingConfig(normalizers={"a": ("collapse_spaces",)})
        values = {"a": "  muitos    espaços   aqui  "}
        result = clean_row(values, config)
        self.assertEqual("muitos espaços aqui", result["a"])

    def test_chained_normalizers(self):
        """Aplica múltiplos normalizadores em sequência."""
        config = MappingConfig(
            normalizers={"a": ("strip_punctuation", "upper", "collapse_spaces")}
        )
        values = {"a": "  limpa,   ISSO!  "}
        # 1. "limpa, ISSO!" -> strip_punctuaction -> "limpa ISSO"
        # 2. "limpa ISSO" -> upper -> "LIMPA ISSO"
        # 3. "LIMPA ISSO" -> collapse_spaces -> "LIMPA ISSO"
        result = clean_row(values, config)
        self.assertEqual("LIMPA ISSO", result["a"])

    def test_normalization_results_in_none(self):
        """Garante que se a normalização esvaziar a string, ela vire None."""
        config = MappingConfig(normalizers={"a": ("strip_punctuation",)})
        values = {"a": "  .,.  "}
        result = clean_row(values, config)
        self.assertIsNone(result["a"])


if __name__ == "__main__":
    unittest.main()
