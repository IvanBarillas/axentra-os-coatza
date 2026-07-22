"""Procesos transaccionales de depreciación, exportación y conciliación."""

import csv
import io
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from hashlib import sha256
from uuid import uuid4

from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Sum
from django.db.models import Q
from django.utils import timezone

from apps.inventory.integrations import core_directory
from apps.inventory.models import (
    AccountingExportBatch, AccountingReconciliation,
    AccountingReconciliationItem, Asset, AssetPatrimonialStatus,
    DepreciationPolicy, DepreciationRecord, DepreciationRun,
    InventoryAuditAction,
)
from apps.inventory.models.financial_models import (
    AccountingExportStatus, DepreciationRunStatus,
    ReconciliationItemResult, ReconciliationStatus,
)
from apps.inventory.services.audit_service import build_audit_request_context, log_inventory_event, model_snapshot
from apps.inventory.services.exceptions import InventoryAuthorizationError, InventoryStateError, InventoryValidationError
from apps.inventory.services.report_service import build_accounting_report


MONEY = Decimal("0.01")


def _actor(actor_id, permission):
    try:
        actor = core_directory.get_user_identity(actor_id)
        role = core_directory.get_module_role(actor.id)
    except core_directory.CoreDirectoryError as exc:
        raise InventoryAuthorizationError(str(exc)) from exc
    if not actor.has_global_bypass and not (role and role.has_permission(permission)):
        raise InventoryAuthorizationError("No cuenta con permiso para ejecutar este proceso financiero.")
    return actor


def _folio(prefix):
    return f"{prefix}-{timezone.localtime():%Y%m%d-%H%M%S}-{str(uuid4())[:8]}".upper()


def _audit(action, summary, actor, target, request, new_value=None):
    log_inventory_event(
        action=action, summary=summary, actor_id=actor.id, target=target,
        new_value=new_value or model_snapshot(target),
        request_context=build_audit_request_context(request),
    )


@transaction.atomic
def create_depreciation_run(*, data, actor_id, request=None):
    actor = _actor(actor_id, "can_run_depreciation")
    duplicate = DepreciationRun.objects.filter(
        frequency=data.frequency, period_year=data.period_year,
        period_month=data.period_month, is_deleted=False,
    ).exclude(status=DepreciationRunStatus.CANCELLED).exists()
    if duplicate:
        raise InventoryValidationError("Ya existe una ejecución de depreciación para ese periodo.")
    run = DepreciationRun(
        folio=_folio("DEP"), frequency=data.frequency,
        period_year=data.period_year, period_month=data.period_month,
        period_start=data.period_start, period_end=data.period_end,
        cutoff_at=data.cutoff_at, initiated_by_id=actor.id,
        initiated_by_name_snapshot=actor.display_name,
        initiated_by_email_snapshot=actor.normalized_email, notes=data.notes,
    )
    run.full_clean(); run.save()
    _audit(InventoryAuditAction.CREATE, "Ejecución de depreciación creada", actor, run, request)
    return run


@transaction.atomic
def create_depreciation_policy(*, data, actor_id, request=None):
    actor = _actor(actor_id, "can_run_depreciation")
    code = str(data.policy_code).strip().upper()
    overlaps = DepreciationPolicy.objects.filter(
        policy_code=code,
        accounting_account_id=data.accounting_account_id,
        category_id=data.category_id,
        is_deleted=False,
        effective_from__lte=data.effective_until or data.effective_from,
    ).filter(Q(effective_until__isnull=True) | Q(effective_until__gte=data.effective_from))
    if overlaps.exists():
        raise InventoryValidationError("La vigencia se traslapa con otra versión de esta política.")
    last_version = DepreciationPolicy.objects.filter(policy_code=code, is_deleted=False).order_by("-version_number").values_list("version_number", flat=True).first() or 0
    policy = DepreciationPolicy(
        policy_code=code, version_number=last_version + 1, name=data.name,
        accounting_account_id=data.accounting_account_id,
        category_id=data.category_id, method=data.method, frequency=data.frequency,
        useful_life_months=data.useful_life_months,
        residual_percentage=data.residual_percentage,
        effective_from=data.effective_from, effective_until=data.effective_until,
        source_reference=data.source_reference,
    )
    policy.full_clean(); policy.save()
    _audit(InventoryAuditAction.CREATE, "Política de depreciación creada", actor, policy, request)
    return policy


