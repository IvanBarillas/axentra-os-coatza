from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce

from apps.inventory.models import (
    Asset, AssetCategory, AssetIntakeRequest, AssetIntakeStatus,
    AssetOperationalStatus, AssetPatrimonialStatus,
)


ASSET_RELATED = (
    "source_intake_request", "category", "expenditure_object",
    "accounting_account", "manufacturer", "model", "supplier", "contract",
    "origin_sede", "origin_dependencia", "origin_area", "current_sede",
    "current_dependencia", "current_area", "current_custodian", "registered_by",
)


class AssetSelectors:
    @staticmethod
    def base_queryset():
        return Asset.objects.filter(is_deleted=False).select_related(*ASSET_RELATED)

    @classmethod
    def listar_activos(cls, *, q="", status="", patrimonial_status="", operational_status="", category_id="", department_id=""):
        qs = cls.base_queryset()
        patrimonial_status = patrimonial_status or status
        if q:
            qs = qs.filter(Q(official_inventory_number__icontains=q) | Q(internal_inventory_number__icontains=q) | Q(legacy_inventory_number__icontains=q) | Q(name__icontains=q) | Q(serial_number__icontains=q))
        if patrimonial_status:
            qs = qs.filter(patrimonial_status=patrimonial_status)
        if operational_status:
            qs = qs.filter(operational_status=operational_status)
        if category_id:
            qs = qs.filter(category_id=category_id)
        if department_id:
            qs = qs.filter(current_dependencia_id=department_id)
        return qs.order_by("-created_at")

    @classmethod
    def obtener(cls, asset_id):
        return cls.base_queryset().get(pk=asset_id)

    @classmethod
    def obtener_expediente(cls, asset_id):
        return cls.base_queryset().prefetch_related(
            "movements", "loans", "custody_assignments", "depreciation_records",
            "disposal_requests", "physical_audit_items", "audit_logs",
        ).get(pk=asset_id)

    @staticmethod
    def categories():
        return AssetCategory.objects.filter(is_active=True, is_deleted=False).order_by("name")

    @staticmethod
    def status_choices():
        return AssetPatrimonialStatus.choices

    @staticmethod
    def operational_status_choices():
        return AssetOperationalStatus.choices

    @staticmethod
    def dashboard_metrics():
        qs = Asset.objects.filter(is_deleted=False)
        totals = qs.aggregate(
            total=Count("id"),
            acquisition_value=Coalesce(Sum("acquisition_cost"), Decimal("0.00")),
        )
        return {
            **totals,
            "active": qs.filter(patrimonial_status=AssetPatrimonialStatus.ACTIVE).count(),
            "pending": AssetIntakeRequest.objects.filter(is_deleted=False, status__in=[AssetIntakeStatus.SUBMITTED, AssetIntakeStatus.DEPARTMENT_APPROVED, AssetIntakeStatus.UNDER_PATRIMONY_REVIEW, AssetIntakeStatus.OBSERVED, AssetIntakeStatus.APPROVED]).count(),
            "without_custodian": qs.filter(current_custodian__isnull=True).count(),
        }


class IntakeSelectors:
    @staticmethod
    def base_queryset():
        return AssetIntakeRequest.objects.filter(is_deleted=False).select_related(
            "category", "expenditure_object", "accounting_account", "manufacturer",
            "model", "supplier", "contract", "requested_sede", "requested_dependencia",
            "requested_area", "proposed_custodian", "submitted_by",
        )

    @classmethod
    def listar(cls, *, q="", status="", department_id="", requested_by_id=""):
        qs = cls.base_queryset()
        if q:
            qs = qs.filter(Q(request_number__icontains=q) | Q(name__icontains=q) | Q(serial_number__icontains=q))
        if status:
            qs = qs.filter(status=status)
        if department_id:
            qs = qs.filter(requested_dependencia_id=department_id)
        if requested_by_id:
            qs = qs.filter(submitted_by_id=requested_by_id)
        return qs.order_by("-created_at")

    @classmethod
    def obtener(cls, request_id):
        return cls.base_queryset().prefetch_related("decisions").get(pk=request_id)

    @classmethod
    def pendientes_departamento(cls, department_id):
        return cls.listar(status=AssetIntakeStatus.SUBMITTED, department_id=department_id)

    @classmethod
    def pendientes_patrimonio(cls):
        return cls.base_queryset().filter(status__in=[AssetIntakeStatus.DEPARTMENT_APPROVED, AssetIntakeStatus.UNDER_PATRIMONY_REVIEW, AssetIntakeStatus.OBSERVED]).order_by("-created_at")
