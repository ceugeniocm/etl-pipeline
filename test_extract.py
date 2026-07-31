"""Testes da leitura em streaming das planilhas de origem.

Cobre a tarefa 20 de ``docs/tasks.md`` (FR-001, FR-002, NFR-001, NFR-005) e as
bordas do leitor legado ``.xls`` da tarefa 21.

As planilhas usadas nos testes são geradas em tempo de execução, em diretório
temporário; nenhum arquivo binário é versionado.
"""

import datetime
import os
import sys
import tempfile
import types
import unittest

from etl import extract
from etl.config import SourceConfig
from etl.errors import ExtractionError

try:
    import openpyxl
except ImportError:  # pragma: no cover - dependência declarada em requirements.txt
    openpyxl = None

requires_openpyxl = unittest.skipUnless(
    openpyxl is not None,
    "openpyxl não instalado; execute python3 -m pip install -r requirements.txt",
)

try:
    import xlrd
except ImportError:  # pragma: no cover - dependência declarada em requirements.txt
    xlrd = None

requires_xlrd = unittest.skipUnless(
    xlrd is not None,
    "xlrd não instalado; execute python3 -m pip install -r requirements.txt",
)


def write_workbook(path, sheets):
    """Grava uma planilha ``.xlsx`` a partir de ``{aba: [linhas]}``."""
    workbook = openpyxl.Workbook()
    workbook.remove(workbook.active)
    for name, rows in sheets.items():
        worksheet = workbook.create_sheet(title=name)
        for row in rows:
            worksheet.append(list(row))
    workbook.save(path)
    return path


class ExtractTestCase(unittest.TestCase):
    """Base que fornece um diretório temporário por teste."""

    def setUp(self):
        self._directory = tempfile.TemporaryDirectory()
        self.addCleanup(self._directory.cleanup)
        self.directory = self._directory.name

    def path(self, name="planilha.xlsx"):
        """Caminho de um arquivo dentro do diretório temporário."""
        return os.path.join(self.directory, name)

    def workbook(self, sheets, name="planilha.xlsx"):
        """Grava e devolve o caminho de uma planilha de teste."""
        return write_workbook(self.path(name), sheets)

    def simple_workbook(self, extra_rows=(), name="planilha.xlsx"):
        """Planilha de duas colunas com duas linhas válidas."""
        rows = [
            ("Código", "Cliente"),
            (1, "Ana"),
            (2, "Bruno"),
            *extra_rows,
        ]
        return self.workbook({"Vendas": rows}, name=name)

    def read_all(self, path, **kwargs):
        """Abre ``path`` e devolve todas as linhas em uma lista."""
        with extract.open_sheet(path, **kwargs) as sheet:
            return list(sheet.rows())

    def assert_error_mentions(self, text, callable_object, *args, **kwargs):
        """Verifica que a extração falha citando ``text``."""
        with self.assertRaises(ExtractionError) as context:
            result = callable_object(*args, **kwargs)
            # Erros detectados durante a iteração só surgem ao consumir.
            if hasattr(result, "__iter__") and not isinstance(result, (str, bytes)):
                list(result)
        self.assertIn(text, str(context.exception))
        return context.exception