@transaction.atomic
def close_depreciation_policy(*, policy_id, data, actor_id, request=None):
    actor = _actor(actor_id, "can_run_depreciation")
    policy = DepreciationPolicy.objects.select_for_update().get(pk=policy_id, is_deleted=False)
    if policy.effective_until and policy.effective_until <= data.effective_until:
        raise InventoryStateError("La política ya tiene una fecha de cierre igual o anterior.")
    if data.effective_until < policy.effective_from:
        raise InventoryValidationError("El cierre no puede ser anterior al inicio de vigencia.")
    policy.effective_until = data.effective_until
    policy.calculation_settings = {**policy.calculation_settings, "closing_reason": str(data.reason).strip(), "closed_by": str(actor.id)}
    policy.full_clean(); policy.save()
    _audit(InventoryAuditAction.UPDATE, "Vigencia de política de depreciación cerrada", actor, policy, request)
    return policy


def _policy_for(asset, run):
    policies = DepreciationPolicy.objects.filter(
        accounting_account_id=asset.accounting_account_id,
        effective_from__lte=run.period_end, is_active=True, is_deleted=False,
    ).filter(category_id=asset.category_id).order_by("-effective_from", "-version_number")
    fallback = DepreciationPolicy.objects.filter(
        accounting_account_id=asset.accounting_account_id, category__isnull=True,
        effective_from__lte=run.period_end, is_active=True, is_deleted=False,
    ).order_by("-effective_from", "-version_number")
    policies = list(policies) + list(fallback)
    for policy in policies:
        if policy.effective_until is None or policy.effective_until >= run.period_start:
            return policy
    return None


@transaction.atomic
def calculate_depreciation_run(*, run_id, actor_id, asset_ids=(), recalculate=False, request=None):
    actor = _actor(actor_id, "can_run_depreciation")
    run = DepreciationRun.objects.select_for_update().get(pk=run_id, is_deleted=False)
    if run.status not in {DepreciationRunStatus.DRAFT, DepreciationRunStatus.FAILED}:
        raise InventoryStateError("La ejecución ya no admite cálculo.")
    if run.records.exists() and not recalculate:
        raise InventoryStateError("La ejecución ya contiene resultados. Active el recálculo para sustituirlos.")
    run.records.all().delete()
    assets = Asset.objects.filter(
        is_deleted=False, is_capitalizable=True,
        patrimonial_status=AssetPatrimonialStatus.ACTIVE,
        accounting_account__isnull=False, acquisition_date__lte=run.period_end,
    ).select_related("accounting_account", "category")
    if asset_ids:
        assets = assets.filter(pk__in=asset_ids)
    totals = {"original": Decimal("0"), "period": Decimal("0"), "accumulated": Decimal("0"), "book": Decimal("0")}
    errors = []
    for asset in assets:
        policy = _policy_for(asset, run)
        if not policy:
            errors.append(f"{asset.display_inventory_number}: sin política vigente")
            continue
        life = asset.useful_life_months or policy.useful_life_months
        residual = asset.residual_value or (asset.acquisition_cost * policy.residual_factor).quantize(MONEY)
        base = max(asset.acquisition_cost - residual, Decimal("0"))
        previous = DepreciationRecord.objects.filter(asset=asset, is_deleted=False).exclude(run=run).order_by("-period_year", "-period_month").values_list("accumulated_depreciation", flat=True).first() or Decimal("0")
        periods = Decimal("12") if run.frequency == "ANNUAL" else Decimal("1")
        amount = min((base / Decimal(life) * periods).quantize(MONEY, rounding=ROUND_HALF_UP), max(base - previous, Decimal("0")))
        accumulated = previous + amount
        book = asset.acquisition_cost - accumulated
        record = DepreciationRecord(
            run=run, asset=asset, policy=policy,
            asset_folio_snapshot=asset.display_inventory_number,
            asset_name_snapshot=asset.name,
            accounting_account_code_snapshot=asset.accounting_account.code,
            policy_code_snapshot=policy.policy_code,
            policy_version_snapshot=policy.version_number,
            method_snapshot=policy.method,
            useful_life_months_snapshot=life,
            residual_percentage_snapshot=policy.residual_percentage,
            period_year=run.period_year, period_month=run.period_month,
            period_start=run.period_start, period_end=run.period_end,
            original_value=asset.acquisition_cost, residual_value=residual,
            depreciable_base=base, previous_accumulated_depreciation=previous,
            depreciation_amount=amount, accumulated_depreciation=accumulated,
            book_value=book, calculated_by_id=actor.id,
            calculated_by_name_snapshot=actor.display_name,
            calculated_by_email_snapshot=actor.normalized_email,
        )
        record.full_clean(); record.save()
        totals["original"] += asset.acquisition_cost; totals["period"] += amount
        totals["accumulated"] += accumulated; totals["book"] += book
    run.status = DepreciationRunStatus.COMPLETED
    run.completed_by_id = actor.id; run.completed_at = timezone.now()
    run.asset_count = run.records.count(); run.original_value_total = totals["original"]
    run.period_depreciation_total = totals["period"]
    run.accumulated_depreciation_total = totals["accumulated"]
    run.book_value_total = totals["book"]
    run.calculation_metadata = {"omitted_assets": errors, "omitted_count": len(errors)}
    run.error_message = ""; run.full_clean(); run.save()
    _audit(InventoryAuditAction.UPDATE, "Depreciación calculada", actor, run, request)
    return run


