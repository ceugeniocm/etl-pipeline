"""Testes do mapeamento de colunas (tarefa 33).

Cobre as funcionalidades de ``etl/transform/mapping.py`` (FR-003).
"""

import unittest

from etl.config import MappingConfig
from etl.errors import MappingError
from etl.extract import SourceRow
from etl.transform.mapping import apply_mapping, check_mapping


class TestMapping(unittest.TestCase):
    """Testes de mapeamento e verificação de cabeçalho."""

    def test_check_mapping_happy_path(self):
        """Aceita quando todas as colunas mapeadas existem no cabeçalho."""
        config = MappingConfig(columns={"Nome": "nome", "Idade": "idade"})
        check_mapping(("Nome", "Idade", "Sexo"), config, "Aba1")

    def test_check_mapping_missing_columns(self):
        """Rejeita quando colunas mapeadas estão ausentes no cabeçalho."""
        config = MappingConfig(columns={"Nome": "nome", "Salário": "salario"})
        with self.assertRaises(MappingError) as context:
            check_mapping(("Nome", "Idade"), config, "Aba1")
        self.assertIn("Salário", str(context.exception))
        self.assertIn("Aba1", str(context.exception))

    def test_check_mapping_multiple_missing(self):
        """Lista todas as colunas ausentes na mensagem de erro."""
        config = MappingConfig(columns={"A": "a", "B": "b", "C": "c"})
        with self.assertRaises(MappingError) as context:
            check_mapping(("A",), config, "Aba1")
        self.assertIn("B", str(context.exception))
        self.assertIn("C", str(context.exception))

    def test_apply_mapping(self):
        """Transforma nomes de origem em destino e descarta não mapeadas."""
        config = MappingConfig(columns={"Cod": "id", "Valor": "preco"})
        row = SourceRow(
            sheet="Aba1", number=5, values={"Cod": 101, "Valor": 50.5, "Extra": "info"}
        )
        result = apply_mapping(row, config)
        self.assertEqual({"id": 101, "preco": 50.5}, result)
        self.assertNotIn("Extra", result)

    def test_apply_mapping_missing_source_value(self):
        """Lida com colunas mapeadas que não vieram na linha (embora presentes no header)."""
        config = MappingConfig(columns={"A": "a", "B": "b"})
        # Simulando uma linha que por algum motivo não tem a chave "B"
        row = SourceRow(sheet="Aba1", number=1, values={"A": 1})
        result = apply_mapping(row, config)
        self.assertEqual({"a": 1}, result)


if __name__ == "__main__":
    unittest.main()