@requires_openpyxl
class TestHappyPath(ExtractTestCase):
    """Leitura de uma planilha bem formada (FR-001)."""

    def test_columns_come_from_the_header_row(self):
        with extract.open_sheet(self.simple_workbook()) as sheet:
            self.assertEqual(("Código", "Cliente"), sheet.columns)

    def test_rows_carry_values_sheet_and_source_row_number(self):
        rows = self.read_all(self.simple_workbook())
        self.assertEqual(2, len(rows))
        self.assertEqual({"Código": 1, "Cliente": "Ana"}, rows[0].values)
        self.assertEqual("Vendas", rows[0].sheet)
        self.assertEqual(2, rows[0].number)
        self.assertEqual(3, rows[1].number)

    def test_row_supports_indexing_and_get(self):
        row = self.read_all(self.simple_workbook())[0]
        self.assertEqual("Ana", row["Cliente"])
        self.assertEqual("Ana", row.get("Cliente"))
        self.assertIsNone(row.get("Inexistente"))
        with self.assertRaises(KeyError):
            row["Inexistente"]

    def test_row_is_immutable(self):
        row = self.read_all(self.simple_workbook())[0]
        with self.assertRaises(Exception):
            row.number = 99

    def test_native_types_are_preserved(self):
        path = self.workbook(
            {
                "Dados": [
                    ("Texto", "Inteiro", "Decimal", "Data", "Booleano", "Vazio"),
                    ("x", 7, 1.5, datetime.datetime(2026, 7, 30), True, None),
                ]
            }
        )
        values = self.read_all(path)[0].values
        self.assertEqual("x", values["Texto"])
        self.assertEqual(7, values["Inteiro"])
        self.assertEqual(1.5, values["Decimal"])
        self.assertEqual(datetime.datetime(2026, 7, 30), values["Data"])
        self.assertIs(True, values["Booleano"])
        self.assertIsNone(values["Vazio"])

    def test_accented_column_names_are_preserved(self):
        path = self.workbook({"Aba": [("Descrição do Produto",), ("mesa",)]})
        with extract.open_sheet(path) as sheet:
            self.assertEqual(("Descrição do Produto",), sheet.columns)
            rows = list(sheet.rows())
        self.assertEqual("mesa", rows[0]["Descrição do Produto"])

    def test_reading_from_a_source_config(self):
        source = SourceConfig(path=self.simple_workbook(), sheet="Vendas")
        with extract.open_source(source) as sheet:
            self.assertEqual(2, len(list(sheet.rows())))

    def test_header_row_can_be_below_the_first_line(self):
        path = self.workbook(
            {
                "Aba": [
                    ("Relatório de vendas",),
                    (),
                    ("Código", "Cliente"),
                    (1, "Ana"),
                ]
            }
        )
        with extract.open_sheet(path, header_row=3) as sheet:
            self.assertEqual(("Código", "Cliente"), sheet.columns)
            rows = list(sheet.rows())
        self.assertEqual(1, len(rows))
        self.assertEqual(4, rows[0].number)


@requires_openpyxl
class TestSheetSelection(ExtractTestCase):
    """Seleção da aba configurada ou da primeira (FR-001, tarefa 16)."""

    def setUp(self):
        super().setUp()
        self.path_ = self.workbook(
            {
                "Primeira": [("A",), (1,)],
                "Segunda": [("B",), (2,)],
            }
        )

    def test_first_sheet_is_used_by_default(self):
        with extract.open_sheet(self.path_) as sheet:
            self.assertEqual("Primeira", sheet.sheet)
            self.assertEqual(("A",), sheet.columns)

    def test_configured_sheet_is_used(self):
        with extract.open_sheet(self.path_, sheet="Segunda") as sheet:
            self.assertEqual("Segunda", sheet.sheet)
            self.assertEqual(("B",), sheet.columns)

    def test_rows_report_the_selected_sheet(self):
        rows = self.read_all(self.path_, sheet="Segunda")
        self.assertEqual("Segunda", rows[0].sheet)

    def test_missing_sheet_is_rejected(self):
        error = self.assert_error_mentions(
            "Terceira", extract.open_sheet, self.path_, sheet="Terceira"
        )
        self.assertIn(self.path_, str(error))

    def test_sheet_name_is_case_sensitive(self):
        self.assert_error_mentions(
            "primeira", extract.open_sheet, self.path_, sheet="primeira"
        )


