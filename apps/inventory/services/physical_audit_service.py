"""Flujo transaccional de levantamientos físicos de Inventory."""

from uuid import uuid4

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.inventory.integrations.core_directory import (
    CoreDirectoryError,
    get_area_context,
    get_department,
    get_site,
    get_user_identity,
)
from apps.inventory.models import (
    Asset,
    AssetPatrimonialStatus,
    PhysicalAuditItem,
    PhysicalAuditResult,
    PhysicalAuditScope,
    PhysicalAuditSession,
    PhysicalAuditStatus,
    PhysicalCondition,
)
from apps.inventory.services.common import validate_and_save
from apps.inventory.services.exceptions import (
    InventoryConflictError,
    InventoryStateError,
    InventoryValidationError,
)


DISCREPANCY_RESULTS = {
    PhysicalAuditResult.FOUND_DIFFERENT_LOCATION,
    PhysicalAuditResult.FOUND_DIFFERENT_CUSTODIAN,
    PhysicalAuditResult.FOUND_DIFFERENT_LOCATION_AND_CUSTODIAN,
    PhysicalAuditResult.DAMAGED,
    PhysicalAuditResult.NOT_FOUND,
    PhysicalAuditResult.UNREGISTERED,
}


def _lock_session(session_id):
    try:
        return PhysicalAuditSession.objects.select_for_update().get(
            pk=session_id, is_deleted=False
        )
    except PhysicalAuditSession.DoesNotExist as exc:
        raise InventoryValidationError("La auditoría física no existe.") from exc


def _lock_item(item_id):
    try:
        return PhysicalAuditItem.objects.select_for_update(of=("self",)).select_related(
            "session", "asset"
        ).get(pk=item_id, is_deleted=False)
    except PhysicalAuditItem.DoesNotExist as exc:
        raise InventoryValidationError("La partida de auditoría no existe.") from exc


def _folio():
    return f"AF-{timezone.localdate():%Y}-{str(uuid4()).split('-')[0].upper()}"


def _asset_population(session):
    queryset = Asset.objects.filter(
        is_deleted=False,
        patrimonial_status=AssetPatrimonialStatus.ACTIVE,
    ).select_related(
        "current_sede", "current_dependencia", "current_area", "current_custodian"
    )
    if session.sede_id:
        queryset = queryset.filter(current_sede_id=session.sede_id)
    if session.dependencia_id:
        queryset = queryset.filter(current_dependencia_id=session.dependencia_id)
    if session.area_id:
        queryset = queryset.filter(current_area_id=session.area_id)
    return queryset


def _refresh_counters(session):
    items = session.items.filter(is_deleted=False)
    found = items.filter(result=PhysicalAuditResult.FOUND).count()
    discrepancies = items.filter(result__in=DISCREPANCY_RESULTS).exclude(
        result__in={PhysicalAuditResult.NOT_FOUND, PhysicalAuditResult.UNREGISTERED}
    ).count()
    session.found_assets_count = found
    session.discrepancy_assets_count = discrepancies
    session.not_found_assets_count = items.filter(
        result=PhysicalAuditResult.NOT_FOUND
    ).count()
    session.unregistered_assets_count = items.filter(
        result=PhysicalAuditResult.UNREGISTERED
    ).count()
    session.save(update_fields=[
        "found_assets_count", "discrepancy_assets_count",
        "not_found_assets_count", "unregistered_assets_count", "updated_at",
    ])


def _directory_values(data):
    try:
        site = get_site(data.observed_site_id) if data.observed_site_id else None
        department = get_department(data.observed_department_id) if data.observed_department_id else None
        area = get_area_context(data.observed_area_id) if data.observed_area_id else None
        custodian = get_user_identity(data.observed_custodian_id) if data.observed_custodian_id else None
    except CoreDirectoryError as exc:
        raise InventoryValidationError(str(exc)) from exc
    if area and department and area.department_id != department.id:
        raise InventoryValidationError("El área observada no pertenece a la dependencia.")
    if area and site and area.site_id != site.id:
        raise InventoryValidationError("El área observada no pertenece a la sede.")
    return site, department, area, custodian


