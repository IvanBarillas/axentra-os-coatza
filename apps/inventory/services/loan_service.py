"""Flujo transaccional de préstamos temporales de activos."""

from uuid import uuid4

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from apps.inventory.dtos import LoanTransitionResultDTO
from apps.inventory.integrations import core_directory
from apps.inventory.models import (
    Asset,
    AssetDocument,
    AssetLoan,
    AssetLoanStatus,
    AssetOperationalStatus,
    DisposalRequest,
    DisposalStatus,
    DocumentType,
    DocumentValidationStatus,
    InventoryAuditAction,
    InventoryDocumentOwnerType,
    InventoryMovement,
    MovementReferenceType,
    MovementType,
)
from apps.inventory.services.audit_service import (
    build_audit_request_context,
    log_inventory_event,
    model_snapshot,
)
from apps.inventory.services.exceptions import (
    InventoryAuthorizationError,
    InventoryConflictError,
    InventoryStateError,
    InventoryValidationError,
)
from apps.inventory.services.folio_service import get_effective_folio_policy


REQUEST_PERMISSION = "can_request_loans"
DEPARTMENT_PERMISSION = "can_authorize_loans"
MANAGE_PERMISSION = "can_manage_loans"
OPEN_DISPOSAL_STATUSES = {
    DisposalStatus.SUBMITTED,
    DisposalStatus.EVIDENCE_PENDING,
    DisposalStatus.TECHNICAL_REVIEW,
    DisposalStatus.ADMINISTRATIVE_REVIEW,
    DisposalStatus.AUTHORIZATION_PENDING,
    DisposalStatus.APPROVED,
}


def _text(value):
    return str(value or "").strip()


def _loan_folio(*, loan_id, requested_at, department):
    """Construye un folio institucional legible y único."""
    policy = get_effective_folio_policy(effective_on=requested_at.date())
    municipality_code = _text(policy.municipality_code).upper().zfill(3)
    department_code = _text(department.normalized_code).upper()
    if not department_code:
        raise InventoryValidationError(
            "La dependencia propietaria no tiene código presupuestal."
        )
    return (
        f"PRE-{municipality_code}-{department_code}-"
        f"{requested_at:%Y}-{loan_id.hex[:8].upper()}"
    )


def _actor(actor_id):
    try:
        identity = core_directory.get_user_identity(actor_id)
        role = core_directory.get_module_role(identity.id)
    except core_directory.CoreDirectoryError as exc:
        raise InventoryAuthorizationError(str(exc)) from exc
    return identity, role


def _require(actor_id, permission):
    identity, role = _actor(actor_id)
    if identity.has_global_bypass or (role and role.has_permission(permission)):
        return identity
    raise InventoryAuthorizationError(
        f"La operación requiere el permiso [{permission}]."
    )


def _can_operate_origin(loan, actor, role):
    if actor.has_global_bypass:
        return True
    if not (
        role
        and (
            role.has_permission(REQUEST_PERMISSION)
            or role.has_permission(MANAGE_PERMISSION)
        )
    ):
        return False
    try:
        context = core_directory.get_user_organizational_context(
            actor.id,
            require_profile=True,
        )
    except core_directory.CoreDirectoryError:
        return False
    return context.department_id == loan.origin_dependencia_id


def _has_current_acknowledgement(loan_id, document_type):
    return AssetDocument.objects.filter(
        owner_type=InventoryDocumentOwnerType.LOAN,
        owner_id=loan_id,
        document_type=document_type,
        is_current_version=True,
        is_deleted=False,
        validation_status=DocumentValidationStatus.VALIDATED,
    ).exists()


def _lock(loan_id):
    try:
        return AssetLoan.objects.select_for_update().select_related("asset").get(
            pk=loan_id,
            is_deleted=False,
        )
    except AssetLoan.DoesNotExist as exc:
        raise InventoryValidationError("El préstamo no existe.") from exc


def _save(instance):
    instance.full_clean()
    try:
        instance.save()
    except IntegrityError as exc:
        raise InventoryConflictError(
            "El activo ya tiene un préstamo vigente o en proceso."
        ) from exc


def _audit(loan, actor, action, summary, context, old=None):
    log_inventory_event(
        action=action,
        summary=summary,
        actor_id=actor.id,
        asset_id=loan.asset_id,
        target=loan,
        old_value=old or {},
        new_value=model_snapshot(loan),
        request_context=context,
        bypass_used=loan.bypass_used,
        bypass_reason=loan.bypass_reason,
    )