@requires_openpyxl
class TestHeaderDerivation(ExtractTestCase):
    """Derivação dos nomes de coluna (FR-001, tarefa 17)."""

    def test_surrounding_whitespace_is_stripped(self):
        path = self.workbook({"Aba": [("  Código  ", "\tCliente\n"), (1, "Ana")]})
        with extract.open_sheet(path) as sheet:
            self.assertEqual(("Código", "Cliente"), sheet.columns)

    def test_non_text_headers_become_text(self):
        path = self.workbook({"Aba": [(2026, 1.5), ("a", "b")]})
        with extract.open_sheet(path) as sheet:
            self.assertEqual(("2026", "1.5"), sheet.columns)

    def test_trailing_empty_headers_are_dropped(self):
        path = self.workbook({"Aba": [("Código", None, None), (1, None, None)]})
        with extract.open_sheet(path) as sheet:
            self.assertEqual(("Código",), sheet.columns)

    def test_blank_header_between_columns_gets_a_reserved_name(self):
        path = self.workbook({"Aba": [("Código", None, "Cliente"), (1, "x", "Ana")]})
        with extract.open_sheet(path) as sheet:
            self.assertEqual(3, len(sheet.columns))
            self.assertEqual("Código", sheet.columns[0])
            self.assertEqual("Cliente", sheet.columns[2])
            rows = list(sheet.rows())
        self.assertEqual("Ana", rows[0]["Cliente"])

    def test_duplicate_header_is_rejected(self):
        path = self.workbook({"Aba": [("Código", "Código"), (1, 2)]})
        self.assert_error_mentions("Código", extract.open_sheet, path)

    def test_duplicate_header_after_stripping_is_rejected(self):
        path = self.workbook({"Aba": [("Código", " Código "), (1, 2)]})
        self.assert_error_mentions("ambígu", extract.open_sheet, path)

    def test_blank_header_row_is_rejected(self):
        path = self.workbook({"Aba": [(None, None), (1, 2)]})
        self.assert_error_mentions("cabeçalho", extract.open_sheet, path)

    def test_header_row_beyond_the_last_line_is_rejected(self):
        path = self.workbook({"Aba": [("Código",), (1,)]})
        self.assert_error_mentions(
            "cabeçalho", extract.open_sheet, path, header_row=5
        )


@requires_openpyxl
class TestRowHandling(ExtractTestCase):
    """Tratamento das linhas de dados (FR-001, NFR-009)."""

    def test_blank_rows_are_skipped_without_shifting_numbers(self):
        path = self.workbook(
            {
                "Aba": [
                    ("Código", "Cliente"),
                    (1, "Ana"),
                    (None, None),
                    (2, "Bruno"),
                ]
            }
        )
        rows = self.read_all(path)
        self.assertEqual([2, 4], [row.number for row in rows])

    def test_short_rows_are_padded_with_none(self):
        path = self.workbook(
            {"Aba": [("Código", "Cliente", "Total"), (1, "Ana"), (2, "Bruno", 10)]}
        )
        rows = self.read_all(path)
        self.assertEqual({"Código", "Cliente", "Total"}, set(rows[0].values))
        self.assertIsNone(rows[0]["Total"])
        self.assertEqual(10, rows[1]["Total"])

    def test_values_beyond_the_header_are_dropped(self):
        path = self.workbook({"Aba": [("Código",), (1, "excedente")]})
        rows = self.read_all(path)
        self.assertEqual({"Código": 1}, rows[0].values)

    def test_rows_are_produced_lazily(self):
        with extract.open_sheet(self.simple_workbook()) as sheet:
            rows = sheet.rows()
            self.assertIsInstance(rows, types.GeneratorType)
            self.assertEqual(2, next(rows).number)

    def test_rows_can_be_read_only_once(self):
        with extract.open_sheet(self.simple_workbook()) as sheet:
            list(sheet.rows())
            with self.assertRaises(RuntimeError):
                list(sheet.rows())

    def test_close_is_idempotent(self):
        sheet = extract.open_sheet(self.simple_workbook())
        sheet.close()
        sheet.close()


