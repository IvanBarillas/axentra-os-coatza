# apps/inventory/services/audit_service.py

"""Registro append-only de eventos auditables de Inventory."""

from dataclasses import asdict, dataclass, is_dataclass
from datetime import date, datetime, time, timezone as datetime_timezone
from decimal import Decimal
from enum import Enum
from ipaddress import ip_address
from typing import Any, Mapping
from uuid import UUID, uuid4

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Model
from django.utils import timezone

from apps.inventory.integrations.core_directory import (
    CoreDirectoryError,
    get_user_identity,
)
from apps.inventory.models import (
    InventoryAuditAction,
    InventoryAuditLevel,
    InventoryAuditLog,
)
from apps.inventory.services.exceptions import (
    InventoryBypassReasonRequired,
    InventoryConfigurationError,
    InventoryValidationError,
)


@dataclass(frozen=True, slots=True)
class AuditRequestContext:
    request_id: UUID
    ip_address: str | None = None
    user_agent: str = ""


def _as_uuid_or_none(value, *, field_name: str) -> UUID | None:
    if value is None or value == "":
        return None

    if isinstance(value, UUID):
        return value

    if isinstance(value, Model):
        value = value.pk

    try:
        return UUID(str(value))
    except (TypeError, ValueError, AttributeError) as exc:
        raise InventoryValidationError(
            f"{field_name} debe ser un UUID válido.",
            details={"field": field_name},
        ) from exc


def _normalize_ip(value) -> str | None:
    if not value:
        return None

    candidate = str(value).strip()

    try:
        return str(ip_address(candidate))
    except ValueError:
        return None


def build_audit_request_context(
    request=None,
    *,
    request_id=None,
) -> AuditRequestContext:
    """
    Construye metadatos auditables desde un HttpRequest sin confiar en
    X-Forwarded-For. La configuración del proxy debe resolver REMOTE_ADDR.
    """

    resolved_request_id = _as_uuid_or_none(
        request_id,
        field_name="request_id",
    )

    if request is not None and resolved_request_id is None:
        existing_request_id = getattr(
            request,
            "axentra_inventory_request_id",
            None,
        )

        if existing_request_id:
            resolved_request_id = _as_uuid_or_none(
                existing_request_id,
                field_name="request_id",
            )

    if resolved_request_id is None:
        resolved_request_id = uuid4()

    if request is not None:
        request.axentra_inventory_request_id = resolved_request_id

    remote_address = None
    user_agent = ""

    if request is not None:
        remote_address = _normalize_ip(
            request.META.get("REMOTE_ADDR")
        )
        user_agent = str(
            request.META.get("HTTP_USER_AGENT", "")
        ).strip()[:2000]

    return AuditRequestContext(
        request_id=resolved_request_id,
        ip_address=remote_address,
        user_agent=user_agent,
    )


def to_json_safe(value: Any) -> Any:
    """Convierte snapshots a valores aceptados por JSONField."""

    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, UUID):
        return str(value)

    if isinstance(value, Decimal):
        return str(value)

    if isinstance(value, datetime):
        if timezone.is_aware(value):
            value = value.astimezone(datetime_timezone.utc)
        return value.isoformat()

    if isinstance(value, (date, time)):
        return value.isoformat()

    if isinstance(value, Enum):
        return to_json_safe(value.value)

    if isinstance(value, Model):
        return {
            "model": value._meta.label,
            "id": str(value.pk),
            "display": str(value),
        }

    if is_dataclass(value):
        return to_json_safe(asdict(value))

    if isinstance(value, Mapping):
        return {
            str(key): to_json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple, set, frozenset)):
        return [to_json_safe(item) for item in value]

    return str(value)


def model_snapshot(
    instance: Model | None,
    *,
    fields: tuple[str, ...] | list[str] | None = None,
) -> dict[str, Any]:
    """Obtiene un snapshot explícito de campos concretos de un modelo."""

    if instance is None:
        return {}

    if fields is None:
        selected_fields = [
            field.name
            for field in instance._meta.concrete_fields
        ]
    else:
        selected_fields = list(fields)

    snapshot = {
        "_model": instance._meta.label,
        "_id": str(instance.pk) if instance.pk else None,
    }

    for field_name in selected_fields:
        try:
            field = instance._meta.get_field(field_name)
        except Exception as exc:
            raise InventoryConfigurationError(
                "Se solicitó un campo inexistente para el snapshot.",
                details={
                    "model": instance._meta.label,
                    "field": field_name,
                },
            ) from exc

        attribute_name = (
            field.attname
            if getattr(field, "many_to_one", False)
            or getattr(field, "one_to_one", False)
            else field.name
        )
        snapshot[field_name] = to_json_safe(
            getattr(instance, attribute_name)
        )

    return snapshot


def _normalize_action(action) -> str:
    normalized = str(action).strip().upper()
    valid_actions = {
        value for value, _label in InventoryAuditAction.choices
    }

    if normalized not in valid_actions:
        raise InventoryValidationError(
            "La acción de auditoría no es válida.",
            details={"action": normalized},
        )

    return normalized


def _normalize_level(level) -> str:
    normalized = str(level).strip().upper()
    valid_levels = {
        value for value, _label in InventoryAuditLevel.choices
    }

    if normalized not in valid_levels:
        raise InventoryValidationError(
            "El nivel de auditoría no es válido.",
            details={"level": normalized},
        )

    return normalized