@transaction.atomic
def create_physical_audit(*, data, actor_id):
    if data.scope not in {value for value, _ in PhysicalAuditScope.choices}:
        raise InventoryValidationError("El alcance seleccionado no es válido.")
    session = PhysicalAuditSession(
        folio=_folio(), name=str(data.name).strip(), fiscal_year=data.fiscal_year,
        scope=data.scope, sede_id=data.site_id, dependencia_id=data.department_id,
        area_id=data.area_id, created_by_id=actor_id, notes=str(data.notes or "").strip(),
    )
    if not session.sede_id or not session.dependencia_id:
        raise InventoryValidationError(
            "Seleccione la sede y la dependencia que serán revisadas."
        )
    if not _asset_population(session).exists():
        raise InventoryValidationError(
            "La sede y dependencia seleccionadas no tienen bienes activos para auditar."
        )
    return validate_and_save(session)


@transaction.atomic
def freeze_physical_audit(*, session_id, data, actor_id):
    session = _lock_session(session_id)
    if session.status not in {PhysicalAuditStatus.DRAFT, PhysicalAuditStatus.PREPARING}:
        raise InventoryStateError("Sólo una auditoría en preparación puede congelarse.")
    if session.items.filter(is_deleted=False).exists():
        raise InventoryConflictError("La auditoría ya contiene una población congelada.")
    assets = list(_asset_population(session))
    items = []
    for asset in assets:
        custodian = asset.current_custodian
        items.append(PhysicalAuditItem(
            session=session, asset=asset, was_expected=True,
            inventory_number_snapshot=asset.official_inventory_number,
            internal_number_snapshot=asset.internal_inventory_number,
            serial_number_snapshot=asset.serial_number or "",
            asset_name_snapshot=asset.name,
            expected_sede=asset.current_sede,
            expected_dependencia=asset.current_dependencia,
            expected_area=asset.current_area,
            expected_custodian=custodian,
            expected_sede_name_snapshot=str(asset.current_sede or ""),
            expected_dependencia_name_snapshot=str(asset.current_dependencia or ""),
            expected_area_name_snapshot=str(asset.current_area or ""),
            expected_custodian_name_snapshot=(custodian.get_full_name() or str(custodian)) if custodian else "",
            expected_custodian_email_snapshot=getattr(custodian, "email", "") if custodian else "",
            expected_condition=asset.physical_condition,
        ))
    PhysicalAuditItem.objects.bulk_create(items, batch_size=500)
    session.status = PhysicalAuditStatus.FROZEN
    session.snapshot_at = data.snapshot_at
    session.frozen_at = timezone.now()
    session.frozen_by_id = actor_id
    session.expected_assets_count = len(items)
    return validate_and_save(session)


@transaction.atomic
def start_physical_audit(*, session_id, data, actor_id):
    session = _lock_session(session_id)
    if session.status != PhysicalAuditStatus.FROZEN:
        raise InventoryStateError("La auditoría debe estar congelada antes de iniciar.")
    session.status = PhysicalAuditStatus.IN_PROGRESS
    session.started_at = data.started_at
    session.started_by_id = actor_id
    return validate_and_save(session)


def _determine_result(item, *, condition, site_id, department_id, area_id, custodian_id):
    location_differs = any((
        site_id and site_id != item.expected_sede_id,
        department_id and department_id != item.expected_dependencia_id,
        area_id and area_id != item.expected_area_id,
    ))
    custodian_differs = bool(custodian_id and custodian_id != item.expected_custodian_id)
    if condition and condition != item.expected_condition and condition in {
        PhysicalCondition.BAD, PhysicalCondition.UNSERVICEABLE
    }:
        return PhysicalAuditResult.DAMAGED
    if location_differs and custodian_differs:
        return PhysicalAuditResult.FOUND_DIFFERENT_LOCATION_AND_CUSTODIAN
    if location_differs:
        return PhysicalAuditResult.FOUND_DIFFERENT_LOCATION
    if custodian_differs:
        return PhysicalAuditResult.FOUND_DIFFERENT_CUSTODIAN
    return PhysicalAuditResult.FOUND