@requires_openpyxl
class TestSourceErrors(ExtractTestCase):
    """Erros de origem, todos como ExtractionError (FR-001, tarefa 19)."""

    def test_missing_file(self):
        path = self.path("inexistente.xlsx")
        error = self.assert_error_mentions(path, extract.open_sheet, path)
        self.assertEqual(3, error.exit_code)

    def test_unsupported_extension(self):
        path = self.path("dados.csv")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("a,b\n")
        self.assert_error_mentions(".csv", extract.open_sheet, path)

    def test_file_without_extension(self):
        path = self.path("dados")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("x")
        self.assert_error_mentions("não suportado", extract.open_sheet, path)

    def test_extension_is_case_insensitive(self):
        path = self.simple_workbook(name="PLANILHA.XLSX")
        self.assertEqual(2, len(self.read_all(path)))

    def test_corrupt_workbook(self):
        path = self.path("corrompida.xlsx")
        with open(path, "wb") as handle:
            handle.write(b"isto nao e uma planilha")
        self.assert_error_mentions("corrompido", extract.open_sheet, path)

    def test_directory_instead_of_file(self):
        path = self.path("pasta.xlsx")
        os.mkdir(path)
        self.assert_error_mentions(path, extract.open_sheet, path)

    def test_sheet_without_data_rows(self):
        path = self.workbook({"Aba": [("Código", "Cliente")]})
        self.assert_error_mentions("vazia", self.read_all, path)

    def test_sheet_with_only_blank_rows(self):
        path = self.workbook({"Aba": [("Código",), (None,), (None,)]})
        self.assert_error_mentions("vazia", self.read_all, path)

    def test_completely_empty_sheet(self):
        path = self.workbook({"Aba": []})
        self.assert_error_mentions("vazia", extract.open_sheet, path)

    def test_failed_open_does_not_leak_the_file(self):
        # Um erro na seleção da aba deve fechar a pasta de trabalho; no
        # Windows um arquivo ainda aberto não poderia ser removido.
        path = self.simple_workbook()
        with self.assertRaises(ExtractionError):
            extract.open_sheet(path, sheet="Inexistente")
        os.remove(path)


class TestIterChunks(unittest.TestCase):
    """Agrupamento das linhas em blocos (FR-002, tarefa 18)."""

    def rows(self, count):
        """Sequência de linhas sintéticas, sem depender de arquivo."""
        return [
            extract.SourceRow(sheet="Aba", number=index + 2, values={"n": index})
            for index in range(count)
        ]

    def sizes(self, count, chunk_size):
        """Tamanhos dos blocos produzidos para ``count`` linhas."""
        return [len(chunk) for chunk in extract.iter_chunks(self.rows(count), chunk_size)]

    def test_exact_multiple_of_the_chunk_size(self):
        self.assertEqual([3, 3], self.sizes(6, 3))

    def test_last_chunk_may_be_smaller(self):
        self.assertEqual([3, 3, 1], self.sizes(7, 3))

    def test_fewer_rows_than_the_chunk_size(self):
        self.assertEqual([2], self.sizes(2, 100))

    def test_chunk_size_of_one(self):
        self.assertEqual([1, 1, 1], self.sizes(3, 1))

    def test_no_rows_produces_no_chunks(self):
        self.assertEqual([], self.sizes(0, 10))

    def test_rows_keep_their_order_and_identity(self):
        rows = self.rows(5)
        chunks = list(extract.iter_chunks(rows, 2))
        self.assertEqual(rows, [row for chunk in chunks for row in chunk])
        self.assertIs(rows[0], chunks[0][0])

    def test_default_chunk_size_is_the_configured_one(self):
        from etl.config import DEFAULT_CHUNK_SIZE

        rows = self.rows(4)
        self.assertLess(len(rows), DEFAULT_CHUNK_SIZE)
        self.assertEqual([4], [len(chunk) for chunk in extract.iter_chunks(rows)])

    def test_invalid_chunk_size(self):
        with self.assertRaises(ValueError):
            list(extract.iter_chunks(self.rows(1), 0))

    def test_chunks_are_produced_lazily(self):
        consumed = []

        def source():
            for row in self.rows(10):
                consumed.append(row.number)
                yield row

        chunks = extract.iter_chunks(source(), 2)
        next(chunks)
        # Apenas o primeiro bloco foi materializado.
        self.assertEqual(2, len(consumed))


