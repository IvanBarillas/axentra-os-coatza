from django import forms

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
    InventoryAssetType,
    AssetModel,
    Contract,
    ExpenditureObject,
    Manufacturer,
    PhysicalCondition,
    Supplier,
)


class AssetIntakeBaseForm(InventoryForm):
    name = forms.CharField(
        label="Nombre del bien",
        max_length=180,
        help_text="Descripción corta que permitirá identificar el bien.",
    )
    description = forms.CharField(
        label="Descripción detallada",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Incluya características técnicas relevantes; no copie solamente toda la factura.",
    )
    category = forms.ModelChoiceField(
        label="Categoría patrimonial",
        queryset=AssetCategory.objects.none(),
        help_text="La naturaleza de la categoría permite determinar automáticamente si corresponde BI.",
    )
    proposed_asset_type = forms.ModelChoiceField(
        label="Tipo patrimonial propuesto",
        queryset=InventoryAssetType.objects.none(),
        required=False,
        help_text=(
            "Es una propuesta del capturista. El sistema calculará el tipo "
            "normativo y Patrimonio resolverá cualquier diferencia."
        ),
    )
    expenditure_object = forms.ModelChoiceField(
        label="Clasificador por objeto del gasto (CONAC)",
        queryset=ExpenditureObject.objects.none(),
        help_text="Su regla de capitalización determina automáticamente BM o BP.",
    )
    accounting_account = forms.ModelChoiceField(
        label="Cuenta contable",
        queryset=AccountingAccount.objects.none(),
        required=False,
        help_text="Cuenta patrimonial utilizada para conciliación con SIGMAVER.",
    )
    acquisition_type = forms.ChoiceField(
        label="Tipo de adquisición",
        choices=AcquisitionType.choices,
    )
    acquisition_date = forms.DateField(
        label="Fecha de adquisición",
        widget=DATE_WIDGET,
        help_text="Fecha de factura o documento que acredita la adquisición.",
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
        help_text="El sistema comparará este importe contra la regla UMA vigente para calcular BM o BP.",
    )
    residual_value = forms.DecimalField(
        label="Valor residual o de desecho",
        min_value=0,
        max_digits=16,
        decimal_places=2,
        initial=0,
    )
    manufacturer = forms.ModelChoiceField(
        label="Fabricante",
        queryset=Manufacturer.objects.none(),
        required=False,
    )
    model = forms.ModelChoiceField(
        label="Modelo",
        queryset=AssetModel.objects.none(),
        required=False,
    )
    serial_number = forms.CharField(
        label="Número de serie o Service Tag",
        max_length=120,
        required=False,
    )
    supplier = forms.ModelChoiceField(
        label="Proveedor",
        queryset=Supplier.objects.none(),
        required=False,
    )
    contract = forms.ModelChoiceField(
        label="Contrato u orden de compra",
        queryset=Contract.objects.none(),
        required=False,
    )
    requested_site_id = UUIDChoiceField(
        label="Sede física",
        help_text="Edificio o sede donde se ubicará inicialmente el bien.",
    )
    requested_department_id = UUIDChoiceField(
        label="Dependencia responsable",
        help_text="Dependencia que recibirá y administrará el bien.",
    )
    requested_area_id = UUIDChoiceField(
        label="Área operativa",
        help_text="Se muestra como dependencia → área [sede] para evitar ambigüedades.",
    )
    proposed_custodian_id = UUIDChoiceField(
        label="Resguardatario propuesto",
        required=False,
        help_text="Servidor público que recibirá inicialmente el resguardo.",
    )
    notes = forms.CharField(
        label="Notas internas",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Observaciones internas del expediente de alta.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        active = {"is_active": True, "is_deleted": False}
        self.fields["category"].queryset = AssetCategory.objects.filter(**active).order_by("name")
        self.fields["proposed_asset_type"].queryset = InventoryAssetType.objects.filter(
            **active,
            allows_user_proposal=True,
        ).order_by("nature", "code")
        self.fields["expenditure_object"].queryset = ExpenditureObject.objects.filter(**active).order_by("code")
        self.fields["accounting_account"].queryset = AccountingAccount.objects.filter(**active).order_by("code")
        self.fields["manufacturer"].queryset = Manufacturer.objects.filter(**active).order_by("name")
        self.fields["model"].queryset = AssetModel.objects.filter(**active).select_related("manufacturer").order_by("manufacturer__name", "name")
        self.fields["supplier"].queryset = Supplier.objects.filter(**active).order_by("razon_social")
        self.fields["contract"].queryset = Contract.objects.filter(**active).select_related("supplier").order_by("-fecha_inicio")

    def clean(self):
        data = super().clean()
        if data.get("residual_value") is not None and data.get("acquisition_cost") is not None:
            if data["residual_value"] > data["acquisition_cost"]:
                self.add_error("residual_value", "No puede superar el costo de adquisición.")
        if data.get("reception_date") and data.get("acquisition_date"):
            if data["reception_date"] < data["acquisition_date"]:
                self.add_error("reception_date", "No puede ser anterior a la adquisición.")
        model = data.get("model")
        manufacturer = data.get("manufacturer")
        if model and manufacturer and model.manufacturer_id != manufacturer.id:
            self.add_error("model", "El modelo no pertenece al fabricante.")
        contract = data.get("contract")
        supplier = data.get("supplier")
        if contract and supplier and contract.supplier_id != supplier.id:
            self.add_error("contract", "El contrato no pertenece al proveedor.")
        proposed_type = data.get("proposed_asset_type")
        category = data.get("category")
        if proposed_type and category and proposed_type.nature != category.nature:
            self.add_error(
                "proposed_asset_type",
                "El tipo propuesto no corresponde a la naturaleza de la categoría.",
            )

        site_id = data.get("requested_site_id")
        department_id = data.get("requested_department_id")
        area_id = data.get("requested_area_id")
        custodian_id = data.get("proposed_custodian_id")

        if area_id:
            from apps.inventory.integrations.core_directory import (
                CoreDirectoryError,
                get_area_context,
            )

            try:
                area_context = get_area_context(area_id)
            except CoreDirectoryError as exc:
                self.add_error("requested_area_id", str(exc))
            else:
                if department_id and area_context.department_id != department_id:
                    self.add_error(
                        "requested_area_id",
                        "El área no pertenece a la dependencia seleccionada.",
                    )
                if site_id and area_context.site_id != site_id:
                    self.add_error(
                        "requested_area_id",
                        "El área no pertenece a la sede seleccionada.",
                    )

        if custodian_id and area_id:
            from apps.inventory.integrations.core_directory import (
                CoreDirectoryError,
                get_user_organizational_context,
            )

            try:
                user_context = get_user_organizational_context(
                    custodian_id,
                    require_profile=True,
                )
            except CoreDirectoryError as exc:
                self.add_error("proposed_custodian_id", str(exc))
            else:
                if user_context.area_id != area_id:
                    self.add_error(
                        "proposed_custodian_id",
                        "El resguardatario no está adscrito al área seleccionada.",
                    )
        return data

    def _dto_kwargs(self):
        d = self.require_cleaned_data()
        return {
            "name": d["name"], "description": d.get("description", ""),
            "category_id": d["category"].id,
            "proposed_asset_type_id": (
                d["proposed_asset_type"].id
                if d.get("proposed_asset_type") else None
            ),
            "expenditure_object_id": d["expenditure_object"].id if d.get("expenditure_object") else None,
            "accounting_account_id": d["accounting_account"].id if d.get("accounting_account") else None,
            "acquisition_type": d["acquisition_type"], "acquisition_date": d.get("acquisition_date"),
            "reception_date": d.get("reception_date"), "acquisition_cost": d["acquisition_cost"],
            "residual_value": d["residual_value"],
            "manufacturer_id": d["manufacturer"].id if d.get("manufacturer") else None,
            "model_id": d["model"].id if d.get("model") else None,
            "serial_number": d.get("serial_number") or None,
            "supplier_id": d["supplier"].id if d.get("supplier") else None,
            "contract_id": d["contract"].id if d.get("contract") else None,
            "requested_department_id": d["requested_department_id"],
            "requested_site_id": d.get("requested_site_id"), "requested_area_id": d.get("requested_area_id"),
            "proposed_custodian_id": d.get("proposed_custodian_id"), "notes": d.get("notes", ""),
        }


class AssetIntakeCreateForm(AssetIntakeBaseForm):
    def to_dto(self): return CreateAssetIntakeDTO(**self._dto_kwargs())


class AssetIntakeUpdateForm(AssetIntakeBaseForm):
    def to_dto(self): return UpdateAssetIntakeDTO(**self._dto_kwargs())


class DepartmentIntakeDecisionForm(InventoryForm):
    approve = forms.BooleanField(label="Aprobar solicitud", required=False)
    comment = forms.CharField(label="Comentario o motivo del rechazo", required=False, widget=forms.Textarea(attrs={"rows": 3}))
    bypass_reason = forms.CharField(label="Justificación de excepción", required=False, widget=forms.Textarea(attrs={"rows": 2}))
    def clean(self):
        d = super().clean()
        if not d.get("approve") and not str(d.get("comment", "")).strip():
            self.add_error("comment", "Indique el motivo del rechazo.")
        return d
    def to_dto(self):
        d = self.require_cleaned_data(); return DepartmentIntakeDecisionDTO(d["approve"], d.get("comment", ""), d.get("bypass_reason", ""))


class PatrimonyApprovalForm(InventoryForm):
    expenditure_object = forms.ModelChoiceField(label="Clasificador por objeto del gasto (CONAC)", queryset=ExpenditureObject.objects.none())
    accounting_account = forms.ModelChoiceField(label="Cuenta contable", queryset=AccountingAccount.objects.none(), required=False)
    physical_condition = forms.ChoiceField(label="Condición física", choices=PhysicalCondition.choices, initial=PhysicalCondition.GOOD)
    residual_value = forms.DecimalField(label="Valor residual o de desecho", required=False, min_value=0, max_digits=16, decimal_places=2)
    useful_life_months = forms.IntegerField(label="Vida útil en meses", required=False, min_value=1)
    observation = forms.CharField(label="Observaciones de validación patrimonial", required=False, widget=forms.Textarea(attrs={"rows": 3}))
    bypass_reason = forms.CharField(label="Justificación de excepción", required=False, widget=forms.Textarea(attrs={"rows": 2}))
    authorized_asset_type = forms.ModelChoiceField(
        label="Tipo patrimonial autorizado",
        queryset=InventoryAssetType.objects.none(),
        required=False,
        help_text="Si se deja vacío, se utilizará el tipo calculado por el sistema.",
    )
    classification_override_reason = forms.CharField(
        label="Justificación de clasificación diferente",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs); active={"is_active":True,"is_deleted":False}
        self.fields["expenditure_object"].queryset=ExpenditureObject.objects.filter(**active).order_by("code")
        self.fields["accounting_account"].queryset=AccountingAccount.objects.filter(**active).order_by("code")
        self.fields["authorized_asset_type"].queryset = InventoryAssetType.objects.filter(
            **active,
        ).order_by("nature", "code")
    def to_dto(self):
        d=self.require_cleaned_data(); return PatrimonyApprovalDTO(
            expenditure_object_id=d["expenditure_object"].id,
            accounting_account_id=d["accounting_account"].id if d.get("accounting_account") else None,
            physical_condition=d["physical_condition"],
            residual_value=d.get("residual_value"),
            useful_life_months=d.get("useful_life_months"),
            observation=d.get("observation", ""),
            authorized_asset_type_id=(
                d["authorized_asset_type"].id
                if d.get("authorized_asset_type") else None
            ),
            classification_override_reason=d.get("classification_override_reason", ""),
        )


class PatrimonyObservationForm(InventoryForm):
    observation = forms.CharField(label="Observación patrimonial", widget=forms.Textarea(attrs={"rows": 4}))
    def to_dto(self): return PatrimonyObservationDTO(self.require_cleaned_data()["observation"])


class CancelAssetIntakeForm(InventoryForm):
    reason = forms.CharField(label="Motivo de cancelación", widget=forms.Textarea(attrs={"rows": 3}))
    bypass_reason = forms.CharField(label="Justificación de excepción", required=False, widget=forms.Textarea(attrs={"rows": 2}))
    def to_dto(self):
        d=self.require_cleaned_data(); return CancelAssetIntakeDTO(d["reason"], d.get("bypass_reason", ""))


__all__ = [name for name in globals() if name.endswith("Form") and not name.endswith("BaseForm")]