@transaction.atomic
def scan_physical_audit_item(*, session_id, data, actor_id):
    session = _lock_session(session_id)
    if session.status != PhysicalAuditStatus.IN_PROGRESS:
        raise InventoryStateError("La auditoría no está recibiendo lecturas.")
    code = str(data.scanned_inventory_number or "").strip().upper()
    try:
        item = PhysicalAuditItem.objects.select_for_update().get(
            Q(inventory_number_snapshot__iexact=code)
            | Q(internal_number_snapshot__iexact=code)
            | Q(serial_number_snapshot__iexact=code),
            session=session, was_expected=True, is_deleted=False,
        )
    except PhysicalAuditItem.DoesNotExist as exc:
        raise InventoryValidationError(
            "El código no pertenece a la población esperada; regístrelo como sobrante."
        ) from exc
    if item.scanned_at:
        raise InventoryConflictError("Este activo ya fue leído en la auditoría.")
    site, department, area, custodian = _directory_values(data)
    result = _determine_result(
        item, condition=data.observed_condition, site_id=getattr(site, "id", None),
        department_id=getattr(department, "id", None), area_id=getattr(area, "id", None),
        custodian_id=getattr(custodian, "id", None),
    )
    reason = str(data.discrepancy_reason or "").strip()
    if result != PhysicalAuditResult.FOUND and not reason:
        reason = "Diferencia detectada automáticamente durante la lectura física."
    item.scanned_inventory_number = code
    item.result = result
    item.observed_sede_id = getattr(site, "id", None)
    item.observed_dependencia_id = getattr(department, "id", None)
    item.observed_area_id = getattr(area, "id", None)
    item.observed_custodian_id = getattr(custodian, "id", None)
    item.observed_sede_name_snapshot = getattr(site, "name", "")
    item.observed_dependencia_name_snapshot = getattr(department, "name", "")
    item.observed_area_name_snapshot = getattr(area, "name", "")
    item.observed_custodian_name_snapshot = getattr(custodian, "display_name", "")
    item.observed_custodian_email_snapshot = getattr(custodian, "email", "")
    item.observed_condition = data.observed_condition
    item.scanned_by_id = actor_id
    item.scanned_at = timezone.now()
    item.discrepancy_reason = reason
    item.latitude = getattr(data.geolocation, "latitude", None)
    item.longitude = getattr(data.geolocation, "longitude", None)
    item.evidence = dict(data.evidence or {})
    item.notes = str(data.notes or "").strip()
    validate_and_save(item)
    _refresh_counters(session)
    return item


@transaction.atomic
def register_unlisted_audit_item(*, session_id, data, actor_id):
    session = _lock_session(session_id)
    if session.status != PhysicalAuditStatus.IN_PROGRESS:
        raise InventoryStateError("La auditoría no está recibiendo lecturas.")
    code = str(data.scanned_inventory_number or "").strip().upper()
    if not code:
        raise InventoryValidationError("Capture el identificador encontrado.")
    if session.items.filter(scanned_inventory_number__iexact=code, is_deleted=False).exists():
        raise InventoryConflictError("Este código ya fue registrado.")
    site, department, area, custodian = _directory_values(data)
    item = PhysicalAuditItem(
        session=session, was_expected=False, scanned_inventory_number=code,
        result=PhysicalAuditResult.UNREGISTERED,
        observed_sede_id=getattr(site, "id", None),
        observed_dependencia_id=getattr(department, "id", None),
        observed_area_id=getattr(area, "id", None),
        observed_custodian_id=getattr(custodian, "id", None),
        observed_sede_name_snapshot=getattr(site, "name", ""),
        observed_dependencia_name_snapshot=getattr(department, "name", ""),
        observed_area_name_snapshot=getattr(area, "name", ""),
        observed_custodian_name_snapshot=getattr(custodian, "display_name", ""),
        observed_custodian_email_snapshot=getattr(custodian, "email", ""),
        observed_condition=data.observed_condition,
        scanned_by_id=actor_id, scanned_at=timezone.now(),
        latitude=getattr(data.geolocation, "latitude", None),
        longitude=getattr(data.geolocation, "longitude", None),
        evidence=dict(data.evidence or {}), notes=str(data.notes or "").strip(),
    )
    validate_and_save(item)
    _refresh_counters(session)
    return item


