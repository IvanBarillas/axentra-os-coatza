# apps/inventory/selectors/asset_selectors.py

from django.db.models import Count, Q, Sum

from apps.inventory.models import Asset


class AssetSelectors:
    @staticmethod
    def dashboard_metrics() -> dict:
        activos = Asset.objects.filter(is_deleted=False)

        return {
            "total_assets": activos.count(),
            "capitalized_assets": activos.filter(is_capitalizable=True).count(),
            "internal_control_assets": activos.filter(is_capitalizable=False).count(),
            "assigned_assets": activos.filter(current_custodian__isnull=False).count(),
            "total_book_value": activos.aggregate(
                total=Sum("acquisition_cost")
            )["total"] or 0,
        }

    @staticmethod
    def listar_activos(*, q: str = "", status: str = "", category_id: str = ""):
        queryset = (
            Asset.objects
            .filter(is_deleted=False)
            .select_related(
                "category",
                "accounting_account",
                "manufacturer",
                "model",
                "sede",
                "dependencia",
                "area",
                "current_custodian",
            )
            .order_by("-created_at")
        )

        if q:
            queryset = queryset.filter(
                Q(inventory_number__icontains=q)
                | Q(legacy_inventory_number__icontains=q)
                | Q(name__icontains=q)
                | Q(description__icontains=q)
                | Q(serial_number__icontains=q)
                | Q(manufacturer__name__icontains=q)
                | Q(model__name__icontains=q)
                | Q(current_custodian__email__icontains=q)
                | Q(current_custodian__first_name__icontains=q)
                | Q(current_custodian__last_name__icontains=q)
            )

        if status:
            queryset = queryset.filter(lifecycle_status=status)

        if category_id:
            queryset = queryset.filter(category_id=category_id)

        return queryset

    @staticmethod
    def obtener_expediente(asset_id):
        return (
            Asset.objects
            .select_related(
                "category",
                "accounting_account",
                "manufacturer",
                "model",
                "supplier",
                "contract",
                "sede",
                "dependencia",
                "area",
                "current_custodian",
            )
            .prefetch_related(
                "documents",
                "photos",
                "movements",
                "custody_assignments",
                "depreciation_records",
                "child_relations",
                "parent_relations",
                "audit_logs",
            )
            .get(id=asset_id, is_deleted=False)
        )