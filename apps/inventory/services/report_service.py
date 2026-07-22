"""Generadores CSV oficiales de Inventory, separados por finalidad."""

import csv
import io
from dataclasses import dataclass
from decimal import Decimal

from django.db.models import Count, Sum

from apps.inventory.models import Asset, DepreciationRecord, DisposalRequest
from apps.inventory.models.catalog_models import AcquisitionType, AssetNature
from apps.inventory.models.financial_models import AccountingExportBatch
from apps.inventory.models.movement_models import DisposalStatus


@dataclass(frozen=True, slots=True)
class GeneratedReport:
    content: bytes
    filename_suffix: str
    record_count: int
    total_amount: Decimal
    metadata: dict


ASSET_HEADERS = [
    "folio_oficial", "folio_anterior", "descripcion_del_bien", "numero_de_serie",
    "categoria", "naturaleza", "cuenta_contable", "fecha_de_adquisicion",
    "costo_de_adquisicion", "valor_residual", "estado_patrimonial",
    "condicion_fisica", "sede", "dependencia", "area", "resguardatario",
]


def _csv(headers, rows):
    output = io.StringIO(newline="")
    writer = csv.writer(output); writer.writerow(headers); writer.writerows(rows)
    return output.getvalue().encode("utf-8-sig")


def _asset_queryset(*, nature=None, period_start=None, period_end=None, additions=False):
    queryset = Asset.objects.filter(is_deleted=False).select_related(
        "category", "accounting_account", "current_sede", "current_dependencia",
        "current_area", "current_custodian",
    )
    if nature: queryset = queryset.filter(category__nature=nature)
    if additions:
        queryset = queryset.filter(registration_date__gte=period_start, registration_date__lte=period_end)
    else:
        queryset = queryset.exclude(patrimonial_status__in=["DISPOSED", "ARCHIVED"])
    return queryset.order_by("official_inventory_number")


def _asset_rows(queryset):
    for asset in queryset:
        yield [
            asset.official_inventory_number, asset.legacy_inventory_number,
            asset.name, asset.serial_number, str(asset.category),
            asset.get_category_nature_display() if hasattr(asset, "get_category_nature_display") else asset.category.get_nature_display(),
            str(asset.accounting_account or ""), asset.acquisition_date.isoformat(),
            asset.acquisition_cost, asset.residual_value,
            asset.get_patrimonial_status_display(), asset.get_physical_condition_display(),
            str(asset.current_sede or ""), str(asset.current_dependencia or ""),
            str(asset.current_area or ""), str(asset.current_custodian or ""),
        ]


def _assets_report(export_type, period_start, period_end):
    nature = AssetNature.MOVABLE if export_type in {
        AccountingExportBatch.ExportType.REPORT_A,
        AccountingExportBatch.ExportType.REPORT_B,
        AccountingExportBatch.ExportType.TRANSPARENCY_MOVABLE,
    } else (None if export_type == AccountingExportBatch.ExportType.TRANSPARENCY_ADDITIONS else AssetNature.IMMOVABLE)
    additions = export_type in {
        AccountingExportBatch.ExportType.REPORT_B,
        AccountingExportBatch.ExportType.REPORT_E,
        AccountingExportBatch.ExportType.TRANSPARENCY_ADDITIONS,
    }
    queryset = _asset_queryset(nature=nature, period_start=period_start, period_end=period_end, additions=additions)
    rows = list(_asset_rows(queryset)); total = sum((asset.acquisition_cost for asset in queryset), Decimal("0"))
    return GeneratedReport(_csv(ASSET_HEADERS, rows), export_type.lower(), len(rows), total, {"nature": nature, "additions_only": additions})


def _disposals_report(export_type, period_start, period_end):
    nature = AssetNature.MOVABLE if export_type == AccountingExportBatch.ExportType.REPORT_C else (AssetNature.IMMOVABLE if export_type == AccountingExportBatch.ExportType.REPORT_F else None)
    queryset = DisposalRequest.objects.filter(
        is_deleted=False, status=DisposalStatus.EXECUTED,
        executed_at__date__gte=period_start, executed_at__date__lte=period_end,
    ).select_related("asset", "asset__category", "asset__accounting_account", "executed_by").order_by("executed_at")
    if nature:
        queryset = queryset.filter(asset__category__nature=nature)
    headers = ["folio_de_baja", "folio_del_bien", "descripcion", "naturaleza", "motivo", "fecha_de_baja", "costo_historico", "cuenta_contable", "fundamento", "ejecutado_por"]
    rows = [[item.folio, item.asset.display_inventory_number, item.asset.name, item.asset.category.get_nature_display(), item.get_reason_display(), item.executed_at.date().isoformat(), item.asset.acquisition_cost, str(item.asset.accounting_account or ""), item.legal_reference, str(item.executed_by or "")] for item in queryset]
    total = sum((item.asset.acquisition_cost for item in queryset), Decimal("0"))
    return GeneratedReport(_csv(headers, rows), export_type.lower(), len(rows), total, {"nature": nature, "executed_only": True})


def _donations_report(export_type, period_start, period_end):
    queryset = _asset_queryset(period_start=period_start, period_end=period_end, additions=True).filter(acquisition_type=AcquisitionType.DONATION)
    rows = list(_asset_rows(queryset)); total = sum((asset.acquisition_cost for asset in queryset), Decimal("0"))
    return GeneratedReport(_csv(ASSET_HEADERS, rows), "donaciones", len(rows), total, {"acquisition_type": AcquisitionType.DONATION})


