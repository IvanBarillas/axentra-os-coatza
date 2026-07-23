from django import forms

from apps.inventory.dtos import (
    CancelAssetIntakeDTO,
    CreateAssetIntakeDTO,
    DepartmentIntakeDecisionDTO,
    PatrimonyApprovalDTO,
    PatrimonyObservationDTO,
    UpdateAssetIntakeDTO,
)
from apps.inventory.forms.base_forms import DATE_WIDGET, InventoryForm, UUIDChoiceField
from apps.inventory.models import (
    AccountingAccount,
    AcquisitionType,
    AssetCategory,
    AssetModel,
    Contract,
    ExpenditureObject,
    Manufacturer,
    PhysicalCondition,
    Supplier,
)


class AssetIntakeBaseForm(InventoryForm):
    name = forms.CharField(max_length=180)
    description = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    category = forms.ModelChoiceField(queryset=AssetCategory.objects.none())
    expenditure_object = forms.ModelChoiceField(queryset=ExpenditureObject.objects.none(), required=False)
    accounting_account = forms.ModelChoiceField(queryset=AccountingAccount.objects.none(), required=False)
    acquisition_type = forms.ChoiceField(choices=AcquisitionType.choices)
    acquisition_date = forms.DateField(required=False, widget=DATE_WIDGET)
    reception_date = forms.DateField(required=False, widget=DATE_WIDGET)
    acquisition_cost = forms.DecimalField(min_value=0, max_digits=16, decimal_places=2)
    residual_value = forms.DecimalField(min_value=0, max_digits=16, decimal_places=2, initial=0)
    manufacturer = forms.ModelChoiceField(queryset=Manufacturer.objects.none(), required=False)
    model = forms.ModelChoiceField(queryset=AssetModel.objects.none(), required=False)
    serial_number = forms.CharField(max_length=120, required=False)
    invoice_number = forms.CharField(
        label="Número de factura",
        max_length=120,
        required=False,
        help_text="Referencia visible de la factura. El PDF o XML se carga por separado.",
    )
    supplier = forms.ModelChoiceField(queryset=Supplier.objects.none(), required=False)
    contract = forms.ModelChoiceField(queryset=Contract.objects.none(), required=False)
    requested_site_id = UUIDChoiceField()
    requested_department_id = UUIDChoiceField()
    requested_area_id = UUIDChoiceField(required=False)
    proposed_custodian_id = UUIDChoiceField(required=False)
    location_detail = forms.CharField(
        required=False,
        max_length=255,
        widget=forms.TextInput(attrs={"placeholder": "Ej. Rack del cuarto piso, oficina 204"}),
        help_text="Indique la ubicación precisa dentro de la sede cuando aplique.",
    )
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound and not self.initial.get("invoice_number"):
            self.initial["invoice_number"] = (
                self.initial.get("extra_attributes") or {}
            ).get("invoice_number", "")
        labels = {
            "name": "Nombre del bien", "description": "Descripción",
            "category": "Categoría patrimonial", "expenditure_object": "Objeto del gasto",
            "accounting_account": "Cuenta contable", "acquisition_type": "Tipo de adquisición",
            "acquisition_date": "Fecha de adquisición", "reception_date": "Fecha de recepción",
            "acquisition_cost": "Costo de adquisición", "residual_value": "Valor residual",
            "manufacturer": "Fabricante", "model": "Modelo", "serial_number": "Número de serie",
            "invoice_number": "Número de factura", "supplier": "Proveedor", "contract": "Contrato",
            "requested_site_id": "Sede receptora", "requested_department_id": "Dependencia receptora",
            "requested_area_id": "Área receptora propuesta",
            "proposed_custodian_id": "Resguardatario propuesto (opcional)",
            "location_detail": "Detalle de ubicación física", "notes": "Notas internas",
        }
        for field_name, label in labels.items():
            self.fields[field_name].label = label
        active = {"is_active": True, "is_deleted": False}
        self.fields["category"].queryset = AssetCategory.objects.filter(**active).order_by("name")
        self.fields["expenditure_object"].queryset = ExpenditureObject.objects.filter(**active).order_by("code")
        self.fields["accounting_account"].queryset = AccountingAccount.objects.filter(**active).order_by("code")
        self.fields["manufacturer"].queryset = Manufacturer.objects.filter(**active).order_by("name")
        self.fields["model"].queryset = AssetModel.objects.none()
        manufacturer_id = self.data.get("manufacturer") if self.is_bound else self.initial.get("manufacturer")
        if manufacturer_id:
            self.fields["model"].queryset = AssetModel.objects.filter(
                **active, manufacturer_id=manufacturer_id
            ).select_related("manufacturer").order_by("name")
        self.fields["supplier"].queryset = Supplier.objects.filter(**active).order_by("razon_social")
        self.fields["contract"].queryset = Contract.objects.filter(**active).select_related("supplier").order_by("-fecha_inicio")

    def clean_invoice_number(self):
        return str(self.cleaned_data.get("invoice_number") or "").strip().upper()

    def clean(self):
        data = super().clean()
        if data.get("residual_value") is not None and data.get("acquisition_cost") is not None:
            if data["residual_value"] > data["acquisition_cost"]:
                self.add_error("residual_value", "No puede superar el costo de adquisición.")
        if data.get("reception_date") and data.get("acquisition_date"):
            if data["reception_date"] < data["acquisition_date"]:
                self.add_error("reception_date", "No puede ser anterior a la adquisición.")
        model = data.get("model"); manufacturer = data.get("manufacturer")
        if model and manufacturer and model.manufacturer_id != manufacturer.id:
            self.add_error("model", "El modelo no pertenece al fabricante.")
        contract = data.get("contract"); supplier = data.get("supplier")
        if contract and supplier and contract.supplier_id != supplier.id:
            self.add_error("contract", "El contrato no pertenece al proveedor.")
        return data

    def _dto_kwargs(self):
        d = self.require_cleaned_data()
        extra_attributes = dict(self.initial.get("extra_attributes") or {})
        if d.get("invoice_number"):
            extra_attributes["invoice_number"] = d["invoice_number"]
        else:
            extra_attributes.pop("invoice_number", None)
        return {
            "name": d["name"], "description": d.get("description", ""),
            "category_id": d["category"].id,
            "expenditure_object_id": d["expenditure_object"].id if d.get("expenditure_object") else None,
            "accounting_account_id": d["accounting_account"].id if d.get("accounting_account") else None,
            "acquisition_type": d["acquisition_type"], "acquisition_date": d.get("acquisition_date"),
            "reception_date": d.get("reception_date"), "acquisition_cost": d["acquisition_cost"],
            "residual_value": d["residual_value"],
            "manufacturer_id": d["manufacturer"].id if d.get("manufacturer") else None,
            "model_id": d["model"].id if d.get("model") else None,
            "serial_number": d.get("serial_number") or None,
            "invoice_number": d.get("invoice_number", ""),
            "supplier_id": d["supplier"].id if d.get("supplier") else None,
            "contract_id": d["contract"].id if d.get("contract") else None,
            "requested_department_id": d["requested_department_id"],
            "requested_site_id": d.get("requested_site_id"),
            "requested_area_id": d.get("requested_area_id"),
            "proposed_custodian_id": d.get("proposed_custodian_id"),
            "location_detail": d.get("location_detail", ""),
            "notes": d.get("notes", ""),
            "extra_attributes": extra_attributes,
        }


