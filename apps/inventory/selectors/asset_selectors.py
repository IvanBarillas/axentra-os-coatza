# apps/inventory/selectors/asset_selectors.py

"""Consultas autorizadas de activos y solicitudes de alta.

Este módulo aplica seguridad a nivel de datos. El permiso ``can_view_assets``
permite entrar a la pantalla, pero este selector decide cuáles filas puede ver
el usuario: propias, de su dependencia o globales.
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce

from apps.inventory.integrations.core_directory import (
    CoreDirectoryError,
    get_module_role,
    get_user_identity,
    get_user_organizational_context,
)
from apps.inventory.models import (
    Asset,
    AssetCategory,
    AssetIntakeRequest,
    AssetIntakeStatus,
    AssetOperationalStatus,
    AssetPatrimonialStatus,
)


class InventoryDataScope(StrEnum):
    OWN = "OWN"
    DEPARTMENT = "DEPARTMENT"
    GLOBAL = "GLOBAL"


@dataclass(frozen=True, slots=True)
class InventoryScopeContext:
    actor_id: UUID
    role: str
    scope: InventoryDataScope
    department_id: UUID | None


ASSET_RELATED = (
    "source_intake_request",
    "category",
    "expenditure_object",
    "accounting_account",
    "manufacturer",
    "model",
    "supplier",
    "contract",
    "origin_sede",
    "origin_dependencia",
    "origin_area",
    "current_sede",
    "current_dependencia",
    "current_area",
    "current_custodian",
    "registered_by",
)


INTAKE_RELATED = (
    "category",
    "expenditure_object",
    "accounting_account",
    "manufacturer",
    "model",
    "supplier",
    "contract",
    "requested_sede",
    "requested_dependencia",
    "requested_area",
    "proposed_custodian",
    "captured_by",
    "capture_dependencia",
    "submitted_by",
    "department_approved_by",
    "patrimony_validated_by",
)


GLOBAL_ASSET_ROLES = {
    "owner",
    "admin",
    "admin_patrimonio",
    "almacenista",
    "auditor",
}

DEPARTMENT_ASSET_ROLES = {
    "director",
    "reviewer",
}


def _normalize_role(role) -> str:
    return str(role.role if role else "").strip().lower()


def _has_permission(role, permission: str) -> bool:
    return bool(role and role.has_permission(permission))


def _uuid_or_none(value) -> UUID | None:
    if value in (None, ""):
        return None

    try:
        return value if isinstance(value, UUID) else UUID(str(value))
    except (TypeError, ValueError, AttributeError):
        return None


def _valid_choice(value, choices) -> bool:
    return not value or value in {
        choice_value for choice_value, _label in choices
    }


def resolve_asset_scope(actor_id) -> InventoryScopeContext:
    """Resuelve el alcance aplicable al padrón de activos."""

    try:
        actor = get_user_identity(actor_id)
        role = get_module_role(actor.id)
        organization = get_user_organizational_context(
            actor.id,
            require_profile=False,
        )
    except CoreDirectoryError as exc:
        raise PermissionDenied(str(exc)) from exc

    if actor.has_global_bypass:
        return InventoryScopeContext(
            actor_id=actor.id,
            role=_normalize_role(role),
            scope=InventoryDataScope.GLOBAL,
            department_id=organization.department_id,
        )

    if not role or not role.has_permission("can_view_assets"):
        raise PermissionDenied(
            "El usuario no tiene permiso para consultar activos."
        )

    normalized_role = _normalize_role(role)

    if (
        normalized_role in GLOBAL_ASSET_ROLES
        or _has_permission(role, "can_validate_patrimony_intake")
        or _has_permission(role, "can_register_asset")
        or _has_permission(role, "can_view_audit")
    ):
        scope = InventoryDataScope.GLOBAL
    elif (
        normalized_role in DEPARTMENT_ASSET_ROLES
        or _has_permission(role, "can_approve_department_intake")
        or _has_permission(role, "can_authorize_movements")
    ):
        if not organization.department_id:
            raise PermissionDenied(
                "El usuario no tiene una dependencia activa."
            )
        scope = InventoryDataScope.DEPARTMENT
    else:
        scope = InventoryDataScope.OWN

    return InventoryScopeContext(
        actor_id=actor.id,
        role=normalized_role,
        scope=scope,
        department_id=organization.department_id,
    )


def resolve_intake_scope(actor_id) -> InventoryScopeContext:
    """Resuelve el alcance de las solicitudes de alta."""

    try:
        actor = get_user_identity(actor_id)
        role = get_module_role(actor.id)
        organization = get_user_organizational_context(
            actor.id,
            require_profile=False,
        )
    except CoreDirectoryError as exc:
        raise PermissionDenied(str(exc)) from exc

    if actor.has_global_bypass:
        return InventoryScopeContext(
            actor_id=actor.id,
            role=_normalize_role(role),
            scope=InventoryDataScope.GLOBAL,
            department_id=organization.department_id,
        )

    if not role or not role.has_permission("can_view_assets"):
        raise PermissionDenied(
            "El usuario no tiene permiso para consultar solicitudes."
        )

    normalized_role = _normalize_role(role)

    # Captura transversal permite consultar el tablero completo de solicitudes,
    # pero no concede por sí misma acceso global al padrón de activos.
    if (
        normalized_role in {"owner", "admin", "admin_patrimonio", "auditor"}
        or _has_permission(role, "can_create_intake_for_any_department")
        or _has_permission(role, "can_validate_patrimony_intake")
        or _has_permission(role, "can_register_asset")
        or _has_permission(role, "can_view_audit")
    ):
        scope = InventoryDataScope.GLOBAL
    elif _has_permission(role, "can_approve_department_intake"):
        if not organization.department_id:
            raise PermissionDenied(
                "El usuario no tiene una dependencia activa."
            )
        scope = InventoryDataScope.DEPARTMENT
    else:
        scope = InventoryDataScope.OWN

    return InventoryScopeContext(
        actor_id=actor.id,
        role=normalized_role,
        scope=scope,
        department_id=organization.department_id,
    )


class AssetSelectors:
    @staticmethod
    def base_queryset():
        """Query base técnica; no debe usarse directamente desde vistas."""

        return (
            Asset.objects
            .filter(is_deleted=False)
            .select_related(*ASSET_RELATED)
        )

    @classmethod
    def visible_queryset(cls, *, actor_id):
        context = resolve_asset_scope(actor_id)
        queryset = cls.base_queryset()

        if context.scope == InventoryDataScope.GLOBAL:
            return queryset

        if context.scope == InventoryDataScope.DEPARTMENT:
            return queryset.filter(
                current_dependencia_id=context.department_id,
            )

        return queryset.filter(
            current_custodian_id=context.actor_id,
        )

    @classmethod
    def listar_activos(
        cls,
        *,
        actor_id,
        q="",
        status="",
        patrimonial_status="",
        operational_status="",
        category_id="",
        department_id="",
    ):
        queryset = cls.visible_queryset(actor_id=actor_id)
        patrimonial_status = patrimonial_status or status

        normalized_query = str(q or "").strip()
        if normalized_query:
            queryset = queryset.filter(
                Q(
                    official_inventory_number__icontains=(
                        normalized_query
                    )
                )
                | Q(
                    internal_inventory_number__icontains=(
                        normalized_query
                    )
                )
                | Q(
                    legacy_inventory_number__icontains=(
                        normalized_query
                    )
                )
                | Q(name__icontains=normalized_query)
                | Q(serial_number__icontains=normalized_query)
            )

        if not _valid_choice(
            patrimonial_status,
            AssetPatrimonialStatus.choices,
        ):
            return queryset.none()

        if not _valid_choice(
            operational_status,
            AssetOperationalStatus.choices,
        ):
            return queryset.none()

        if patrimonial_status:
            queryset = queryset.filter(
                patrimonial_status=patrimonial_status,
            )

        if operational_status:
            queryset = queryset.filter(
                operational_status=operational_status,
            )

        if category_id:
            resolved_category_id = _uuid_or_none(category_id)
            if not resolved_category_id:
                return queryset.none()
            queryset = queryset.filter(category_id=resolved_category_id)

        # Este filtro sólo reduce el queryset previamente autorizado.
        if department_id:
            resolved_department_id = _uuid_or_none(department_id)
            if not resolved_department_id:
                return queryset.none()
            queryset = queryset.filter(
                current_dependencia_id=resolved_department_id,
            )

        return queryset.order_by(
            "current_dependencia__nombre",
            "official_inventory_number",
        )

    @classmethod
    def obtener(cls, *, actor_id, asset_id):
        return cls.visible_queryset(actor_id=actor_id).get(pk=asset_id)

    @classmethod
    def obtener_expediente(cls, *, actor_id, asset_id):
        return (
            cls.visible_queryset(actor_id=actor_id)
            .prefetch_related(
                "movements",
                "loans",
                "custody_assignments",
                "depreciation_records",
                "disposal_requests",
                "physical_audit_items",
                "audit_logs",
            )
            .get(pk=asset_id)
        )

    @staticmethod
    def categories():
        return (
            AssetCategory.objects
            .filter(is_active=True, is_deleted=False)
            .order_by("nature", "code", "name")
        )

    @staticmethod
    def status_choices():
        return AssetPatrimonialStatus.choices

    @staticmethod
    def operational_status_choices():
        return AssetOperationalStatus.choices

    @classmethod
    def dashboard_metrics(cls, *, actor_id):
        assets = cls.visible_queryset(actor_id=actor_id)
        intakes = IntakeSelectors.visible_queryset(actor_id=actor_id)

        totals = assets.aggregate(
            total=Count("id"),
            acquisition_value=Coalesce(
                Sum("acquisition_cost"),
                Decimal("0.00"),
            ),
        )

        pending_statuses = (
            AssetIntakeStatus.SUBMITTED,
            AssetIntakeStatus.DEPARTMENT_APPROVED,
            AssetIntakeStatus.UNDER_PATRIMONY_REVIEW,
            AssetIntakeStatus.OBSERVED,
            AssetIntakeStatus.APPROVED,
        )

        return {
            **totals,
            "active": assets.filter(
                patrimonial_status=AssetPatrimonialStatus.ACTIVE,
            ).count(),
            "pending": intakes.filter(
                status__in=pending_statuses,
            ).count(),
            "without_custodian": assets.filter(
                current_custodian__isnull=True,
            ).count(),
            "scope": resolve_asset_scope(actor_id).scope.value,
        }


class IntakeSelectors:
    @staticmethod
    def base_queryset():
        """Query base técnica; no debe usarse directamente desde vistas."""

        return (
            AssetIntakeRequest.objects
            .filter(is_deleted=False)
            .select_related(*INTAKE_RELATED)
        )

    @classmethod
    def visible_queryset(cls, *, actor_id):
        context = resolve_intake_scope(actor_id)
        queryset = cls.base_queryset()

        if context.scope == InventoryDataScope.GLOBAL:
            return queryset

        if context.scope == InventoryDataScope.DEPARTMENT:
            return queryset.filter(
                requested_dependencia_id=context.department_id,
            )

        return queryset.filter(
            Q(captured_by_id=context.actor_id)
            | Q(submitted_by_id=context.actor_id)
        )

    @classmethod
    def listar(
        cls,
        *,
        actor_id,
        q="",
        status="",
        department_id="",
        capture_department_id="",
        requested_by_id="",
        captured_by_id="",
        submitted_by_id="",
        cross_department=None,
        scope="",
    ):
        queryset = cls.visible_queryset(actor_id=actor_id)
        context = resolve_intake_scope(actor_id)

        requested_scope = str(scope or "").strip().upper()
        if requested_scope:
            allowed_scopes = {item.value for item in InventoryDataScope}
            if requested_scope not in allowed_scopes:
                return queryset.none()

            # El usuario puede pedir una vista más limitada, nunca una mayor.
            if requested_scope == InventoryDataScope.OWN:
                queryset = queryset.filter(
                    Q(captured_by_id=context.actor_id)
                    | Q(submitted_by_id=context.actor_id)
                )
            elif requested_scope == InventoryDataScope.DEPARTMENT:
                if not context.department_id:
                    return queryset.none()
                queryset = queryset.filter(
                    requested_dependencia_id=context.department_id,
                )
            elif context.scope != InventoryDataScope.GLOBAL:
                raise PermissionDenied(
                    "No tiene alcance global sobre las solicitudes."
                )

        normalized_query = str(q or "").strip()
        if normalized_query:
            queryset = queryset.filter(
                Q(request_number__icontains=normalized_query)
                | Q(name__icontains=normalized_query)
                | Q(serial_number__icontains=normalized_query)
                | Q(
                    requested_dependencia__nombre__icontains=(
                        normalized_query
                    )
                )
                | Q(
                    capture_dependencia_name_snapshot__icontains=(
                        normalized_query
                    )
                )
                | Q(
                    captured_by_name_snapshot__icontains=normalized_query
                )
            )

        if not _valid_choice(status, AssetIntakeStatus.choices):
            return queryset.none()

        if status:
            queryset = queryset.filter(status=status)

        if department_id:
            resolved_department_id = _uuid_or_none(department_id)
            if not resolved_department_id:
                return queryset.none()
            queryset = queryset.filter(
                requested_dependencia_id=resolved_department_id,
            )

        if capture_department_id:
            resolved_capture_department_id = _uuid_or_none(
                capture_department_id
            )
            if not resolved_capture_department_id:
                return queryset.none()
            queryset = queryset.filter(
                capture_dependencia_id=resolved_capture_department_id,
            )

        if cross_department not in (None, ""):
            normalized_cross_department = str(
                cross_department
            ).strip().lower()
            if normalized_cross_department in {"1", "true", "yes", "on"}:
                queryset = queryset.filter(
                    is_cross_department_capture=True,
                )
            elif normalized_cross_department in {
                "0",
                "false",
                "no",
                "off",
            }:
                queryset = queryset.filter(
                    is_cross_department_capture=False,
                )
            else:
                return queryset.none()

        if requested_by_id:
            resolved_user_id = _uuid_or_none(requested_by_id)
            if not resolved_user_id:
                return queryset.none()
            # Alias de compatibilidad: históricamente requested_by_id se usó
            # tanto para quien capturó como para quien envió.
            queryset = queryset.filter(
                Q(captured_by_id=resolved_user_id)
                | Q(submitted_by_id=resolved_user_id)
            )

        if captured_by_id:
            resolved_captured_by_id = _uuid_or_none(captured_by_id)
            if not resolved_captured_by_id:
                return queryset.none()
            queryset = queryset.filter(
                captured_by_id=resolved_captured_by_id,
            )

        if submitted_by_id:
            resolved_submitted_by_id = _uuid_or_none(submitted_by_id)
            if not resolved_submitted_by_id:
                return queryset.none()
            queryset = queryset.filter(
                submitted_by_id=resolved_submitted_by_id,
            )

        return queryset.order_by("-created_at")

    @classmethod
    def visible_for_user(cls, *, actor_id, **filters):
        return cls.listar(actor_id=actor_id, **filters)

    @classmethod
    def obtener(cls, *, actor_id, request_id):
        return (
            cls.visible_queryset(actor_id=actor_id)
            .prefetch_related("decisions")
            .get(pk=request_id)
        )

    @classmethod
    def pendientes_departamento(cls, *, actor_id):
        context = resolve_intake_scope(actor_id)
        if not context.department_id:
            return cls.base_queryset().none()

        return (
            cls.visible_queryset(actor_id=actor_id)
            .filter(
                status=AssetIntakeStatus.SUBMITTED,
                requested_dependencia_id=context.department_id,
            )
            .order_by("created_at")
        )

    @classmethod
    def pendientes_patrimonio(cls, *, actor_id):
        context = resolve_intake_scope(actor_id)
        if context.scope != InventoryDataScope.GLOBAL:
            raise PermissionDenied(
                "No tiene alcance para consultar la bandeja patrimonial."
            )

        statuses = (
            AssetIntakeStatus.DEPARTMENT_APPROVED,
            AssetIntakeStatus.UNDER_PATRIMONY_REVIEW,
            AssetIntakeStatus.OBSERVED,
        )
        return (
            cls.visible_queryset(actor_id=actor_id)
            .filter(status__in=statuses)
            .order_by("created_at")
        )


__all__ = [
    "AssetSelectors",
    "IntakeSelectors",
    "InventoryDataScope",
    "InventoryScopeContext",
    "resolve_asset_scope",
    "resolve_intake_scope",
]

