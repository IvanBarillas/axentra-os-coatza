"""Consultas de activos y solicitudes con alcance organizacional explícito."""

from decimal import Decimal

from django.db.models import Count, Q, QuerySet, Sum
from django.db.models.functions import Coalesce

from apps.inventory.models import (
    Asset,
    AssetCategory,
    AssetIntakeRequest,
    AssetIntakeStatus,
    AssetOperationalStatus,
    AssetPatrimonialStatus,
)


class InventoryScope:
    GLOBAL = "GLOBAL"
    DEPARTMENT = "DEPARTMENT"
    OWN = "OWN"
    VALUES = {GLOBAL, DEPARTMENT, OWN}

    @classmethod
    def normalize(cls, value):
        normalized = str(value or "").strip().upper()
        if normalized not in cls.VALUES:
            raise ValueError("El alcance de Inventory no es válido.")
        return normalized


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


class AssetSelectors:
    @staticmethod
    def base_queryset() -> QuerySet:
        return (
            Asset.objects
            .filter(is_deleted=False)
            .select_related(*ASSET_RELATED)
        )

    @classmethod
    def visible_queryset(
        cls,
        *,
        scope=InventoryScope.GLOBAL,
        actor_id=None,
        department_id=None,
    ) -> QuerySet:
        normalized_scope = InventoryScope.normalize(scope)
        queryset = cls.base_queryset()

        if normalized_scope == InventoryScope.GLOBAL:
            return queryset
        if normalized_scope == InventoryScope.DEPARTMENT:
            if not department_id:
                return queryset.none()
            return queryset.filter(current_dependencia_id=department_id)
        if not actor_id:
            return queryset.none()
        return queryset.filter(current_custodian_id=actor_id)

    @classmethod
    def listar_activos(
        cls,
        *,
        q="",
        status="",
        patrimonial_status="",
        operational_status="",
        category_id="",
        department_id="",
        scope=InventoryScope.GLOBAL,
        actor_id=None,
        scope_department_id=None,
    ) -> QuerySet:
        queryset = cls.visible_queryset(
            scope=scope,
            actor_id=actor_id,
            department_id=scope_department_id,
        )
        patrimonial_status = patrimonial_status or status
        normalized_query = str(q or "").strip()

        if normalized_query:
            queryset = queryset.filter(
                Q(official_inventory_number__icontains=normalized_query)
                | Q(internal_inventory_number__icontains=normalized_query)
                | Q(legacy_inventory_number__icontains=normalized_query)
                | Q(name__icontains=normalized_query)
                | Q(serial_number__icontains=normalized_query)
            )
        if patrimonial_status:
            queryset = queryset.filter(
                patrimonial_status=patrimonial_status
            )
        if operational_status:
            queryset = queryset.filter(
                operational_status=operational_status
            )
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        if department_id:
            queryset = queryset.filter(
                current_dependencia_id=department_id
            )
        return queryset.order_by("-created_at")

    @classmethod
    def obtener(
        cls,
        asset_id,
        *,
        scope=InventoryScope.GLOBAL,
        actor_id=None,
        department_id=None,
    ):
        return cls.visible_queryset(
            scope=scope,
            actor_id=actor_id,
            department_id=department_id,
        ).get(pk=asset_id)

    @classmethod
    def obtener_expediente(
        cls,
        asset_id,
        *,
        scope=InventoryScope.GLOBAL,
        actor_id=None,
        department_id=None,
    ):
        return (
            cls.visible_queryset(
                scope=scope,
                actor_id=actor_id,
                department_id=department_id,
            )
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
    def categories() -> QuerySet:
        return AssetCategory.objects.filter(
            is_active=True,
            is_deleted=False,
        ).order_by("name")

    @staticmethod
    def status_choices():
        return AssetPatrimonialStatus.choices

    @staticmethod
    def operational_status_choices():
        return AssetOperationalStatus.choices

    @classmethod
    def dashboard_metrics(
        cls,
        *,
        scope=InventoryScope.GLOBAL,
        actor_id=None,
        department_id=None,
    ):
        assets = cls.visible_queryset(
            scope=scope,
            actor_id=actor_id,
            department_id=department_id,
        )
        intakes = IntakeSelectors.visible_queryset(
            scope=scope,
            actor_id=actor_id,
            department_id=department_id,
        )
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
        }


class IntakeSelectors:
    @staticmethod
    def base_queryset() -> QuerySet:
        return (
            AssetIntakeRequest.objects
            .filter(is_deleted=False)
            .select_related(
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
                "submitted_by",
            )
        )

    @classmethod
    def visible_queryset(
        cls,
        *,
        scope=InventoryScope.GLOBAL,
        actor_id=None,
        department_id=None,
    ) -> QuerySet:
        normalized_scope = InventoryScope.normalize(scope)
        queryset = cls.base_queryset()

        if normalized_scope == InventoryScope.GLOBAL:
            return queryset
        if normalized_scope == InventoryScope.DEPARTMENT:
            if not department_id:
                return queryset.none()
            return queryset.filter(requested_dependencia_id=department_id)
        if not actor_id:
            return queryset.none()
        return queryset.filter(submitted_by_id=actor_id)

    @classmethod
    def listar(
        cls,
        *,
        q="",
        status="",
        department_id="",
        requested_by_id="",
        scope=InventoryScope.GLOBAL,
        actor_id=None,
        scope_department_id=None,
    ) -> QuerySet:
        queryset = cls.visible_queryset(
            scope=scope,
            actor_id=actor_id,
            department_id=scope_department_id,
        )
        normalized_query = str(q or "").strip()
        if normalized_query:
            queryset = queryset.filter(
                Q(request_number__icontains=normalized_query)
                | Q(name__icontains=normalized_query)
                | Q(serial_number__icontains=normalized_query)
            )
        if status:
            queryset = queryset.filter(status=status)
        if department_id:
            queryset = queryset.filter(
                requested_dependencia_id=department_id
            )
        if requested_by_id:
            queryset = queryset.filter(submitted_by_id=requested_by_id)
        return queryset.order_by("-created_at")

    @classmethod
    def obtener(
        cls,
        request_id,
        *,
        scope=InventoryScope.GLOBAL,
        actor_id=None,
        department_id=None,
    ):
        return (
            cls.visible_queryset(
                scope=scope,
                actor_id=actor_id,
                department_id=department_id,
            )
            .prefetch_related("decisions")
            .get(pk=request_id)
        )

    @classmethod
    def pendientes_departamento(cls, department_id) -> QuerySet:
        return cls.listar(
            status=AssetIntakeStatus.SUBMITTED,
            scope=InventoryScope.DEPARTMENT,
            scope_department_id=department_id,
        )

    @classmethod
    def pendientes_patrimonio(cls) -> QuerySet:
        return cls.visible_queryset(scope=InventoryScope.GLOBAL).filter(
            status__in=(
                AssetIntakeStatus.DEPARTMENT_APPROVED,
                AssetIntakeStatus.UNDER_PATRIMONY_REVIEW,
                AssetIntakeStatus.OBSERVED,
            )
        ).order_by("-created_at")


__all__ = ["AssetSelectors", "IntakeSelectors", "InventoryScope"]
