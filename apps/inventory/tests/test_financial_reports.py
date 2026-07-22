from unittest.mock import patch

from django.test import SimpleTestCase

from apps.inventory.models.financial_models import AccountingExportBatch
from apps.inventory.services.report_service import GeneratedReport, build_accounting_report


class FinancialReportRoutingTests(SimpleTestCase):
    def setUp(self):
        self.result = GeneratedReport(b"csv", "prueba", 1, 0, {})

    def test_incisos_de_padron_usan_generador_de_bienes(self):
        report_types = [
            AccountingExportBatch.ExportType.REPORT_A,
            AccountingExportBatch.ExportType.REPORT_B,
            AccountingExportBatch.ExportType.REPORT_D,
            AccountingExportBatch.ExportType.REPORT_E,
        ]
        with patch("apps.inventory.services.report_service._assets_report", return_value=self.result) as generator:
            for report_type in report_types:
                self.assertIs(build_accounting_report(export_type=report_type, period_start=None, period_end=None), self.result)
            self.assertEqual(generator.call_count, len(report_types))

    def test_bajas_usan_generador_de_bajas(self):
        with patch("apps.inventory.services.report_service._disposals_report", return_value=self.result) as generator:
            for report_type in (AccountingExportBatch.ExportType.REPORT_C, AccountingExportBatch.ExportType.REPORT_F):
                build_accounting_report(export_type=report_type, period_start=None, period_end=None)
            self.assertEqual(generator.call_count, 2)

    def test_polizas_no_reutilizan_el_reporte_de_depreciacion(self):
        with patch("apps.inventory.services.report_service._accounting_entries_report", return_value=self.result) as entries, patch("apps.inventory.services.report_service._depreciation_report", return_value=self.result) as depreciation:
            build_accounting_report(export_type=AccountingExportBatch.ExportType.ACCOUNTING_ENTRIES, period_start=None, period_end=None)
            entries.assert_called_once(); depreciation.assert_not_called()
