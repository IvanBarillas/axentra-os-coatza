from django.db.models import Q
from django.utils import timezone

from apps.inventory.models import AssetLoan, AssetLoanStatus, DisposalRequest, InventoryMovement


class MovementSelectors:
    @staticmethod
    def base_queryset():
        return InventoryMovement.objects.filter(is_deleted=False).select_related(
            "asset", "performed_by", "from_dependencia", "from_area", "from_sede",
            "from_user", "to_dependencia", "to_area", "to_sede", "to_user",
        )

    @classmethod
    def listar(cls, *, q="", asset_id="", movement_type="", date_from=None, date_to=None):
        qs = cls.base_queryset()
        if q:
            qs = qs.filter(Q(asset__official_inventory_number__icontains=q) | Q(asset__internal_inventory_number__icontains=q) | Q(asset__name__icontains=q) | Q(reason__icontains=q))
        if asset_id:
            qs = qs.filter(asset_id=asset_id)
        if movement_type:
            qs = qs.filter(movement_type=movement_type)
        if date_from:
            qs = qs.filter(occurred_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(occurred_at__date__lte=date_to)
        return qs.order_by("-occurred_at")

    @classmethod
    def obtener(cls, movement_id):
        return cls.base_queryset().get(pk=movement_id)


class LoanSelectors:
    @staticmethod
    def base_queryset():
        return AssetLoan.objects.filter(is_deleted=False).select_related("asset", "borrower", "requested_by")

    @classmethod
    def listar(cls, *, q="", status="", asset_id="", borrower_id="", overdue=False):
        qs = cls.base_queryset()
        if q:
            qs = qs.filter(Q(folio__icontains=q) | Q(asset__official_inventory_number__icontains=q) | Q(asset__name__icontains=q))
        if status:
            qs = qs.filter(status=status)
        if asset_id:
            qs = qs.filter(asset_id=asset_id)
        if borrower_id:
            qs = qs.filter(borrower_id=borrower_id)
        if overdue:
            qs = qs.filter(status=AssetLoanStatus.ACTIVE, due_at__lt=timezone.now())
        return qs.order_by("-requested_at")

    @classmethod
    def obtener(cls, loan_id):
        return cls.base_queryset().get(pk=loan_id)


class DisposalSelectors:
    @staticmethod
    def base_queryset():
        return DisposalRequest.objects.filter(is_deleted=False).select_related("asset", "requested_by")

    @classmethod
    def listar(cls, *, q="", status="", asset_id="", reason=""):
        qs = cls.base_queryset()
        if q:
            qs = qs.filter(Q(folio__icontains=q) | Q(asset__official_inventory_number__icontains=q) | Q(asset__name__icontains=q))
        if status:
            qs = qs.filter(status=status)
        if asset_id:
            qs = qs.filter(asset_id=asset_id)
        if reason:
            qs = qs.filter(reason=reason)
        return qs.order_by("-created_at")

    @classmethod
    def obtener(cls, disposal_id):
        return cls.base_queryset().prefetch_related("approvals").get(pk=disposal_id)
