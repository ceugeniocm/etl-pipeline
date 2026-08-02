"""Testes do módulo de relatórios e estatísticas (tarefa 54)."""

import csv
import os
import sys
import unittest
from io import StringIO
from unittest.mock import patch

from etl import messages
from etl.reporting import ExecutionStats, RejectionReporter, print_progress, print_summary
from etl.transform.validation import Rejection


class TestReporting(unittest.TestCase):
    """Testes de contadores, resumo e relatório CSV."""

    def setUp(self):
        self.stats = ExecutionStats()
        self.stats.read = 100
        self.stats.transformed = 90
        self.stats.loaded = 85
        self.stats.rejected = 5
        self.stats.duplicated = 2
        self.stats.start_time = 1000.0
        self.stats.end_time = 1065.0  # 65 segundos = 00:01:05
        self.report_path = "test_rejections.csv"

    def tearDown(self):
        if os.path.exists(self.report_path):
            os.remove(self.report_path)

    def test_stats_elapsed(self):
        """Verifica a formatação do tempo decorrido."""
        self.assertEqual(self.stats.elapsed, "00:01:05")

    def test_print_progress(self):
        """Verifica a linha de progresso no stderr."""
        with patch("sys.stderr", new=StringIO()) as fake_stderr:
            print_progress(self.stats)
            output = fake_stderr.getvalue()
            self.assertIn("100 linhas lidas", output)
            self.assertIn("90 transformadas", output)
            self.assertIn("85 carregadas", output)
            self.assertIn("5 rejeitadas", output)

    def test_print_summary_success(self):
        """Verifica o resumo final em caso de sucesso."""
        with patch("sys.stderr", new=StringIO()) as fake_stderr:
            print_summary(self.stats, success=True)
            output = fake_stderr.getvalue()
            self.assertIn(messages.SUMMARY_TITLE, output)
            self.assertIn("Linhas lidas: 100", output)
            self.assertIn("Linhas carregadas: 85", output)
            self.assertIn("Linhas duplicadas descartadas: 2", output)
            self.assertIn("Tempo total: 00:01:05", output)
            self.assertIn(messages.SUMMARY_STATUS_SUCCESS, output)

    def test_print_summary_failure(self):
        """Verifica o resumo final em caso de erro."""
        with patch("sys.stderr", new=StringIO()) as fake_stderr:
            print_summary(self.stats, success=False)
            output = fake_stderr.getvalue()
            self.assertIn(messages.SUMMARY_STATUS_FAILURE, output)

    def test_rejection_reporter(self):
        """Verifica a gravação do relatório CSV."""
        reporter = RejectionReporter(self.report_path)
        rejections = [
            Rejection("Aba1", 10, "ColA", "Erro 1"),
            Rejection("Aba1", 11, "ColB", "Erro 2"),
        ]
        
        reporter.write(rejections)
        self.assertEqual(reporter.count, 2)
        
        # Segunda chamada deve anexar
        reporter.write([Rejection("Aba2", 5, "ColC", "Erro 3")])
        self.assertEqual(reporter.count, 3)
        
        with open(self.report_path, encoding="utf-8") as f:
            reader = list(csv.reader(f))
            self.assertEqual(len(reader), 4)  # Cabeçalho + 3 linhas
            self.assertEqual(reader[0], ["aba", "linha", "coluna", "motivo"])
            self.assertEqual(reader[1], ["Aba1", "10", "ColA", "Erro 1"])
            self.assertEqual(reader[3], ["Aba2", "5", "ColC", "Erro 3"])
