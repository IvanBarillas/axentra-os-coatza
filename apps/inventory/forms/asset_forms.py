# apps/inventory/forms/asset_forms.py

from django import forms
from django.utils import timezone

from apps.inventory.models import (
    AccountingAccount,
    Asset,
    AssetCategory,
    AssetModel,
    Contract,
    Manufacturer,
    Supplier,
)
from apps.inventory.forms.base_styler import AxentraFormStylerMixin

from apps.security.models.organigrama import AreaOperativa, Dependencia, Sede


class AssetForm(AxentraFormStylerMixin, forms.ModelForm):
    class Meta:
        model = Asset
        fields = [
            "inventory_number",
            "legacy_inventory_number",
            "name",
            "description",
            "category",
            "accounting_account",
            "control_type",
            "lifecycle_status",
            "physical_condition",
            "acquisition_type",
            "acquisition_date",
            "registration_date",
            "acquisition_cost",
            "residual_value",
            "useful_life_months",
            "is_capitalizable",
            "capitalization_threshold_amount",
            "manufacturer",
            "model",
            "serial_number",
            "supplier",
            "contract",
            "sede",
            "dependencia",
            "area",
            "current_custodian",
            "latitude",
            "longitude",
            "notes",
            "extra_attributes",
        ]

        widgets = {
            "inventory_number": forms.TextInput(
                attrs={
                    "placeholder": "Ej: COATZA-TI-000001",
                    "autocomplete": "off",
                }
            ),
            "legacy_inventory_number": forms.TextInput(
                attrs={
                    "placeholder": "Número anterior si existe",
                    "autocomplete": "off",
                }
            ),
            "name": forms.TextInput(
                attrs={
                    "placeholder": "Ej: COMPUTADORA DELL OPTIPLEX SOPORTE",
                    "autocomplete": "off",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "Descripción detallada del bien patrimonial.",
                }
            ),
            "serial_number": forms.TextInput(
                attrs={
                    "placeholder": "Número de serie / Service Tag",
                    "autocomplete": "off",
                }
            ),
            "acquisition_date": forms.DateInput(attrs={"type": "date"}),
            "registration_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "Notas internas del expediente.",
                }
            ),
            "extra_attributes": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": '{"hostname": "COATZA-PC-001", "vlan": "10"}',
                }
            ),
        }

        labels = {
            "inventory_number": "Número de inventario / placa patrimonial",
            "legacy_inventory_number": "Número de inventario anterior",
            "name": "Nombre / descripción corta",
            "description": "Descripción detallada",
            "category": "Categoría patrimonial",
            "accounting_account": "Cuenta contable",
            "control_type": "Tipo de control",
            "lifecycle_status": "Estado patrimonial",
            "physical_condition": "Estado físico",
            "acquisition_type": "Tipo de adquisición",
            "acquisition_date": "Fecha de adquisición",
            "registration_date": "Fecha de registro",
            "acquisition_cost": "Costo de adquisición",
            "residual_value": "Valor residual / desecho",
            "useful_life_months": "Vida útil en meses",
            "is_capitalizable": "Capitalizable contablemente",
            "capitalization_threshold_amount": "Umbral de capitalización aplicado",
            "manufacturer": "Fabricante",
            "model": "Modelo",
            "serial_number": "Número de serie",
            "supplier": "Proveedor",
            "contract": "Contrato",
            "sede": "Sede física",
            "dependencia": "Dependencia responsable",
            "area": "Área operativa",
            "current_custodian": "Resguardatario actual",
            "latitude": "Latitud",
            "longitude": "Longitud",
            "notes": "Notas",
            "extra_attributes": "Atributos extendidos JSON",
        }

        help_texts = {
            "inventory_number": "Folio oficial de patrimonio o folio interno generado por Axentra.",
            "control_type": "Define si el bien será activo fijo capitalizado, control interno o consumible.",
            "is_capitalizable": "Marca si el bien supera el umbral contable aplicable.",
            "extra_attributes": "Datos flexibles no críticos. Ejemplo: datos técnicos temporales.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        today = timezone.localdate()

        self.fields["registration_date"].initial = (
            self.fields["registration_date"].initial or today
        )

        self.fields["category"].queryset = AssetCategory.objects.filter(
            is_active=True,
            is_deleted=False,
        ).order_by("nature", "name")

        self.fields["category"].empty_label = "--- Seleccione categoría patrimonial ---"
        self.fields["category"].label_from_instance = (
            lambda obj: f"{obj.code} · {obj.name}"
        )

        self.fields["accounting_account"].queryset = AccountingAccount.objects.filter(
            is_active=True,
            is_deleted=False,
        ).select_related("category").order_by("code")

        self.fields["accounting_account"].empty_label = "--- Seleccione cuenta contable ---"
        self.fields["accounting_account"].label_from_instance = (
            lambda obj: f"{obj.code} · {obj.name}"
        )

        self.fields["manufacturer"].queryset = Manufacturer.objects.filter(
            is_active=True,
            is_deleted=False,
        ).order_by("name")
        self.fields["manufacturer"].empty_label = "--- Fabricante opcional ---"

        self.fields["model"].queryset = AssetModel.objects.filter(
            is_active=True,
            is_deleted=False,
        ).select_related("manufacturer").order_by("manufacturer__name", "name")
        self.fields["model"].empty_label = "--- Modelo opcional ---"
        self.fields["model"].label_from_instance = (
            lambda obj: f"{obj.manufacturer.name} · {obj.name}"
        )

        self.fields["supplier"].queryset = Supplier.objects.filter(
            is_active=True,
            is_deleted=False,
        ).order_by("razon_social")
        self.fields["supplier"].empty_label = "--- Proveedor opcional ---"

        self.fields["contract"].queryset = Contract.objects.filter(
            is_active=True,
            is_deleted=False,
        ).select_related("supplier").order_by("-fecha_inicio", "numero_contrato")
        self.fields["contract"].empty_label = "--- Contrato opcional ---"

        self.fields["sede"].queryset = Sede.objects.filter(
            is_active=True,
            is_deleted=False,
        ).order_by("nombre")
        self.fields["sede"].empty_label = "--- Seleccione sede física ---"

        self.fields["dependencia"].queryset = Dependencia.objects.filter(
            is_active=True,
            is_deleted=False,
        ).order_by("nombre")
        self.fields["dependencia"].empty_label = "--- Seleccione dependencia ---"

        self.fields["area"].queryset = AreaOperativa.objects.filter(
            is_active=True,
            is_deleted=False,
        ).select_related("dependencia", "sede_fisica").order_by(
            "dependencia__nombre",
            "nombre",
        )
        self.fields["area"].empty_label = "--- Seleccione área operativa ---"
        self.fields["area"].label_from_instance = (
            lambda obj: (
                f"{obj.dependencia.nombre.upper()} → "
                f"{obj.nombre.upper()} "
                f"[{obj.sede_fisica.nombre.upper()}]"
            )
        )

        self.aplicar_estilos_institucionales()

    def clean_inventory_number(self):
        value = self.cleaned_data["inventory_number"]
        return value.strip().upper()

    def clean_name(self):
        value = self.cleaned_data["name"]
        return value.strip().upper()

    def clean_serial_number(self):
        value = self.cleaned_data.get("serial_number")

        if not value:
            return value

        return value.strip().upper()