@transaction.atomic
def post_depreciation_run(*, run_id, data, actor_id, request=None):
    actor = _actor(actor_id, "can_post_depreciation")
    run = DepreciationRun.objects.select_for_update().get(pk=run_id, is_deleted=False)
    if run.status != DepreciationRunStatus.COMPLETED:
        raise InventoryStateError("Sólo una ejecución calculada puede aplicarse.")
    run.status = DepreciationRunStatus.POSTED; run.posted_by_id = actor.id; run.posted_at = timezone.now()
    run.notes = "\n".join(filter(None, [run.notes, data.notes, f"Referencia contable: {data.posting_reference}"]))
    run.calculation_metadata = {**run.calculation_metadata, "posting_reference": data.posting_reference}
    run.full_clean(); run.save()
    _audit(InventoryAuditAction.APPROVE, "Depreciación aplicada y cerrada", actor, run, request)
    return run


@transaction.atomic
def create_accounting_export(*, data, actor_id, request=None):
    actor = _actor(actor_id, "can_export_reports")
    batch = AccountingExportBatch(
        folio=_folio("EXP"), export_type=data.export_type, file_format="CSV",
        destination_system=data.destination_system, period_start=data.period_start,
        period_end=data.period_end, cutoff_at=data.cutoff_at,
        requested_by_id=actor.id, requested_by_name_snapshot=actor.display_name,
        requested_by_email_snapshot=actor.normalized_email, filters_snapshot=dict(data.filters),
        status=AccountingExportStatus.PROCESSING,
    )
    batch.full_clean(); batch.save()
    report = build_accounting_report(export_type=data.export_type, period_start=data.period_start, period_end=data.period_end)
    content = report.content; filename = f"{batch.folio}-{report.filename_suffix}.csv"
    batch.generated_file.save(filename, ContentFile(content), save=False)
    batch.generated_filename = filename; batch.generated_file_hash = sha256(content).hexdigest()
    batch.generated_file_size = len(content); batch.record_count = report.record_count; batch.total_amount = report.total_amount
    batch.metadata = report.metadata
    batch.status = AccountingExportStatus.COMPLETED; batch.completed_by_id = actor.id; batch.completed_at = timezone.now()
    batch.full_clean(); batch.save()
    _audit(InventoryAuditAction.EXPORT, "Reporte patrimonial exportado", actor, batch, request)
    return batch


@transaction.atomic
def create_reconciliation(*, data, actor_id, request=None):
    actor = _actor(actor_id, "can_manage_reconciliation")
    uploaded = data.source_file
    digest = sha256()
    for chunk in uploaded.chunks(): digest.update(chunk)
    uploaded.seek(0)
    reconciliation = AccountingReconciliation(
        folio=_folio("CON"), source_system=data.source_system,
        period_start=data.period_start, period_end=data.period_end, cutoff_at=data.cutoff_at,
        source_file=uploaded, source_filename=data.source_filename,
        source_file_hash=digest.hexdigest(), source_file_size=getattr(uploaded, "size", None),
        created_by_id=actor.id, created_by_name_snapshot=actor.display_name,
        created_by_email_snapshot=actor.normalized_email,
        status=ReconciliationStatus.FILE_UPLOADED,
    )
    reconciliation.full_clean(); reconciliation.save()
    _audit(InventoryAuditAction.CREATE, "Conciliación contable creada", actor, reconciliation, request)
    return reconciliation


