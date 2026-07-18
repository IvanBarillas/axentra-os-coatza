from django.db.models import Count, Q

from apps.inventory.models import PhysicalAuditItem, PhysicalAuditSession


class PhysicalAuditSelectors:
    @staticmethod
    def sessions(*, q="", status="", department_id=""):
        qs = PhysicalAuditSession.objects.filter(is_deleted=False).select_related(
            "sede", "dependencia", "area", "started_by", "closed_by",
        )
        if q:
            qs = qs.filter(Q(folio__icontains=q) | Q(name__icontains=q))
        if status:
            qs = qs.filter(status=status)
        if department_id:
            qs = qs.filter(dependencia_id=department_id)
        return qs.order_by("-created_at")

    @classmethod
    def session_detail(cls, session_id):
        return cls.sessions().prefetch_related("items").get(pk=session_id)

    @staticmethod
    def items(*, session_id, result="", asset_id="", scanned_by_id=""):
        qs = PhysicalAuditItem.objects.filter(is_deleted=False, session_id=session_id).select_related("session", "asset", "scanned_by")
        if result:
            qs = qs.filter(result=result)
        if asset_id:
            qs = qs.filter(asset_id=asset_id)
        if scanned_by_id:
            qs = qs.filter(scanned_by_id=scanned_by_id)
        return qs.order_by("-scanned_at")

    @staticmethod
    def result_totals(session_id):
        return PhysicalAuditItem.objects.filter(is_deleted=False, session_id=session_id).values("result").annotate(total=Count("id")).order_by("result")