class AssetIntakeCreateForm(AssetIntakeBaseForm):
    def to_dto(self): return CreateAssetIntakeDTO(**self._dto_kwargs())


class AssetIntakeUpdateForm(AssetIntakeBaseForm):
    def to_dto(self): return UpdateAssetIntakeDTO(**self._dto_kwargs())


class DepartmentIntakeDecisionForm(InventoryForm):
    approve = forms.BooleanField(required=False)
    comment = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    bypass_reason = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))
    def clean(self):
        data = super().clean()
        if not data.get("approve") and not str(data.get("comment", "")).strip():
            self.add_error("comment", "Indique el motivo del rechazo.")
        return data
    def to_dto(self):
        data = self.require_cleaned_data()
        return DepartmentIntakeDecisionDTO(data["approve"], data.get("comment", ""), data.get("bypass_reason", ""))


class PatrimonyApprovalForm(InventoryForm):
    expenditure_object = forms.ModelChoiceField(queryset=ExpenditureObject.objects.none())
    accounting_account = forms.ModelChoiceField(queryset=AccountingAccount.objects.none(), required=False)
    physical_condition = forms.ChoiceField(choices=PhysicalCondition.choices, initial=PhysicalCondition.GOOD)
    residual_value = forms.DecimalField(required=False, min_value=0, max_digits=16, decimal_places=2)
    useful_life_months = forms.IntegerField(required=False, min_value=1)
    observation = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    bypass_reason = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        active = {"is_active": True, "is_deleted": False}
        self.fields["expenditure_object"].queryset = ExpenditureObject.objects.filter(**active).order_by("code")
        self.fields["accounting_account"].queryset = AccountingAccount.objects.filter(**active).order_by("code")
    def to_dto(self):
        data = self.require_cleaned_data()
        return PatrimonyApprovalDTO(data["expenditure_object"].id, data["accounting_account"].id if data.get("accounting_account") else None, data["physical_condition"], data.get("residual_value"), data.get("useful_life_months"), data.get("observation", ""))


class PatrimonyObservationForm(InventoryForm):
    observation = forms.CharField(widget=forms.Textarea(attrs={"rows": 4}))
    def to_dto(self): return PatrimonyObservationDTO(self.require_cleaned_data()["observation"])


class CancelAssetIntakeForm(InventoryForm):
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}))
    bypass_reason = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))
    def to_dto(self):
        data = self.require_cleaned_data()
        return CancelAssetIntakeDTO(data["reason"], data.get("bypass_reason", ""))


__all__ = [name for name in globals() if name.endswith("Form") and not name.endswith("BaseForm")]
