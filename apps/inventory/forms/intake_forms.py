# apps/inventory/forms/intake_forms.py

from django import forms
from django.utils import timezone

from apps.inventory.dtos import (
    CancelAssetIntakeDTO,
    CreateAssetIntakeDTO,
    DepartmentIntakeDecisionDTO,
    PatrimonyApprovalDTO,
    PatrimonyObservationDTO,
    UpdateAssetIntakeDTO,
)
from apps.inventory.forms.base_forms import (
    DATE_WIDGET,
    InventoryForm,
    UUIDChoiceField,
)
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
    name = forms.CharField(
        label="Nombre o descripción corta",
        max_length=180,
    )
    description = forms.CharField(
        label="Descripción detallada",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    category = forms.ModelChoiceField(
        label="Categoría patrimonial",
        queryset=AssetCategory.objects.none(),
        empty_label="--- Seleccione categoría ---",
    )
    expenditure_object = forms.ModelChoiceField(
        label="Clasificador por objeto del gasto",
        queryset=ExpenditureObject.objects.none(),
        required=False,
        empty_label="--- Se completará antes del envío ---",
        help_text=(
            "Puede omitirse en el borrador, pero será obligatorio para "
            "enviar la solicitud."
        ),
    )
    accounting_account = forms.ModelChoiceField(
        label="Cuenta contable",
        queryset=AccountingAccount.objects.none(),
        required=False,
        empty_label="--- Determinada por el clasificador ---",
    )
    acquisition_type = forms.ChoiceField(
        label="Tipo de adquisición",
        choices=AcquisitionType.choices,
    )
    acquisition_date = forms.DateField(
        label="Fecha de adquisición",
        required=False,
        widget=DATE_WIDGET,
        help_text="Será obligatoria al enviar la solicitud.",
    )
    reception_date = forms.DateField(
        label="Fecha de recepción física",
        required=False,
        widget=DATE_WIDGET,
    )
    acquisition_cost = forms.DecimalField(
        label="Costo de adquisición",
        min_value=0,
        max_digits=16,
        decimal_places=2,
    )
    residual_value = forms.DecimalField(
        label="Valor residual propuesto",
        min_value=0,
        max_digits=16,
        decimal_places=2,
        initial=0,
    )
    manufacturer = forms.ModelChoiceField(
        label="Fabricante",
        queryset=Manufacturer.objects.none(),
        required=False,
        empty_label="--- Fabricante opcional ---",
    )
    model = forms.ModelChoiceField(
        label="Modelo",
        queryset=AssetModel.objects.none(),
        required=False,
        empty_label="--- Modelo opcional ---",
    )
    serial_number = forms.CharField(
        label="Número de serie / Service Tag",
        max_length=120,
        required=False,
    )
    supplier = forms.ModelChoiceField(
        label="Proveedor",
        queryset=Supplier.objects.none(),
        required=False,
        empty_label="--- Proveedor opcional ---",
    )
    contract = forms.ModelChoiceField(
        label="Contrato",
        queryset=Contract.objects.none(),
        required=False,
        empty_label="--- Contrato opcional ---",
    )
    requested_department_id = UUIDChoiceField(
        label="Dependencia receptora",
        help_text=(
            "Dependencia a cuyo inventario ingresará el bien después de la "
            "aceptación y validación patrimonial."
        ),
    )
    requested_site_id = UUIDChoiceField(
        label="Sede receptora propuesta",
        required=False,
    )
    requested_area_id = UUIDChoiceField(
        label="Área receptora propuesta",
        required=False,
    )
    proposed_custodian_id = UUIDChoiceField(
        label="Resguardatario propuesto",
        required=False,
        help_text=(
            "Debe pertenecer a la dependencia receptora. El servicio lo "
            "validará nuevamente."
        ),
    )
    notes = forms.CharField(
        label="Notas internas",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        active = {"is_active": True, "is_deleted": False}

        self.fields["category"].queryset = (
            AssetCategory.objects
            .filter(**active)
            .order_by("nature", "code", "name")
        )
        self.fields["expenditure_object"].queryset = (
            ExpenditureObject.objects
            .filter(**active)
            .select_related("category", "accounting_account")
            .order_by("code")
        )
        self.fields["accounting_account"].queryset = (
            AccountingAccount.objects
            .filter(**active)
            .select_related("category")
            .order_by("code")
        )
        self.fields["manufacturer"].queryset = (
            Manufacturer.objects
            .filter(**active)
            .order_by("name")
        )
        self.fields["model"].queryset = (
            AssetModel.objects
            .filter(**active)
            .select_related("manufacturer")
            .order_by("manufacturer__name", "name")
        )
        self.fields["supplier"].queryset = (
            Supplier.objects
            .filter(**active)
            .order_by("razon_social")
        )
        self.fields["contract"].queryset = (
            Contract.objects
            .filter(**active)
            .select_related("supplier")
            .order_by("-fecha_inicio", "numero_contrato")
        )

    def clean(self):
        data = super().clean()
        today = timezone.localdate()

        acquisition_cost = data.get("acquisition_cost")
        residual_value = data.get("residual_value")
        if (
            residual_value is not None
            and acquisition_cost is not None
            and residual_value > acquisition_cost
        ):
            self.add_error(
                "residual_value",
                "No puede superar el costo de adquisición.",
            )

        acquisition_date = data.get("acquisition_date")
        reception_date = data.get("reception_date")
        if acquisition_date and acquisition_date > today:
            self.add_error(
                "acquisition_date",
                "La fecha de adquisición no puede estar en el futuro.",
            )

        if reception_date and reception_date > today:
            self.add_error(
                "reception_date",
                "La fecha de recepción no puede estar en el futuro.",
            )

        if (
            reception_date
            and acquisition_date
            and reception_date < acquisition_date
        ):
            self.add_error(
                "reception_date",
                "No puede ser anterior a la adquisición.",
            )

        category = data.get("category")
        expenditure_object = data.get("expenditure_object")
        accounting_account = data.get("accounting_account")

        if (
            category
            and expenditure_object
            and expenditure_object.category_id != category.id
        ):
            self.add_error(
                "expenditure_object",
                "El clasificador no pertenece a la categoría seleccionada.",
            )

        if expenditure_object and accounting_account is None:
            data["accounting_account"] = (
                expenditure_object.accounting_account
            )
            accounting_account = data["accounting_account"]

        if (
            category
            and accounting_account
            and accounting_account.category_id not in {None, category.id}
        ):
            self.add_error(
                "accounting_account",
                "La cuenta contable pertenece a otra categoría.",
            )

        model = data.get("model")
        manufacturer = data.get("manufacturer")
        if model and manufacturer is None:
            data["manufacturer"] = model.manufacturer
            manufacturer = model.manufacturer

        if (
            model
            and manufacturer
            and model.manufacturer_id != manufacturer.id
        ):
            self.add_error(
                "model",
                "El modelo no pertenece al fabricante seleccionado.",
            )

        contract = data.get("contract")
        supplier = data.get("supplier")
        if contract and supplier is None:
            data["supplier"] = contract.supplier
            supplier = contract.supplier

        if (
            contract
            and supplier
            and contract.supplier_id != supplier.id
        ):
            self.add_error(
                "contract",
                "El contrato no pertenece al proveedor seleccionado.",
            )

        serial_number = data.get("serial_number")
        if serial_number:
            data["serial_number"] = serial_number.strip().upper()

        return data

    def _dto_kwargs(self):
        data = self.require_cleaned_data()
        expenditure_object = data.get("expenditure_object")
        accounting_account = data.get("accounting_account")
        manufacturer = data.get("manufacturer")
        model = data.get("model")
        supplier = data.get("supplier")
        contract = data.get("contract")

        return {
            "name": data["name"],
            "description": data.get("description", ""),
            "category_id": data["category"].id,
            "expenditure_object_id": (
                expenditure_object.id if expenditure_object else None
            ),
            "accounting_account_id": (
                accounting_account.id if accounting_account else None
            ),
            "acquisition_type": data["acquisition_type"],
            "acquisition_date": data.get("acquisition_date"),
            "reception_date": data.get("reception_date"),
            "acquisition_cost": data["acquisition_cost"],
            "residual_value": data["residual_value"],
            "manufacturer_id": (
                manufacturer.id if manufacturer else None
            ),
            "model_id": model.id if model else None,
            "serial_number": data.get("serial_number") or None,
            "supplier_id": supplier.id if supplier else None,
            "contract_id": contract.id if contract else None,
            "requested_department_id": data[
                "requested_department_id"
            ],
            "requested_site_id": data.get("requested_site_id"),
            "requested_area_id": data.get("requested_area_id"),
            "proposed_custodian_id": data.get(
                "proposed_custodian_id"
            ),
            "notes": data.get("notes", ""),
        }


class AssetIntakeCreateForm(AssetIntakeBaseForm):
    def to_dto(self):
        return CreateAssetIntakeDTO(**self._dto_kwargs())


class AssetIntakeUpdateForm(AssetIntakeBaseForm):
    def to_dto(self):
        return UpdateAssetIntakeDTO(**self._dto_kwargs())


class DepartmentIntakeDecisionForm(InventoryForm):
    DECISION_APPROVE = "APPROVE"
    DECISION_REJECT = "REJECT"

    decision = forms.ChoiceField(
        label="Decisión",
        choices=(
            (DECISION_APPROVE, "Aceptar el ingreso del bien"),
            (DECISION_REJECT, "Rechazar la solicitud"),
        ),
        widget=forms.RadioSelect,
    )
    comment = forms.CharField(
        label="Comentario o motivo",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    bypass_reason = forms.CharField(
        label="Justificación de bypass",
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
    )

    def clean(self):
        data = super().clean()
        if (
            data.get("decision") == self.DECISION_REJECT
            and not str(data.get("comment", "")).strip()
        ):
            self.add_error(
                "comment",
                "Indique el motivo del rechazo.",
            )
        return data

    def to_dto(self):
        data = self.require_cleaned_data()
        return DepartmentIntakeDecisionDTO(
            approve=data["decision"] == self.DECISION_APPROVE,
            comment=data.get("comment", ""),
            bypass_reason=data.get("bypass_reason", ""),
        )


class PatrimonyApprovalForm(InventoryForm):
    expenditure_object = forms.ModelChoiceField(
        label="Clasificador definitivo",
        queryset=ExpenditureObject.objects.none(),
    )
    accounting_account = forms.ModelChoiceField(
        label="Cuenta contable definitiva",
        queryset=AccountingAccount.objects.none(),
        required=False,
    )
    physical_condition = forms.ChoiceField(
        label="Condición física inicial",
        choices=PhysicalCondition.choices,
        initial=PhysicalCondition.GOOD,
    )
    residual_value = forms.DecimalField(
        label="Valor residual definitivo",
        required=False,
        min_value=0,
        max_digits=16,
        decimal_places=2,
    )
    useful_life_months = forms.IntegerField(
        label="Vida útil en meses",
        required=False,
        min_value=1,
    )
    observation = forms.CharField(
        label="Observación patrimonial",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    bypass_reason = forms.CharField(
        label="Justificación de bypass",
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        active = {"is_active": True, "is_deleted": False}
        self.fields["expenditure_object"].queryset = (
            ExpenditureObject.objects
            .filter(**active)
            .select_related("category", "accounting_account")
            .order_by("code")
        )
        self.fields["accounting_account"].queryset = (
            AccountingAccount.objects
            .filter(**active)
            .select_related("category")
            .order_by("code")
        )

    def clean(self):
        data = super().clean()
        expenditure_object = data.get("expenditure_object")
        accounting_account = data.get("accounting_account")

        if expenditure_object and accounting_account is None:
            data["accounting_account"] = (
                expenditure_object.accounting_account
            )
            accounting_account = data["accounting_account"]

        if expenditure_object and accounting_account:
            if accounting_account.category_id not in {
                None,
                expenditure_object.category_id,
            }:
                self.add_error(
                    "accounting_account",
                    "La cuenta no corresponde al clasificador seleccionado.",
                )

        return data

    def to_dto(self):
        data = self.require_cleaned_data()
        accounting_account = data.get("accounting_account")
        return PatrimonyApprovalDTO(
            expenditure_object_id=data["expenditure_object"].id,
            accounting_account_id=(
                accounting_account.id if accounting_account else None
            ),
            physical_condition=data["physical_condition"],
            residual_value=data.get("residual_value"),
            useful_life_months=data.get("useful_life_months"),
            observation=data.get("observation", ""),
        )


class PatrimonyObservationForm(InventoryForm):
    observation = forms.CharField(
        label="Observación patrimonial",
        widget=forms.Textarea(attrs={"rows": 4}),
    )

    def to_dto(self):
        return PatrimonyObservationDTO(
            observation=self.require_cleaned_data()["observation"],
        )


class CancelAssetIntakeForm(InventoryForm):
    reason = forms.CharField(
        label="Motivo de cancelación",
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    bypass_reason = forms.CharField(
        label="Justificación de bypass",
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
    )

    def to_dto(self):
        data = self.require_cleaned_data()
        return CancelAssetIntakeDTO(
            reason=data["reason"],
            bypass_reason=data.get("bypass_reason", ""),
        )


__all__ = [
    "AssetIntakeCreateForm",
    "AssetIntakeUpdateForm",
    "CancelAssetIntakeForm",
    "DepartmentIntakeDecisionForm",
    "PatrimonyApprovalForm",
    "PatrimonyObservationForm",
]