def _result(loan, previous, movement=None):
    return LoanTransitionResultDTO(
        loan_id=loan.id,
        asset_id=loan.asset_id,
        previous_status=previous,
        current_status=loan.status,
        movement_id=movement.id if movement else None,
        bypass_used=loan.bypass_used,
    )


def _directory_snapshot(department_id=None, area_id=None, site_id=None):
    snapshot = {}
    department = area = site = None
    try:
        if department_id:
            department = core_directory.get_department(department_id)
            snapshot["dependencia"] = {
                "id": str(department.id),
                "nombre": department.name,
                "codigo": department.code,
            }
        if area_id:
            area = core_directory.get_area_context(area_id)
            snapshot["area"] = {"id": str(area.id), "nombre": area.name}
        if site_id:
            site = core_directory.get_site(site_id)
            snapshot["sede"] = {"id": str(site.id), "nombre": site.name}
        if department_id:
            core_directory.validate_organizational_context(
                department_id=department_id,
                area_id=area_id,
                site_id=site_id,
            )
    except core_directory.CoreDirectoryError as exc:
        raise InventoryValidationError(str(exc)) from exc
    return department, area, site, snapshot


def _fill_location(movement, prefix, department, area, site):
    if department:
        setattr(movement, f"{prefix}_dependencia_id", department.id)
        setattr(movement, f"{prefix}_dependencia_id_snapshot", department.id)
        setattr(movement, f"{prefix}_dependencia_name_snapshot", department.name)
        setattr(movement, f"{prefix}_dependencia_code_snapshot", department.code)
    if area:
        setattr(movement, f"{prefix}_area_id", area.id)
        setattr(movement, f"{prefix}_area_id_snapshot", area.id)
        setattr(movement, f"{prefix}_area_name_snapshot", area.name)
    if site:
        setattr(movement, f"{prefix}_sede_id", site.id)
        setattr(movement, f"{prefix}_sede_id_snapshot", site.id)
        setattr(movement, f"{prefix}_sede_name_snapshot", site.name)


def _loan_movement(loan, actor, movement_type, occurred_at, reason, *, returning=False):
    asset = loan.asset
    movement = InventoryMovement(
        asset=asset,
        movement_type=movement_type,
        performed_by_id=actor.id,
        performed_by_name_snapshot=actor.display_name,
        performed_by_email_snapshot=actor.normalized_email,
        occurred_at=occurred_at,
        recorded_at=timezone.now(),
        reason=reason,
        reference_folio=loan.folio,
        reference_type=MovementReferenceType.LOAN,
        reference_id=loan.id,
        condition_before=asset.physical_condition,
        condition_after=(
            loan.return_condition if returning else loan.delivery_condition
        ),
        payload={
            "external_borrower": loan.external_borrower,
            "external_destination": loan.external_destination,
            "borrower_name": loan.borrower_name_snapshot,
        },
    )
    origin_department, origin_area, origin_site, _ = _directory_snapshot(
        loan.origin_dependencia_id,
        loan.origin_area_id,
        loan.origin_sede_id,
    )
    destination_department, destination_area, destination_site, _ = _directory_snapshot(
        loan.destination_dependencia_id,
        loan.destination_area_id,
        loan.destination_sede_id,
    )
    if returning:
        _fill_location(movement, "from", destination_department, destination_area, destination_site)
        _fill_location(movement, "to", origin_department, origin_area, origin_site)
        if loan.borrower_id:
            borrower = core_directory.get_user_identity(loan.borrower_id, include_unavailable=True)
            movement.from_user_id = borrower.id
            movement.from_user_id_snapshot = borrower.id
            movement.from_user_name_snapshot = borrower.display_name
            movement.from_user_email_snapshot = borrower.normalized_email
        if asset.current_custodian_id:
            custodian = core_directory.get_user_identity(asset.current_custodian_id, include_unavailable=True)
            movement.to_user_id = custodian.id
            movement.to_user_id_snapshot = custodian.id
            movement.to_user_name_snapshot = custodian.display_name
            movement.to_user_email_snapshot = custodian.normalized_email
    else:
        _fill_location(movement, "from", origin_department, origin_area, origin_site)
        _fill_location(movement, "to", destination_department, destination_area, destination_site)
        if asset.current_custodian_id:
            custodian = core_directory.get_user_identity(asset.current_custodian_id, include_unavailable=True)
            movement.from_user_id = custodian.id
            movement.from_user_id_snapshot = custodian.id
            movement.from_user_name_snapshot = custodian.display_name
            movement.from_user_email_snapshot = custodian.normalized_email
        if loan.borrower_id:
            borrower = core_directory.get_user_identity(loan.borrower_id, include_unavailable=True)
            movement.to_user_id = borrower.id
            movement.to_user_id_snapshot = borrower.id
            movement.to_user_name_snapshot = borrower.display_name
            movement.to_user_email_snapshot = borrower.normalized_email
    movement.full_clean()
    movement.save()
    return movement