@transaction.atomic
def process_reconciliation(*, reconciliation_id, data, actor_id, request=None):
    actor = _actor(actor_id, "can_manage_reconciliation")
    reconciliation = AccountingReconciliation.objects.select_for_update().get(pk=reconciliation_id, is_deleted=False)
    if reconciliation.status not in {ReconciliationStatus.FILE_UPLOADED, ReconciliationStatus.FAILED}:
        raise InventoryStateError("La conciliación no está lista para procesarse.")
    mapping = dict(data.column_mapping or {})
    code_column = mapping.get("account_code", "cuenta")
    amount_column = mapping.get("amount", "saldo")
    reconciliation.source_file.open("rb")
    raw = reconciliation.source_file.read(); reconciliation.source_file.close()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    source = {}
    try:
        for row in csv.DictReader(io.StringIO(text)):
            code = str(row.get(code_column, "")).strip()
            if not code: continue
            normalized = str(row.get(amount_column, "0")).replace(",", "").strip()
            source[code] = source.get(code, Decimal("0")) + Decimal(normalized or "0")
    except (InvalidOperation, csv.Error) as exc:
        raise InventoryValidationError("El archivo no contiene saldos contables válidos.") from exc
    inventory_rows = Asset.objects.filter(
        is_deleted=False,
        is_capitalizable=True,
        patrimonial_status=AssetPatrimonialStatus.ACTIVE,
        accounting_account__isnull=False,
    ).values("accounting_account__code", "accounting_account__name", "accounting_account_id").annotate(amount=Sum("acquisition_cost"))
    inventory = {row["accounting_account__code"]: row for row in inventory_rows}
    reconciliation.items.all().delete()
    inventory_total = Decimal("0"); accounting_total = Decimal("0"); matched = 0; different = 0
    for code in sorted(set(inventory) | set(source)):
        inv = inventory.get(code); inv_amount = inv["amount"] if inv else Decimal("0")
        acc_amount = source.get(code, Decimal("0")); difference = inv_amount - acc_amount
        if inv is None: result = ReconciliationItemResult.ACCOUNTING_ONLY
        elif code not in source: result = ReconciliationItemResult.INVENTORY_ONLY
        elif difference == 0: result = ReconciliationItemResult.MATCHED
        else: result = ReconciliationItemResult.DIFFERENCE
        matched += int(result == ReconciliationItemResult.MATCHED); different += int(result != ReconciliationItemResult.MATCHED)
        AccountingReconciliationItem.objects.create(
            reconciliation=reconciliation, accounting_account_id=inv["accounting_account_id"] if inv else None,
            account_code_snapshot=code, account_name_snapshot=inv["accounting_account__name"] if inv else "",
            inventory_amount=inv_amount, accounting_amount=acc_amount, difference_amount=difference,
            result=result, source_payload={"saldo": str(acc_amount)},
        )
        inventory_total += inv_amount; accounting_total += acc_amount
    reconciliation.inventory_total = inventory_total; reconciliation.accounting_total = accounting_total
    reconciliation.difference_total = inventory_total - accounting_total
    reconciliation.matched_account_count = matched; reconciliation.different_account_count = different
    reconciliation.processed_by_id = actor.id; reconciliation.processed_at = timezone.now()
    reconciliation.status = ReconciliationStatus.RECONCILED if different == 0 else ReconciliationStatus.WITH_DIFFERENCES
    reconciliation.import_metadata = {"column_mapping": mapping, "source_rows": len(source)}
    reconciliation.full_clean(); reconciliation.save()
    _audit(InventoryAuditAction.UPDATE, "Conciliación físico-contable procesada", actor, reconciliation, request)
    return reconciliation


@transaction.atomic
def close_reconciliation(*, reconciliation_id, data, actor_id, request=None):
    actor = _actor(actor_id, "can_manage_reconciliation")
    reconciliation = AccountingReconciliation.objects.select_for_update().get(pk=reconciliation_id, is_deleted=False)
    if reconciliation.status not in {ReconciliationStatus.RECONCILED, ReconciliationStatus.WITH_DIFFERENCES, ReconciliationStatus.UNDER_REVIEW}:
        raise InventoryStateError("La conciliación todavía no puede cerrarse.")
    reconciliation.status = ReconciliationStatus.CLOSED
    reconciliation.reviewed_by_id = actor.id; reconciliation.reviewed_at = timezone.now()
    reconciliation.closed_by_id = actor.id; reconciliation.closed_at = timezone.now()
    reconciliation.closing_notes = data.closing_notes
    reconciliation.full_clean(); reconciliation.save()
    _audit(InventoryAuditAction.APPROVE, "Conciliación físico-contable cerrada", actor, reconciliation, request)
    return reconciliation


__all__ = ["calculate_depreciation_run", "close_depreciation_policy", "close_reconciliation", "create_accounting_export", "create_depreciation_policy", "create_depreciation_run", "create_reconciliation", "post_depreciation_run", "process_reconciliation"]