def _resolve_target(target):
    if target is None:
        return "", None

    if not isinstance(target, Model):
        raise InventoryValidationError(
            "target debe ser una instancia de modelo Django."
        )

    if not target.pk:
        raise InventoryValidationError(
            "El objetivo debe estar guardado antes de auditarse."
        )

    return target._meta.label, _as_uuid_or_none(
        target.pk,
        field_name="target_id",
    )


def log_inventory_event(
    *,
    action,
    summary: str,
    actor_id=None,
    level=InventoryAuditLevel.INFO,
    asset_id=None,
    intake_request_id=None,
    target=None,
    target_model: str = "",
    target_id=None,
    reason: str = "",
    old_value: Mapping[str, Any] | None = None,
    new_value: Mapping[str, Any] | None = None,
    payload: Mapping[str, Any] | None = None,
    request_context: AuditRequestContext | None = None,
    request=None,
    request_id=None,
    bypass_used: bool = False,
    bypass_reason: str = "",
    occurred_at=None,
) -> InventoryAuditLog:
    """Crea un evento inmutable en la bitácora de Inventory."""

    normalized_summary = str(summary or "").strip()
    if not normalized_summary:
        raise InventoryValidationError(
            "El resumen del evento es obligatorio."
        )

    normalized_bypass_reason = str(bypass_reason or "").strip()
    if bypass_used and not normalized_bypass_reason:
        raise InventoryBypassReasonRequired(
            "Toda operación con bypass requiere una justificación."
        )

    normalized_action = _normalize_action(action)
    normalized_level = _normalize_level(level)

    actor_identity = None
    resolved_actor_id = _as_uuid_or_none(
        actor_id,
        field_name="actor_id",
    )

    if resolved_actor_id:
        try:
            actor_identity = get_user_identity(
                resolved_actor_id,
                include_unavailable=True,
            )
        except CoreDirectoryError as exc:
            raise InventoryValidationError(str(exc)) from exc

    resolved_target_model, resolved_target_id = _resolve_target(
        target
    )

    if target_model:
        resolved_target_model = str(target_model).strip()

    if target_id is not None:
        resolved_target_id = _as_uuid_or_none(
            target_id,
            field_name="target_id",
        )

    if resolved_target_id and not resolved_target_model:
        raise InventoryValidationError(
            "Debe indicar target_model para el UUID objetivo."
        )

    context = request_context or build_audit_request_context(
        request,
        request_id=request_id,
    )

    event = InventoryAuditLog(
        action_type=normalized_action,
        level=normalized_level,
        actor_id=resolved_actor_id,
        actor_name_snapshot=(
            actor_identity.display_name if actor_identity else ""
        ),
        actor_email_snapshot=(
            actor_identity.normalized_email if actor_identity else ""
        ),
        asset_id=_as_uuid_or_none(
            asset_id,
            field_name="asset_id",
        ),
        intake_request_id=_as_uuid_or_none(
            intake_request_id,
            field_name="intake_request_id",
        ),
        target_model=resolved_target_model,
        target_id=resolved_target_id,
        summary=normalized_summary[:255],
        reason=str(reason or "").strip(),
        old_value=to_json_safe(old_value or {}),
        new_value=to_json_safe(new_value or {}),
        payload=to_json_safe(payload or {}),
        request_id=context.request_id,
        bypass_used=bool(bypass_used),
        bypass_reason=normalized_bypass_reason,
        ip_address=context.ip_address,
        user_agent=context.user_agent,
        occurred_at=occurred_at or timezone.now(),
    )

    try:
        event.full_clean()
    except DjangoValidationError as exc:
        raise InventoryValidationError(
            "El evento de auditoría no superó la validación.",
            details={
                "errors": getattr(
                    exc,
                    "message_dict",
                    {"__all__": exc.messages},
                )
            },
        ) from exc

    event.save(force_insert=True)
    return event


def log_model_change(
    *,
    action,
    summary: str,
    target: Model,
    actor_id=None,
    before: Mapping[str, Any] | Model | None = None,
    after: Mapping[str, Any] | Model | None = None,
    snapshot_fields: tuple[str, ...] | list[str] | None = None,
    **kwargs,
) -> InventoryAuditLog:
    old_value = (
        model_snapshot(before, fields=snapshot_fields)
        if isinstance(before, Model)
        else dict(before or {})
    )
    new_value = (
        model_snapshot(after, fields=snapshot_fields)
        if isinstance(after, Model)
        else dict(after or {})
    )

    return log_inventory_event(
        action=action,
        summary=summary,
        actor_id=actor_id,
        target=target,
        old_value=old_value,
        new_value=new_value,
        **kwargs,
    )


def log_bypass_event(
    *,
    summary: str,
    actor_id,
    bypass_reason: str,
    target=None,
    **kwargs,
) -> InventoryAuditLog:
    return log_inventory_event(
        action=InventoryAuditAction.BYPASS,
        level=InventoryAuditLevel.CRITICAL,
        summary=summary,
        actor_id=actor_id,
        target=target,
        bypass_used=True,
        bypass_reason=bypass_reason,
        **kwargs,
    )


__all__ = [
    "AuditRequestContext",
    "build_audit_request_context",
    "log_bypass_event",
    "log_inventory_event",
    "log_model_change",
    "model_snapshot",
    "to_json_safe",
]