from django.db.models import Q

from apps.inventory.models import (
    AccountingExportBatch, AccountingReconciliation, DepreciationPolicy,
    DepreciationRecord, DepreciationRun,
)


class FinancialSelectors:
    @staticmethod
    def depreciation_policies():
        return DepreciationPolicy.objects.filter(is_active=True, is_deleted=False).select_related("accounting_account").order_by("name")

    @staticmethod
    def depreciation_runs(*, status="", period_year=None):
        qs = DepreciationRun.objects.filter(is_deleted=False)
        if status:
            qs = qs.filter(status=status)
        if period_year:
            qs = qs.filter(period_year=period_year)
        return qs.order_by("-created_at")

    @staticmethod
    def depreciation_records(*, asset_id=None, period_year=None):
        qs = DepreciationRecord.objects.filter(is_deleted=False).select_related("asset", "policy", "calculated_by")
        if asset_id:
            qs = qs.filter(asset_id=asset_id)
        if period_year:
            qs = qs.filter(period_year=period_year)
        return qs.order_by("-period_year", "-period_month")

    @staticmethod
    def export_batches(*, q="", export_type="", status=""):
        qs = AccountingExportBatch.objects.filter(is_deleted=False).select_related("requested_by", "completed_by")
        if q:
            qs = qs.filter(Q(folio__icontains=q) | Q(destination_system__icontains=q) | Q(generated_filename__icontains=q))
        if export_type:
            qs = qs.filter(export_type=export_type)
        if status:
            qs = qs.filter(status=status)
        return qs.order_by("-created_at")

    @staticmethod
    def reconciliations(*, status="", date_from=None, date_to=None):
        qs = AccountingReconciliation.objects.filter(is_deleted=False).select_related("created_by", "processed_by", "reviewed_by")
        if status:
            qs = qs.filter(status=status)
        if date_from:
            qs = qs.filter(period_end__gte=date_from)
        if date_to:
            qs = qs.filter(period_start__lte=date_to)
        return qs.order_by("-created_at")

    @classmethod
    def reconciliation_detail(cls, reconciliation_id):
        return cls.reconciliations().prefetch_related("items").get(pk=reconciliation_id)