@transaction.atomic
def create_asset_loan(*, data, actor_id, request=None):
    actor, role = _actor(actor_id)
    can_manage = bool(
        actor.has_global_bypass
        or (role and role.has_permission(MANAGE_PERMISSION))
    )
    can_request = bool(
        can_manage
        or (role and role.has_permission(REQUEST_PERMISSION))
    )
    if not can_request:
        raise InventoryAuthorizationError(
            f"La operación requiere el permiso [{REQUEST_PERMISSION}] o [{MANAGE_PERMISSION}]."
        )
    context = build_audit_request_context(request)
    try:
        asset = Asset.objects.select_for_update().get(pk=data.asset_id, is_deleted=False)
    except Asset.DoesNotExist as exc:
        raise InventoryValidationError("El activo no existe.") from exc
    if asset.operational_status not in {AssetOperationalStatus.AVAILABLE, AssetOperationalStatus.ASSIGNED}:
        raise InventoryStateError("El activo no está disponible para préstamo.")
    blocking_disposal = (
        DisposalRequest.objects.select_for_update()
        .filter(
            asset=asset,
            status__in=OPEN_DISPOSAL_STATUSES,
            is_deleted=False,
        )
        .order_by("-requested_at")
        .first()
    )
    if blocking_disposal:
        raise InventoryConflictError(
            f"El bien forma parte de la baja {blocking_disposal.folio}. "
            "Debe concluirla o cancelarla antes de crear un préstamo."
        )
    if AssetLoan.objects.filter(
        asset=asset,
        is_deleted=False,
        status__in=(
            AssetLoanStatus.REQUESTED,
            AssetLoanStatus.DEPARTMENT_APPROVED,
            AssetLoanStatus.AUTHORIZED,
            AssetLoanStatus.DELIVERED,
            AssetLoanStatus.OVERDUE,
            AssetLoanStatus.RETURN_PENDING,
        ),
    ).exists():
        raise InventoryConflictError("El activo ya tiene un préstamo abierto.")
    if not data.origin_department_id or not data.origin_site_id:
        raise InventoryValidationError(
            "El bien debe tener dependencia y sede vigentes antes de prestarse."
        )
    if not actor.has_global_bypass:
        actor_context = core_directory.get_user_organizational_context(
            actor.id,
            require_profile=True,
        )
        if actor_context.department_id != asset.current_dependencia_id:
            raise InventoryAuthorizationError(
                "Sólo puede prestar bienes de su dependencia."
            )
    origin_department, origin_area, origin_site, origin_snapshot = _directory_snapshot(
        data.origin_department_id, data.origin_area_id, data.origin_site_id
    )
    if origin_department.id != asset.current_dependencia_id:
        raise InventoryValidationError("La dependencia origen no corresponde al activo.")
    if origin_site and origin_site.id != asset.current_sede_id:
        raise InventoryValidationError("La sede de origen no corresponde a la ubicación actual del activo.")
    if origin_area and origin_area.id != asset.current_area_id:
        raise InventoryValidationError("El área de origen no corresponde a la ubicación actual del activo.")
    borrower = None
    if data.external_borrower:
        if not _text(data.external_organization) or not _text(data.external_identification):
            raise InventoryValidationError("El préstamo externo requiere institución e identificación.")
    else:
        if data.borrower_id:
            borrower = core_directory.get_user_identity(data.borrower_id)
    destination_department, destination_area, destination_site, destination_snapshot = _directory_snapshot(
        data.destination_department_id, data.destination_area_id, data.destination_site_id
    )
    if not data.external_borrower and not destination_department:
        raise InventoryValidationError("Debe indicar la dependencia receptora.")
    now = timezone.now()
    if data.due_at <= now:
        raise InventoryValidationError("La fecha límite debe ser posterior a la solicitud.")
    loan_id = uuid4()
    loan = AssetLoan(
        id=loan_id,
        folio=_loan_folio(
            loan_id=loan_id,
            requested_at=now,
            department=origin_department,
        ),
        asset=asset,
        requested_by_id=actor.id,
        requested_at=now,
        borrower_id=borrower.id if borrower else None,
        borrower_id_snapshot=borrower.id if borrower else None,
        borrower_name_snapshot=(borrower.display_name if borrower else _text(data.borrower_name)),
        borrower_email_snapshot=(borrower.normalized_email if borrower else _text(data.borrower_email)),
        borrower_position_snapshot=_text(data.borrower_position),
        external_borrower=data.external_borrower,
        external_organization=_text(data.external_organization),
        external_identification=_text(data.external_identification),
        origin_dependencia_id=origin_department.id,
        origin_area_id=origin_area.id if origin_area else None,
        origin_sede_id=origin_site.id if origin_site else None,
        destination_dependencia_id=destination_department.id if destination_department else None,
        destination_area_id=destination_area.id if destination_area else None,
        destination_sede_id=destination_site.id if destination_site else None,
        external_destination=_text(data.external_destination),
        origin_snapshot=origin_snapshot,
        destination_snapshot=destination_snapshot,
        due_at=data.due_at,
        purpose=_text(data.purpose),
    )
    _save(loan)
    _audit(loan, actor, InventoryAuditAction.CREATE, "Préstamo creado en borrador", context)
    return loan


