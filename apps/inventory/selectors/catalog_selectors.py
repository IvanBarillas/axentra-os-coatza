from django.db.models import QuerySet
from django.utils import timezone

from apps.inventory.integrations import core_directory
from apps.inventory.models import (
    AccountingAccount, AssetCategory, AssetModel, CapitalizationRule, Contract,
    ExpenditureObject, InventoryFolioPolicy, Manufacturer, Supplier, UmaValue,
)


class CatalogSelectors:
    @staticmethod
    def categories(*, nature=None) -> QuerySet:
        qs = AssetCategory.objects.filter(is_active=True, is_deleted=False)
        return qs.filter(nature=nature).order_by("code") if nature else qs.order_by("code")

    @staticmethod
    def accounting_accounts(*, category_id=None) -> QuerySet:
        qs = AccountingAccount.objects.filter(is_active=True, is_deleted=False).select_related("category")
        return qs.filter(category_id=category_id).order_by("code") if category_id else qs.order_by("code")

    @staticmethod
    def expenditure_objects(*, category_id=None) -> QuerySet:
        qs = ExpenditureObject.objects.filter(is_active=True, is_deleted=False).select_related("category")
        return qs.filter(category_id=category_id).order_by("code") if category_id else qs.order_by("code")

    @staticmethod
    def manufacturers() -> QuerySet:
        return Manufacturer.objects.filter(is_active=True, is_deleted=False).order_by("name")

    @staticmethod
    def models(*, manufacturer_id=None) -> QuerySet:
        qs = AssetModel.objects.filter(is_active=True, is_deleted=False).select_related("manufacturer")
        return qs.filter(manufacturer_id=manufacturer_id).order_by("name") if manufacturer_id else qs.order_by("manufacturer__name", "name")

    @staticmethod
    def suppliers() -> QuerySet:
        return Supplier.objects.filter(is_active=True, is_deleted=False).order_by("razon_social")

    @staticmethod
    def contracts(*, supplier_id=None) -> QuerySet:
        qs = Contract.objects.filter(is_active=True, is_deleted=False).select_related("supplier")
        return qs.filter(supplier_id=supplier_id).order_by("-fecha_inicio") if supplier_id else qs.order_by("-fecha_inicio")

    @staticmethod
    def current_uma(*, on_date=None):
        date = on_date or timezone.localdate()
        return UmaValue.objects.filter(
            is_active=True, is_deleted=False,
            effective_from__lte=date, effective_until__gte=date,
        ).order_by("-effective_from").first()

    @staticmethod
    def capitalization_rules() -> QuerySet:
        return CapitalizationRule.choices

    @staticmethod
    def folio_policies() -> QuerySet:
        return InventoryFolioPolicy.objects.filter(is_active=True, is_deleted=False).order_by("name")


class CoreDirectorySelectors:
    """Opciones del Core obtenidas sólo mediante el adaptador desacoplado."""

    @staticmethod
    def departments():
        return core_directory.list_departments()

    @staticmethod
    def sites():
        return core_directory.list_sites()

    @staticmethod
    def areas(*, department_id=None, site_id=None):
        return core_directory.list_areas(department_id=department_id, site_id=site_id)

    @staticmethod
    def users(*, department_id=None):
        return core_directory.list_users(department_id=department_id)

    @classmethod
    def form_choices(cls, *, department_id=None, site_id=None):
        return {
            "department_choices": [(str(x.id), f"{x.code or 'SIN-CÓDIGO'} · {x.name}") for x in cls.departments()],
            "site_choices": [(str(x.id), x.name) for x in cls.sites()],
            "area_choices": [(str(x.id), x.name) for x in cls.areas(department_id=department_id, site_id=site_id)],
            "user_choices": [(str(x.id), x.display_name) for x in cls.users(department_id=department_id)],
        }
