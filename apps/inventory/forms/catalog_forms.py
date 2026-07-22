from django import forms

from apps.inventory.forms.base_forms import InventoryFormMixin
from apps.inventory.models import (
    AccountingAccount,
    AssetCategory,
    AssetModel,
    ExpenditureObject,
    Manufacturer,
)


class CatalogModelForm(InventoryFormMixin, forms.ModelForm):
    """Base visual común para catálogos administrables de Inventory."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "is_active" in self.fields:
            self.fields["is_active"].label = "Activo"


class AssetCategoryForm(CatalogModelForm):
    class Meta:
        model = AssetCategory
        fields = (
            "code", "name", "nature", "description",
            "requires_serial_number", "requires_photographic_evidence",
            "requires_custody_assignment", "is_active",
        )
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}


class AccountingAccountForm(CatalogModelForm):
    class Meta:
        model = AccountingAccount
        fields = (
            "code", "name", "account_type", "category", "is_depreciable",
            "default_useful_life_months", "default_annual_depreciation_rate",
            "external_system_code", "is_active",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].label = "Categoría patrimonial"
        self.fields["category"].queryset = AssetCategory.objects.filter(
            is_deleted=False
        ).order_by("name")


class ExpenditureObjectForm(CatalogModelForm):
    class Meta:
        model = ExpenditureObject
        fields = (
            "code", "name", "description", "category", "accounting_account",
            "default_asset_type_code", "capitalization_rule", "uma_multiplier",
            "requires_inventory_control", "requires_accounting_reconciliation",
            "external_system_code", "is_active",
        )
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        available = {"is_deleted": False}
        self.fields["category"].queryset = AssetCategory.objects.filter(
            **available
        ).order_by("name")
        self.fields["accounting_account"].queryset = (
            AccountingAccount.objects.filter(**available)
            .select_related("category")
            .order_by("code")
        )


class ManufacturerForm(CatalogModelForm):
    class Meta:
        model = Manufacturer
        fields = ("name", "is_active")


class AssetModelForm(CatalogModelForm):
    class Meta:
        model = AssetModel
        fields = ("manufacturer", "name", "description", "is_active")
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["manufacturer"].label = "Fabricante"
        self.fields["manufacturer"].queryset = Manufacturer.objects.filter(
            is_deleted=False
        ).order_by("name")


__all__ = [
    "AccountingAccountForm",
    "AssetCategoryForm",
    "AssetModelForm",
    "ExpenditureObjectForm",
    "ManufacturerForm",
]