def _transition(loan_id, actor, expected, target, context, action, summary, mutate=None):
    loan = _lock(loan_id)
    if loan.status not in set(expected):
        raise InventoryStateError("El préstamo no puede procesarse desde su estado actual.")
    previous = loan.status
    old = model_snapshot(loan)
    loan.status = target
    if mutate:
        mutate(loan)
    _save(loan)
    _audit(loan, actor, action, summary, context, old)
    return loan, previous


@transaction.atomic
def submit_asset_loan(*, loan_id, actor_id, request=None):
    actor = _require(actor_id, REQUEST_PERMISSION)
    context = build_audit_request_context(request)
    loan = _lock(loan_id)
    if loan.requested_by_id != actor.id and not actor.has_global_bypass:
        raise InventoryAuthorizationError("Sólo el solicitante puede enviar el préstamo.")
    blocking_disposal = (
        DisposalRequest.objects.select_for_update()
        .filter(
            asset_id=loan.asset_id,
            status__in=OPEN_DISPOSAL_STATUSES,
            is_deleted=False,
        )
        .order_by("-requested_at")
        .first()
    )
    if blocking_disposal:
        raise InventoryConflictError(
            f"El bien forma parte de la baja {blocking_disposal.folio}. "
            "No puede enviarse el préstamo mientras ese expediente esté activo."
        )
    loan, previous = _transition(loan_id, actor, {AssetLoanStatus.DRAFT, AssetLoanStatus.REJECTED}, AssetLoanStatus.REQUESTED, context, InventoryAuditAction.SUBMIT, "Préstamo enviado a la dependencia receptora")
    return _result(loan, previous)