def _depreciation_report(export_type, period_start, period_end):
    queryset = DepreciationRecord.objects.filter(is_deleted=False, period_end__gte=period_start, period_start__lte=period_end).select_related("run", "asset", "policy").order_by("period_year", "period_month", "asset_folio_snapshot")
    headers = ["periodo", "folio_del_bien", "bien", "cuenta_contable", "politica", "valor_original", "valor_residual", "depreciacion_del_periodo", "depreciacion_acumulada", "valor_en_libros", "estado_del_lote"]
    rows = [[item.period_label, item.asset_folio_snapshot, item.asset_name_snapshot, item.accounting_account_code_snapshot, f"{item.policy_code_snapshot} V{item.policy_version_snapshot}", item.original_value, item.residual_value, item.depreciation_amount, item.accumulated_depreciation, item.book_value, item.run.get_status_display()] for item in queryset]
    total = sum((item.depreciation_amount for item in queryset), Decimal("0"))
    return GeneratedReport(_csv(headers, rows), "depreciacion", len(rows), total, {"source": "depreciation_records"})


def _accounting_entries_report(period_start, period_end):
    queryset = DepreciationRecord.objects.filter(
        is_deleted=False, period_end__gte=period_start, period_start__lte=period_end,
        run__status="POSTED",
    ).select_related("run", "asset", "policy").order_by("period_year", "period_month", "accounting_account_code_snapshot")
    headers = ["referencia", "fecha", "concepto", "cuenta_contable", "folio_del_bien", "debe", "haber"]
    rows = []
    for item in queryset:
        reference = item.run.calculation_metadata.get("posting_reference", item.run.folio)
        concept = f"Depreciación {item.period_label} · {item.asset_name_snapshot}"
        rows.append([reference, item.period_end.isoformat(), concept, item.accounting_account_code_snapshot, item.asset_folio_snapshot, item.depreciation_amount, Decimal("0")])
        rows.append([reference, item.period_end.isoformat(), concept, f"DEP-ACUM-{item.accounting_account_code_snapshot}", item.asset_folio_snapshot, Decimal("0"), item.depreciation_amount])
    total = sum((item.depreciation_amount for item in queryset), Decimal("0"))
    return GeneratedReport(_csv(headers, rows), "polizas_depreciacion", len(rows), total, {"source": "posted_depreciation_records", "balanced_entries": True})


def _balances_report(export_type, period_start, period_end):
    disposed_ids = DisposalRequest.objects.filter(
        is_deleted=False, status=DisposalStatus.EXECUTED,
        executed_at__date__lte=period_end,
    ).values_list("asset_id", flat=True)
    queryset = Asset.objects.filter(is_deleted=False, registration_date__lte=period_end, accounting_account__isnull=False).exclude(pk__in=disposed_ids).values("accounting_account__code", "accounting_account__name").annotate(asset_count=Count("id"), total=Sum("acquisition_cost")).order_by("accounting_account__code")
    headers = ["cuenta_contable", "nombre_de_cuenta", "numero_de_bienes", "saldo_segun_inventory", "fecha_de_corte"]
    rows = [[item["accounting_account__code"], item["accounting_account__name"], item["asset_count"], item["total"], period_end.isoformat()] for item in queryset]
    total = sum((item["total"] or Decimal("0") for item in queryset), Decimal("0"))
    return GeneratedReport(_csv(headers, rows), "saldos_por_cuenta", len(rows), total, {"grouped_by": "accounting_account"})


def build_accounting_report(*, export_type, period_start, period_end):
    asset_types = {
        AccountingExportBatch.ExportType.REPORT_A, AccountingExportBatch.ExportType.REPORT_B,
        AccountingExportBatch.ExportType.REPORT_D, AccountingExportBatch.ExportType.REPORT_E,
        AccountingExportBatch.ExportType.TRANSPARENCY_MOVABLE,
        AccountingExportBatch.ExportType.TRANSPARENCY_IMMOVABLE,
        AccountingExportBatch.ExportType.TRANSPARENCY_ADDITIONS,
    }
    if export_type in asset_types: return _assets_report(export_type, period_start, period_end)
    if export_type in {AccountingExportBatch.ExportType.REPORT_C, AccountingExportBatch.ExportType.REPORT_F, AccountingExportBatch.ExportType.TRANSPARENCY_DISPOSALS}: return _disposals_report(export_type, period_start, period_end)
    if export_type in {AccountingExportBatch.ExportType.REPORT_G, AccountingExportBatch.ExportType.TRANSPARENCY_DONATIONS}: return _donations_report(export_type, period_start, period_end)
    if export_type == AccountingExportBatch.ExportType.DEPRECIATION: return _depreciation_report(export_type, period_start, period_end)
    if export_type == AccountingExportBatch.ExportType.ACCOUNTING_ENTRIES: return _accounting_entries_report(period_start, period_end)
    if export_type == AccountingExportBatch.ExportType.ACCOUNT_BALANCES: return _balances_report(export_type, period_start, period_end)
    # CUSTOM conserva el padrón completo, con columnas documentadas.
    queryset = _asset_queryset(period_start=period_start, period_end=period_end)
    rows = list(_asset_rows(queryset)); total = sum((asset.acquisition_cost for asset in queryset), Decimal("0"))
    return GeneratedReport(_csv(ASSET_HEADERS, rows), "padron_personalizado", len(rows), total, {"source": "asset_registry"})


__all__ = ["GeneratedReport", "build_accounting_report"]
