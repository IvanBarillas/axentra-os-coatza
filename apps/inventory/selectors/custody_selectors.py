from django.db.models import Q

from apps.inventory.models import CustodyAssignment, CustodyStatus


class CustodySelectors:
    @staticmethod
    def base_queryset():
        return CustodyAssignment.objects.filter(is_deleted=False).select_related(
            "asset", "assigned_to", "assigned_by", "dependencia", "area", "sede",
        )

    @classmethod
    def listar(cls, *, q="", status="", asset_id="", assigned_to_id="", department_id=""):
        qs = cls.base_queryset()
        if q:
            qs = qs.filter(Q(folio__icontains=q) | Q(asset__official_inventory_number__icontains=q) | Q(asset__name__icontains=q))
        if status:
            qs = qs.filter(status=status)
        if asset_id:
            qs = qs.filter(asset_id=asset_id)
        if assigned_to_id:
            qs = qs.filter(assigned_to_id=assigned_to_id)
        if department_id:
            qs = qs.filter(dependencia_id=department_id)
        return qs.order_by("-assigned_at")

    @classmethod
    def obtener(cls, custody_id):
        return cls.base_queryset().prefetch_related("events").get(pk=custody_id)

    @classmethod
    def activo_del_bien(cls, asset_id):
        return cls.base_queryset().filter(asset_id=asset_id, status=CustodyStatus.ACTIVE).first()

    @classmethod
    def historial_del_bien(cls, asset_id):
        return cls.listar(asset_id=asset_id)