@transaction.atomic
def decide_department_loan(*, loan_id, actor_id, data, request=None):
    actor = _require(actor_id, DEPARTMENT_PERMISSION)
    context = build_audit_request_context(request)
    loan = _lock(loan_id)
    actor_context = core_directory.get_user_organizational_context(actor.id, require_profile=True)
    if loan.external_borrower:
        raise InventoryAuthorizationError("Los préstamos externos deben ser revisados directamente por Patrimonio.")
    if actor_context.department_id != loan.destination_dependencia_id and not actor.has_global_bypass:
        raise InventoryAuthorizationError("Sólo la dirección receptora puede decidir esta solicitud.")
    if data.approve:
        if not data.destination_area_id:
            raise InventoryValidationError("Debe seleccionar el área que recibirá el bien.")
        destination_area = core_directory.get_area_context(data.destination_area_id)
        if destination_area.department_id != loan.destination_dependencia_id:
            raise InventoryValidationError("El área seleccionada no pertenece a la dependencia receptora.")
        borrower = None
        borrower_context = None
        if data.borrower_id:
            borrower = core_directory.get_user_identity(data.borrower_id)
            borrower_context = core_directory.get_user_organizational_context(
                borrower.id,
                require_profile=True,
            )
            if borrower_context.department_id != loan.destination_dependencia_id:
                raise InventoryValidationError("El responsable seleccionado no pertenece a la dependencia receptora.")
            if borrower_context.area_id and borrower_context.area_id != destination_area.id:
                raise InventoryValidationError("El responsable seleccionado no pertenece al área receptora.")
        _, _, destination_site, destination_snapshot = _directory_snapshot(
            loan.destination_dependencia_id,
            destination_area.id,
            destination_area.site_id,
        )
        def mutate(item):
            item.department_approved_by_id = actor.id
            item.department_approved_at = timezone.now()
            item.destination_area_id = destination_area.id
            item.destination_sede_id = destination_site.id
            item.destination_snapshot = destination_snapshot
            item.borrower_id = borrower.id if borrower else None
            item.borrower_id_snapshot = borrower.id if borrower else None
            item.borrower_name_snapshot = borrower.display_name if borrower else ""
            item.borrower_email_snapshot = borrower.normalized_email if borrower else ""
            item.borrower_position_snapshot = borrower_context.position if borrower_context else ""
        target, action, summary = AssetLoanStatus.DEPARTMENT_APPROVED, InventoryAuditAction.APPROVE, "Préstamo aceptado por la dependencia receptora"
    else:
        reason = _text(data.comment)
        if not reason:
            raise InventoryValidationError("Debe indicar el motivo del rechazo.")
        def mutate(item):
            item.rejected_by_id = actor.id
            item.rejected_at = timezone.now()
            item.rejection_reason = reason
        target, action, summary = AssetLoanStatus.REJECTED, InventoryAuditAction.REJECT, "Préstamo rechazado por la dependencia receptora"
    loan, previous = _transition(loan_id, actor, {AssetLoanStatus.REQUESTED}, target, context, action, summary, mutate)
    return _result(loan, previous)


@transaction.atomic
def authorize_asset_loan(*, loan_id, actor_id, data, request=None):
    actor = _require(actor_id, MANAGE_PERMISSION)
    context = build_audit_request_context(request)
    loan = _lock(loan_id)
    if not loan.external_borrower:
        raise InventoryStateError(
            "Los préstamos internos no requieren autorización de Patrimonio."
        )
    allowed = {AssetLoanStatus.REQUESTED}
    if data.approve:
        def mutate(item):
            item.authorized_by_id = actor.id
            item.authorized_at = timezone.now()
        target, action, summary = AssetLoanStatus.AUTHORIZED, InventoryAuditAction.APPROVE, "Préstamo autorizado por Patrimonio"
    else:
        reason = _text(data.comment)
        if not reason:
            raise InventoryValidationError("Debe indicar el motivo del rechazo.")
        def mutate(item):
            item.rejected_by_id = actor.id
            item.rejected_at = timezone.now()
            item.rejection_reason = reason
        target, action, summary = AssetLoanStatus.REJECTED, InventoryAuditAction.REJECT, "Préstamo rechazado por Patrimonio"
    loan, previous = _transition(loan_id, actor, allowed, target, context, action, summary, mutate)
    return _result(loan, previous)


@transaction.atomic
def deliver_asset_loan(*, loan_id, actor_id, data, request=None):
    actor, role = _actor(actor_id)
    context = build_audit_request_context(request)
    loan = _lock(loan_id)
    if not _can_operate_origin(loan, actor, role):
        raise InventoryAuthorizationError(
            "Sólo la dependencia propietaria puede registrar la entrega."
        )
    expected_status = (
        AssetLoanStatus.AUTHORIZED
        if loan.external_borrower
        else AssetLoanStatus.DEPARTMENT_APPROVED
    )
    if not _has_current_acknowledgement(
        loan.id,
        DocumentType.SIGNED_LOAN_RECEIPT,
    ):
        raise InventoryStateError(
            "Integre el acuse firmado del vale antes de registrar la entrega."
        )
    def mutate(item):
        item.delivered_by_id = actor.id
        item.delivered_at = data.delivered_at
        item.delivery_condition = data.delivery_condition
        item.delivery_notes = _text(data.notes)
    loan, previous = _transition(loan_id, actor, {expected_status}, AssetLoanStatus.DELIVERED, context, InventoryAuditAction.LOAN, "Bien entregado en préstamo", mutate)
    movement = _loan_movement(loan, actor, MovementType.LOAN, loan.delivered_at, loan.purpose)
    loan.asset.operational_status = AssetOperationalStatus.LOANED
    loan.asset.full_clean()
    loan.asset.save()
    return _result(loan, previous, movement)