@transaction.atomic
def mark_audit_item_not_found(*, item_id, data, actor_id):
    item = _lock_item(item_id)
    if item.session.status != PhysicalAuditStatus.IN_PROGRESS or item.scanned_at:
        raise InventoryStateError("Sólo una partida pendiente puede marcarse no localizada.")
    item.result = PhysicalAuditResult.NOT_FOUND
    item.discrepancy_reason = str(data.reason or "").strip()
    validate_and_save(item)
    _refresh_counters(item.session)
    return item


@transaction.atomic
def begin_physical_audit_reconciliation(*, session_id, actor_id):
    session = _lock_session(session_id)
    if session.status != PhysicalAuditStatus.IN_PROGRESS:
        raise InventoryStateError("El levantamiento no está en curso.")
    session.status = PhysicalAuditStatus.RECONCILIATION
    return validate_and_save(session)


@transaction.atomic
def reconcile_physical_audit_item(*, item_id, data, actor_id):
    item = _lock_item(item_id)
    if item.session.status != PhysicalAuditStatus.RECONCILIATION:
        raise InventoryStateError("La auditoría no está en conciliación.")
    if data.result not in {value for value, _ in PhysicalAuditResult.choices} - {PhysicalAuditResult.PENDING}:
        raise InventoryValidationError("El resultado de conciliación no es válido.")
    if data.create_corrective_movement:
        raise InventoryValidationError(
            "La corrección debe tramitarse desde Movimientos; la auditoría conserva el hallazgo original."
        )
    item.result = data.result
    item.reconciliation_notes = str(data.notes or "").strip()
    item.reconciled_by_id = actor_id
    item.reconciled_at = timezone.now()
    if item.result in DISCREPANCY_RESULTS and not item.discrepancy_reason:
        item.discrepancy_reason = item.reconciliation_notes
    validate_and_save(item)
    _refresh_counters(item.session)
    return item


@transaction.atomic
def close_physical_audit(*, session_id, data, actor_id):
    session = _lock_session(session_id)
    if session.status != PhysicalAuditStatus.RECONCILIATION:
        raise InventoryStateError("La auditoría debe estar en conciliación para cerrarse.")
    if session.items.filter(result=PhysicalAuditResult.PENDING, is_deleted=False).exists():
        raise InventoryConflictError("Existen activos pendientes de clasificar.")
    if session.items.filter(result__in=DISCREPANCY_RESULTS, reconciled_at__isnull=True, is_deleted=False).exists():
        raise InventoryConflictError("Existen discrepancias pendientes de conciliación.")
    session.status = PhysicalAuditStatus.CLOSED
    session.closed_by_id = actor_id
    session.closed_at = timezone.now()
    session.closing_summary = str(data.closing_summary or "").strip()
    return validate_and_save(session)


@transaction.atomic
def cancel_physical_audit(*, session_id, data, actor_id):
    session = _lock_session(session_id)
    if session.status in {PhysicalAuditStatus.CLOSED, PhysicalAuditStatus.CANCELLED}:
        raise InventoryStateError("La auditoría ya no puede cancelarse.")
    session.status = PhysicalAuditStatus.CANCELLED
    session.cancelled_by_id = actor_id
    session.cancelled_at = timezone.now()
    session.cancellation_reason = str(data.reason or "").strip()
    return validate_and_save(session)


__all__ = [name for name in globals() if name.endswith("physical_audit") or "audit_item" in name]
