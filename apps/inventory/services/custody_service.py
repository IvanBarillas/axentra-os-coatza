"""Flujo transaccional de resguardos patrimoniales."""

from uuid import uuid4

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.inventory.dtos import CustodyTransitionResultDTO
from apps.inventory.integrations import core_directory
from apps.inventory.models import (
    Asset,
    AssetOperationalStatus,
    CustodyAcceptanceMethod,
    CustodyAssignment,
    CustodyAssigneeMode,
    CustodyAssignmentEvent,
    CustodyEventType,
    CustodyStatus,
    InventoryAuditAction,
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


MANAGE_PERMISSION = "can_manage_custody"
ACCEPT_PERMISSION = "can_accept_custody"


def _text(value):
    return str(value or "").strip()


def _actor(actor_id):
    try:
        identity = core_directory.get_user_identity(actor_id)
        role = core_directory.get_module_role(identity.id)
    except core_directory.CoreDirectoryError as exc:
        raise InventoryAuthorizationError(str(exc)) from exc
    return identity, role


def _require_permission(actor_id, permission):
    identity, role = _actor(actor_id)
    if identity.has_global_bypass or (role and role.has_permission(permission)):
        return identity
    raise InventoryAuthorizationError(
        f"La operación requiere el permiso [{permission}]."
    )


def _lock(custody_id):
    try:
        return CustodyAssignment.objects.select_for_update().get(
            pk=custody_id,
            is_deleted=False,
        )
    except CustodyAssignment.DoesNotExist as exc:
        raise InventoryValidationError("El resguardo no existe.") from exc


def _validate_save(instance):
    instance.full_clean()
    try:
        instance.save()
    except IntegrityError as exc:
        raise InventoryConflictError(
            "El activo ya tiene un resguardo vigente o en proceso."
        ) from exc


def _event(custody, event_type, previous, actor, context, *, comment=""):
    event = CustodyAssignmentEvent(
        custody_assignment=custody,
        event_type=event_type,
        previous_status=previous,
        resulting_status=custody.status,
        actor_id=actor.id,
        actor_name_snapshot=actor.display_name,
        actor_email_snapshot=actor.normalized_email,
        comment=_text(comment),
        bypass_used=custody.bypass_used,
        bypass_reason=custody.bypass_reason if custody.bypass_used else "",
        ip_address=context.ip_address,
        user_agent=context.user_agent,
        payload=model_snapshot(custody),
    )
    event.full_clean()
    event.save()
    return event


def _result(custody, previous, event):
    return CustodyTransitionResultDTO(
        custody_assignment_id=custody.id,
        asset_id=custody.asset_id,
        previous_status=previous,
        current_status=custody.status,
        event_id=event.id,
        bypass_used=custody.bypass_used,
    )


def _audit(custody, actor, action, summary, context, old):
    log_inventory_event(
        action=action,
        summary=summary,
        actor_id=actor.id,
        asset_id=custody.asset_id,
        target=custody,
        old_value=old,
        new_value=model_snapshot(custody),
        request_context=context,
        bypass_used=custody.bypass_used,
        bypass_reason=custody.bypass_reason,
    )


@transaction.atomic
def create_custody_assignment(*, data, actor_id, request=None):
    actor = _require_permission(actor_id, MANAGE_PERMISSION)
    context = build_audit_request_context(request)

    try:
        asset = (
            Asset.objects
            .select_for_update()
            .select_related(
                "current_sede",
                "current_dependencia",
                "current_area",
            )
            .get(
                pk=data.asset_id,
                is_deleted=False,
            )
        )
    except Asset.DoesNotExist as exc:
        raise InventoryValidationError(
            "El activo no existe."
        ) from exc

    if asset.operational_status not in {
        AssetOperationalStatus.AVAILABLE,
        AssetOperationalStatus.ASSIGNED,
    }:
        raise InventoryStateError(
            "El activo no está disponible para generar un resguardo."
        )

    if not asset.current_dependencia_id:
        raise InventoryValidationError(
            "El activo no tiene una dependencia actual. "
            "Registre primero su ubicación institucional."
        )

    if CustodyAssignment.objects.filter(
        asset=asset,
        is_deleted=False,
        status__in=(
            CustodyStatus.PENDING_AUTHORIZATION,
            CustodyStatus.PENDING_ACCEPTANCE,
            CustodyStatus.ACTIVE,
            CustodyStatus.RETURN_PENDING,
        ),
    ).exists():
        raise InventoryConflictError(
            "El activo ya tiene un resguardo vigente o en proceso."
        )

    try:
        department = core_directory.get_department(
            asset.current_dependencia_id
        )
        area = (
            core_directory.get_area_context(asset.current_area_id)
            if asset.current_area_id else None
        )
        site = (
            core_directory.get_site(asset.current_sede_id)
            if asset.current_sede_id else None
        )

        core_directory.validate_organizational_context(
            department_id=department.id,
            area_id=area.id if area else None,
            site_id=site.id if site else None,
        )

        mode = _text(data.assignee_mode)

        if mode == CustodyAssigneeMode.DEPARTMENT_MANAGER:
            assigned_to_id = department.manager_user_id
            if not assigned_to_id:
                raise InventoryValidationError(
                    "La dependencia actual del bien no tiene un titular "
                    "o encargado registrado. Asígnelo desde Organización "
                    "o seleccione un servidor público."
                )
        elif mode == CustodyAssigneeMode.PUBLIC_SERVANT:
            assigned_to_id = data.assigned_to_id
            if not assigned_to_id:
                raise InventoryValidationError(
                    "Seleccione al servidor público que recibirá "
                    "el resguardo."
                )
        else:
            raise InventoryValidationError(
                "El tipo de responsable seleccionado no es válido."
            )

        assigned = core_directory.get_user_identity(assigned_to_id)
        assigned_context = (
            core_directory.get_user_organizational_context(
                assigned.id,
                require_profile=True,
            )
        )
    except InventoryValidationError:
        raise
    except core_directory.CoreDirectoryError as exc:
        raise InventoryValidationError(str(exc)) from exc

    bypass_reason = _text(data.bypass_reason)

    if bypass_reason and not actor.has_global_bypass:
        raise InventoryAuthorizationError(
            "Sólo un operador con bypass puede justificar una excepción."
        )

    if (
        assigned_context.department_id != department.id
        and not actor.has_global_bypass
    ):
        raise InventoryValidationError(
            "El resguardatario no pertenece a la dependencia "
            "actual del bien."
        )

    custody = CustodyAssignment(
        folio=(
            f"RES-{timezone.localdate():%Y}-"
            f"{uuid4().hex[:10].upper()}"
        ),
        asset=asset,
        assignee_mode=mode,
        assigned_to_id=assigned.id,
        assigned_to_name_snapshot=assigned.display_name,
        assigned_to_email_snapshot=assigned.normalized_email,
        assigned_to_position_snapshot=assigned_context.position,
        dependencia_id=department.id,
        area_id=area.id if area else None,
        sede_id=site.id if site else None,
        dependencia_id_snapshot=department.id,
        dependencia_name_snapshot=department.name,
        dependencia_code_snapshot=department.code,
        area_id_snapshot=area.id if area else None,
        area_name_snapshot=area.name if area else "",
        sede_id_snapshot=site.id if site else None,
        sede_name_snapshot=site.name if site else "",
        prepared_by_id=actor.id,
        notes=_text(data.notes),
        bypass_used=bool(bypass_reason),
        bypass_reason=bypass_reason,
    )
    _validate_save(custody)

    event = _event(
        custody,
        CustodyEventType.CREATED,
        "",
        actor,
        context,
        comment=(
            "Responsable seleccionado como titular de la dependencia."
            if mode == CustodyAssigneeMode.DEPARTMENT_MANAGER
            else "Responsable seleccionado como servidor público."
        ),
    )
    _audit(
        custody,
        actor,
        InventoryAuditAction.CREATE,
        "Resguardo creado",
        context,
        {},
    )
    return custody

def _transition(custody_id, actor_id, expected, target, event_type, action, summary, *, request=None, comment="", mutate=None, permission=MANAGE_PERMISSION):
    actor = _require_permission(actor_id, permission) if permission else _actor(actor_id)[0]
    context = build_audit_request_context(request)
    custody = _lock(custody_id)
    if custody.status not in set(expected):
        raise InventoryStateError("El resguardo no puede procesarse desde su estado actual.")
    previous = custody.status
    old = model_snapshot(custody)
    custody.status = target
    if mutate:
        mutate(custody, actor)
    _validate_save(custody)
    event = _event(custody, event_type, previous, actor, context, comment=comment)
    _audit(custody, actor, action, summary, context, old)
    return _result(custody, previous, event)


@transaction.atomic
def submit_custody_assignment(*, custody_id, actor_id, request=None):
    return _transition(custody_id, actor_id, {CustodyStatus.DRAFT, CustodyStatus.REJECTED}, CustodyStatus.PENDING_AUTHORIZATION, CustodyEventType.SUBMITTED, InventoryAuditAction.SUBMIT, "Resguardo enviado a autorización", request=request)


@transaction.atomic
def authorize_custody_assignment(*, custody_id, actor_id, data, request=None):
    custody = _lock(custody_id)
    actor, role = _actor(actor_id)
    manages = actor.has_global_bypass or bool(
        role and role.has_permission(MANAGE_PERMISSION)
    )
    try:
        authority = core_directory.user_can_approve_department(
            actor.id,
            custody.dependencia_id,
        )
    except core_directory.CoreDirectoryError as exc:
        raise InventoryAuthorizationError(str(exc)) from exc
    if not manages and not authority.allowed:
        raise InventoryAuthorizationError(
            "Sólo Patrimonio o el titular de la dependencia puede autorizar el resguardo."
        )
    def mutate(c, a):
        c.authorized_by_id = a.id
        c.authorized_at = timezone.now()
    return _transition(custody_id, actor_id, {CustodyStatus.PENDING_AUTHORIZATION}, CustodyStatus.PENDING_ACCEPTANCE, CustodyEventType.AUTHORIZED, InventoryAuditAction.APPROVE, "Resguardo autorizado", request=request, comment=data.comment, mutate=mutate, permission=None)


@transaction.atomic
def deliver_custody_assignment(*, custody_id, actor_id, comment="", request=None):
    def mutate(c, a):
        c.delivered_by_id = a.id
        c.delivered_at = timezone.now()
        c.delivery_observations = _text(comment)
    return _transition(custody_id, actor_id, {CustodyStatus.PENDING_ACCEPTANCE}, CustodyStatus.PENDING_ACCEPTANCE, CustodyEventType.DELIVERED, InventoryAuditAction.ASSIGN, "Entrega física registrada", request=request, comment=comment, mutate=mutate)


@transaction.atomic
def accept_custody_assignment(*, custody_id, actor_id, data, request=None):
    identity = _require_permission(actor_id, ACCEPT_PERMISSION)
    custody = _lock(custody_id)
    if custody.assigned_to_id != identity.id and not identity.has_global_bypass:
        raise InventoryAuthorizationError("Sólo el resguardatario puede aceptar este resguardo.")
    if not custody.delivered_at:
        raise InventoryStateError("Patrimonio debe registrar primero la entrega física.")
    if data.acceptance_method == CustodyAcceptanceMethod.DIGITAL_SIGNATURE and not _text(data.signature_hash):
        raise InventoryValidationError("La firma digital requiere su hash.")
    now = timezone.now()
    def mutate(c, a):
        c.accepted_by_id = a.id
        c.accepted_at = now
        c.acceptance_method = data.acceptance_method
        c.digital_signature_hash = _text(data.signature_hash)
        c.assigned_at = now
        c.asset.current_custodian_id = c.assigned_to_id
        c.asset.current_dependencia_id = c.dependencia_id
        c.asset.current_area_id = c.area_id
        c.asset.current_sede_id = c.sede_id
        c.asset.operational_status = AssetOperationalStatus.ASSIGNED
        c.asset.full_clean()
        c.asset.save()
    return _transition(custody_id, actor_id, {CustodyStatus.PENDING_ACCEPTANCE}, CustodyStatus.ACTIVE, CustodyEventType.ACCEPTED, InventoryAuditAction.ASSIGN, "Resguardo aceptado y activado", request=request, comment=data.comment, mutate=mutate, permission=ACCEPT_PERMISSION)


@transaction.atomic
def reject_custody_assignment(*, custody_id, actor_id, data, request=None):
    identity = _require_permission(actor_id, ACCEPT_PERMISSION)
    custody = _lock(custody_id)
    if custody.assigned_to_id != identity.id and not identity.has_global_bypass:
        raise InventoryAuthorizationError("Sólo el resguardatario puede rechazar este resguardo.")
    reason = _text(data.reason)
    if not reason:
        raise InventoryValidationError("Debe indicar el motivo del rechazo.")
    def mutate(c, a):
        c.rejected_by_id = a.id
        c.rejected_at = timezone.now()
        c.rejection_reason = reason
    return _transition(custody_id, actor_id, {CustodyStatus.PENDING_ACCEPTANCE}, CustodyStatus.REJECTED, CustodyEventType.REJECTED, InventoryAuditAction.REJECT, "Resguardo rechazado", request=request, comment=reason, mutate=mutate, permission=ACCEPT_PERMISSION)


@transaction.atomic
def request_custody_return(*, custody_id, actor_id, request=None):
    identity = _require_permission(actor_id, ACCEPT_PERMISSION)
    custody = _lock(custody_id)
    if custody.assigned_to_id != identity.id and not identity.has_global_bypass:
        raise InventoryAuthorizationError("Sólo el resguardatario puede solicitar la devolución.")
    def mutate(c, a):
        c.return_requested_by_id = a.id
        c.return_requested_at = timezone.now()
    return _transition(custody_id, actor_id, {CustodyStatus.ACTIVE}, CustodyStatus.RETURN_PENDING, CustodyEventType.RETURN_REQUESTED, InventoryAuditAction.RETURN, "Devolución solicitada", request=request, mutate=mutate, permission=ACCEPT_PERMISSION)


@transaction.atomic
def complete_custody_return(*, custody_id, actor_id, data, request=None):
    def mutate(c, a):
        c.returned_by_id = c.assigned_to_id
        c.received_return_by_id = a.id
        c.returned_at = data.returned_at
        c.return_condition = data.physical_condition
        c.return_observations = _text(data.notes)
        c.asset.current_custodian_id = None
        c.asset.operational_status = AssetOperationalStatus.AVAILABLE
        c.asset.physical_condition = data.physical_condition
        c.asset.full_clean()
        c.asset.save()
    return _transition(custody_id, actor_id, {CustodyStatus.RETURN_PENDING}, CustodyStatus.RETURNED, CustodyEventType.RETURNED, InventoryAuditAction.RETURN, "Devolución recibida", request=request, comment=data.notes, mutate=mutate)


@transaction.atomic
def cancel_custody_assignment(*, custody_id, actor_id, data, request=None):
    reason = _text(data.reason)
    if not reason:
        raise InventoryValidationError("Debe indicar el motivo de cancelación.")
    def mutate(c, a):
        c.cancelled_by_id = a.id
        c.cancelled_at = timezone.now()
        c.cancellation_reason = reason
    return _transition(custody_id, actor_id, {CustodyStatus.DRAFT, CustodyStatus.PENDING_AUTHORIZATION, CustodyStatus.REJECTED}, CustodyStatus.CANCELLED, CustodyEventType.CANCELLED, InventoryAuditAction.REJECT, "Resguardo cancelado", request=request, comment=reason, mutate=mutate)


__all__ = [name for name in globals() if name.endswith("custody_assignment") or name in {"deliver_custody_assignment", "request_custody_return", "complete_custody_return"}]