@transaction.atomic
def request_asset_loan_return(*, loan_id, actor_id, data, request=None):
    actor, role = _actor(actor_id)
    can_manage = role and role.has_permission(MANAGE_PERMISSION)
    loan = _lock(loan_id)
    destination_authority = False
    if role and role.has_permission(DEPARTMENT_PERMISSION):
        try:
            actor_context = core_directory.get_user_organizational_context(
                actor.id,
                require_profile=True,
            )
            destination_authority = (
                actor_context.department_id == loan.destination_dependencia_id
            )
        except core_directory.CoreDirectoryError:
            destination_authority = False
    if not actor.has_global_bypass and actor.id not in {loan.borrower_id, loan.requested_by_id} and not can_manage and not destination_authority:
        raise InventoryAuthorizationError("No puede solicitar la devolución de este préstamo.")
    context = build_audit_request_context(request)
    def mutate(item):
        item.return_requested_at = data.requested_at
        item.return_notes = _text(data.notes)
    loan, previous = _transition(loan_id, actor, {AssetLoanStatus.DELIVERED, AssetLoanStatus.OVERDUE}, AssetLoanStatus.RETURN_PENDING, context, InventoryAuditAction.RETURN, "Devolución del préstamo solicitada", mutate)
    return _result(loan, previous)


@transaction.atomic
def return_asset_loan(*, loan_id, actor_id, data, request=None):
    actor, role = _actor(actor_id)
    context = build_audit_request_context(request)
    loan = _lock(loan_id)
    if not _can_operate_origin(loan, actor, role):
        raise InventoryAuthorizationError(
            "Sólo la dependencia propietaria puede registrar la devolución."
        )
    if not _has_current_acknowledgement(
        loan.id,
        DocumentType.SIGNED_RETURN_RECEIPT,
    ):
        raise InventoryStateError(
            "Integre el acuse firmado de devolución antes de cerrar el préstamo."
        )
    def mutate(item):
        item.returned_by_id = data.returned_by_id
        item.received_return_by_id = actor.id
        item.returned_at = data.returned_at
        item.return_condition = data.return_condition
        item.return_notes = _text(data.notes)
    loan, previous = _transition(loan_id, actor, {AssetLoanStatus.RETURN_PENDING}, AssetLoanStatus.RETURNED, context, InventoryAuditAction.RETURN, "Bien recibido de regreso", mutate)
    movement = _loan_movement(loan, actor, MovementType.RETURN, loan.returned_at, "Devolución de préstamo", returning=True)
    loan.asset.operational_status = AssetOperationalStatus.ASSIGNED if loan.asset.current_custodian_id else AssetOperationalStatus.AVAILABLE
    loan.asset.physical_condition = loan.return_condition
    loan.asset.full_clean()
    loan.asset.save()
    return _result(loan, previous, movement)


@transaction.atomic
def cancel_asset_loan(*, loan_id, actor_id, data, request=None):
    actor, role = _actor(actor_id)
    loan = _lock(loan_id)
    can_manage = role and role.has_permission(MANAGE_PERMISSION)
    if loan.requested_by_id != actor.id and not actor.has_global_bypass and not can_manage:
        raise InventoryAuthorizationError("No puede cancelar este préstamo.")
    reason = _text(data.reason)
    if not reason:
        raise InventoryValidationError("Debe indicar el motivo de cancelación.")
    context = build_audit_request_context(request)
    loan, previous = _transition(loan_id, actor, {AssetLoanStatus.DRAFT, AssetLoanStatus.REQUESTED, AssetLoanStatus.REJECTED}, AssetLoanStatus.CANCELLED, context, InventoryAuditAction.REJECT, f"Préstamo cancelado: {reason}")
    return _result(loan, previous)


__all__ = [
    "authorize_asset_loan",
    "cancel_asset_loan",
    "create_asset_loan",
    "decide_department_loan",
    "deliver_asset_loan",
    "request_asset_loan_return",
    "return_asset_loan",
    "submit_asset_loan",
]