@requires_openpyxl
class TestStreaming(ExtractTestCase):
    """A leitura não carrega o arquivo inteiro em memória (NFR-001)."""

    def test_only_the_current_chunk_is_materialized(self):
        rows = [("Código", "Cliente")]
        rows += [(index, f"Cliente {index}") for index in range(1, 501)]
        path = self.workbook({"Aba": rows})

        with extract.open_sheet(path) as sheet:
            chunks = extract.iter_chunks(sheet.rows(), 100)
            first = next(chunks)
            self.assertEqual(100, len(first))
            self.assertEqual(2, first[0].number)
            remaining = sum(len(chunk) for chunk in chunks)
        self.assertEqual(400, remaining)


class TestLegacyXls(ExtractTestCase):
    """Bordas do leitor legado ``.xls`` (tarefa 21).

    A geração de um arquivo ``.xls`` exigiria um escritor BIFF (``xlwt``), que
    não é dependência do projeto; por isso são exercitados o roteamento por
    extensão, a falha de leitura e a conversão de células.
    """

    def test_missing_xls_file_is_reported_as_not_found(self):
        path = self.path("legado.xls")
        self.assert_error_mentions(path, extract.open_sheet, path)

    @requires_xlrd
    def test_invalid_xls_file_is_reported_as_unreadable(self):
        path = self.path("legado.xls")
        with open(path, "wb") as handle:
            handle.write(b"isto nao e uma planilha")
        self.assert_error_mentions("corrompido", extract.open_sheet, path)

    def test_absent_dependency_is_reported_explicitly(self):
        path = self.path("legado.xls")
        with open(path, "wb") as handle:
            handle.write(b"x")
        original = sys.modules.get("xlrd")
        sys.modules["xlrd"] = None  # torna 'import xlrd' um ImportError
        try:
            error = self.assert_error_mentions("xlrd", extract.open_sheet, path)
        finally:
            if original is None:
                del sys.modules["xlrd"]
            else:
                sys.modules["xlrd"] = original
        self.assertIn(".xls", str(error))


class TestXlsCellConversion(unittest.TestCase):
    """Conversão das células do ``xlrd`` para tipos Python (tarefa 21)."""

    class FakeXlrd:
        """Constantes e utilidades do ``xlrd`` usadas pela conversão."""

        XL_CELL_EMPTY = 0
        XL_CELL_TEXT = 1
        XL_CELL_NUMBER = 2
        XL_CELL_DATE = 3
        XL_CELL_BOOLEAN = 4
        XL_CELL_ERROR = 5
        XL_CELL_BLANK = 6

        class xldate:
            @staticmethod
            def xldate_as_datetime(value, datemode):
                return datetime.datetime(2026, 7, 30) + datetime.timedelta(
                    days=value, hours=datemode
                )

    def convert(self, ctype, value):
        """Converte uma célula sintética com o ``xlrd`` falso."""
        cell = types.SimpleNamespace(ctype=ctype, value=value)
        return extract._xls_cell_value(cell, self.FakeXlrd, 0)

    def test_empty_and_blank_cells_become_none(self):
        self.assertIsNone(self.convert(self.FakeXlrd.XL_CELL_EMPTY, ""))
        self.assertIsNone(self.convert(self.FakeXlrd.XL_CELL_BLANK, ""))

    def test_error_cell_becomes_none(self):
        self.assertIsNone(self.convert(self.FakeXlrd.XL_CELL_ERROR, 42))

    def test_date_serial_becomes_datetime(self):
        self.assertEqual(
            datetime.datetime(2026, 7, 31),
            self.convert(self.FakeXlrd.XL_CELL_DATE, 1),
        )

    def test_boolean_cell_becomes_bool(self):
        self.assertIs(True, self.convert(self.FakeXlrd.XL_CELL_BOOLEAN, 1))
        self.assertIs(False, self.convert(self.FakeXlrd.XL_CELL_BOOLEAN, 0))

    def test_text_and_number_pass_through(self):
        self.assertEqual("Ana", self.convert(self.FakeXlrd.XL_CELL_TEXT, "Ana"))
        self.assertEqual(1.5, self.convert(self.FakeXlrd.XL_CELL_NUMBER, 1.5))


if __name__ == "__main__":
    unittest.main()
