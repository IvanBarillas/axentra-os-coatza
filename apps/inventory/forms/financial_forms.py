from django import forms
from django.utils import timezone
from apps.inventory.dtos import CalculateDepreciationDTO, CloseDepreciationPolicyDTO, CloseReconciliationDTO, CompleteDepreciationRunDTO, CreateAccountingExportDTO, CreateDepreciationPolicyDTO, CreateDepreciationRunDTO, CreateReconciliationDTO, PostDepreciationRunDTO, ProcessReconciliationDTO, ReviewReconciliationItemDTO
from apps.inventory.forms.base_forms import DATE_WIDGET, DATETIME_WIDGET, InventoryForm
from apps.inventory.models import AccountingAccount, AccountingExportBatch, AssetCategory, DepreciationFrequency, DepreciationMethod
from apps.inventory.models.financial_models import (
    AccountingExportFormat,
    ReconciliationItemResult,
)


class DepreciationRunCreateForm(InventoryForm):
    frequency=forms.ChoiceField(label="Frecuencia", choices=DepreciationFrequency.choices); period_year=forms.IntegerField(label="Ejercicio", min_value=2000,max_value=9999); period_month=forms.IntegerField(label="Mes", required=False,min_value=1,max_value=12); period_start=forms.DateField(label="Inicio del periodo", widget=DATE_WIDGET); period_end=forms.DateField(label="Fin del periodo", widget=DATE_WIDGET); cutoff_at=forms.DateTimeField(label="Fecha y hora de corte", widget=DATETIME_WIDGET,initial=timezone.now); notes=forms.CharField(label="Notas", required=False,widget=forms.Textarea(attrs={"rows":3}))
    def clean(self):
        d=super().clean()
        if d.get("period_start") and d.get("period_end") and d["period_end"]<d["period_start"]: self.add_error("period_end","No puede ser anterior al inicio.")
        if d.get("frequency")==DepreciationFrequency.MONTHLY and not d.get("period_month"): self.add_error("period_month","El mes es obligatorio para frecuencia mensual.")
        return d
    def to_dto(self): d=self.require_cleaned_data(); return CreateDepreciationRunDTO(d["frequency"],d["period_year"],d["period_start"],d["period_end"],d["cutoff_at"],d.get("period_month"),d.get("notes", ""))


class DepreciationPolicyCreateForm(InventoryForm):
    policy_code = forms.CharField(label="Código de política", max_length=50)
    name = forms.CharField(label="Nombre de la política", max_length=180)
    accounting_account = forms.ModelChoiceField(label="Cuenta contable depreciable", queryset=AccountingAccount.objects.none())
    category = forms.ModelChoiceField(label="Categoría específica", queryset=AssetCategory.objects.none(), required=False, help_text="Déjela vacía para aplicar a cualquier categoría de la cuenta.")
    method = forms.ChoiceField(label="Método", choices=DepreciationMethod.choices)
    frequency = forms.ChoiceField(label="Frecuencia", choices=DepreciationFrequency.choices)
    useful_life_months = forms.IntegerField(label="Vida útil en meses", min_value=1)
    residual_percentage = forms.DecimalField(label="Porcentaje residual", min_value=0, max_value=100, max_digits=6, decimal_places=3)
    effective_from = forms.DateField(label="Vigente desde", widget=DATE_WIDGET)
    effective_until = forms.DateField(label="Vigente hasta", widget=DATE_WIDGET, required=False)
    source_reference = forms.CharField(label="Referencia normativa o técnica", required=False, max_length=255)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        active = {"is_active": True, "is_deleted": False}
        self.fields["accounting_account"].queryset = AccountingAccount.objects.filter(**active, is_depreciable=True).order_by("code")
        self.fields["category"].queryset = AssetCategory.objects.filter(**active).order_by("name")

    def clean(self):
        data = super().clean()
        if data.get("effective_until") and data.get("effective_from") and data["effective_until"] < data["effective_from"]:
            self.add_error("effective_until", "No puede ser anterior al inicio de vigencia.")
        account = data.get("accounting_account"); category = data.get("category")
        if account and category and account.category_id and account.category_id != category.id:
            self.add_error("category", "La categoría no corresponde a la cuenta contable seleccionada.")
        return data

    def to_dto(self):
        d = self.require_cleaned_data()
        return CreateDepreciationPolicyDTO(d["policy_code"], d["name"], d["accounting_account"].id, d["category"].id if d.get("category") else None, d["method"], d["frequency"], d["useful_life_months"], d["residual_percentage"], d["effective_from"], d.get("effective_until"), d.get("source_reference", ""))


class DepreciationPolicyCloseForm(InventoryForm):
    effective_until = forms.DateField(label="Último día de vigencia", widget=DATE_WIDGET)
    reason = forms.CharField(label="Motivo del cierre", widget=forms.Textarea(attrs={"rows": 3}))

    def to_dto(self):
        d = self.require_cleaned_data(); return CloseDepreciationPolicyDTO(d["effective_until"], d["reason"])


class DepreciationCalculateForm(InventoryForm):
    run_id=forms.UUIDField(); asset_ids=forms.CharField(required=False,help_text="UUID separados por coma."); recalculate=forms.BooleanField(required=False)
    def clean_asset_ids(self):
        from uuid import UUID
        raw=self.cleaned_data.get("asset_ids",""); result=[]
        for value in filter(None,(item.strip() for item in raw.split(","))):
            try: result.append(UUID(value))
            except ValueError: raise forms.ValidationError(f"UUID inválido: {value}")
        return tuple(result)
    def to_dto(self): d=self.require_cleaned_data(); return CalculateDepreciationDTO(d["run_id"],d.get("asset_ids",()),d.get("recalculate",False))


class DepreciationCompleteForm(InventoryForm):
    notes=forms.CharField(required=False,widget=forms.Textarea(attrs={"rows":3}))
    def to_dto(self): return CompleteDepreciationRunDTO(self.require_cleaned_data().get("notes", ""))


class DepreciationPostForm(InventoryForm):
    posting_reference=forms.CharField(label="Referencia contable", max_length=120); notes=forms.CharField(label="Notas de aplicación", required=False,widget=forms.Textarea(attrs={"rows":3})); bypass_reason=forms.CharField(label="Justificación extraordinaria", required=False)
    def to_dto(self): d=self.require_cleaned_data(); return PostDepreciationRunDTO(d["posting_reference"],d.get("notes", ""),d.get("bypass_reason", ""))


class AccountingExportCreateForm(InventoryForm):
    export_type=forms.ChoiceField(label="Tipo de reporte", choices=AccountingExportBatch.ExportType.choices); file_format=forms.ChoiceField(label="Formato", choices=[(AccountingExportFormat.CSV, "Archivo CSV")], initial=AccountingExportFormat.CSV); destination_system=forms.CharField(label="Sistema destino", max_length=120,initial="SIGMAVER"); period_start=forms.DateField(label="Inicio del periodo", widget=DATE_WIDGET); period_end=forms.DateField(label="Fin del periodo", widget=DATE_WIDGET); cutoff_at=forms.DateTimeField(label="Fecha y hora de corte", widget=DATETIME_WIDGET,initial=timezone.now)
    def clean(self):
        d=super().clean()
        if d.get("period_start") and d.get("period_end") and d["period_end"]<d["period_start"]: self.add_error("period_end","No puede ser anterior al inicio.")
        return d
    def to_dto(self): d=self.require_cleaned_data(); return CreateAccountingExportDTO(d["export_type"],d["file_format"],d["destination_system"],d["period_start"],d["period_end"],d["cutoff_at"])


class ReconciliationCreateForm(InventoryForm):
    source_system=forms.CharField(label="Sistema contable origen", max_length=120,initial="SIGMAVER"); period_start=forms.DateField(label="Inicio del periodo", widget=DATE_WIDGET); period_end=forms.DateField(label="Fin del periodo", widget=DATE_WIDGET); cutoff_at=forms.DateTimeField(label="Fecha y hora de corte de Inventory", widget=DATETIME_WIDGET,initial=timezone.now); source_file=forms.FileField(label="Balanza o archivo fuente")
    def clean(self):
        d=super().clean()
        if d.get("period_start") and d.get("period_end") and d["period_end"] < d["period_start"]: self.add_error("period_end", "No puede ser anterior al inicio.")
        return d
    def to_dto(self): d=self.require_cleaned_data(); f=d["source_file"]; return CreateReconciliationDTO(d["source_system"],d["period_start"],d["period_end"],d["cutoff_at"],f,f.name)


class ReconciliationProcessForm(InventoryForm):
    account_code_column=forms.CharField(initial="cuenta"); amount_column=forms.CharField(initial="saldo")
    def to_dto(self): d=self.require_cleaned_data(); return ProcessReconciliationDTO({"account_code":d["account_code_column"],"amount":d["amount_column"]})


class ReconciliationItemReviewForm(InventoryForm):
    result=forms.ChoiceField(choices=ReconciliationItemResult.choices); review_notes=forms.CharField(widget=forms.Textarea(attrs={"rows":3}))
    def to_dto(self): d=self.require_cleaned_data(); return ReviewReconciliationItemDTO(d["result"],d["review_notes"])


class ReconciliationCloseForm(InventoryForm):
    closing_notes=forms.CharField(widget=forms.Textarea(attrs={"rows":5})); bypass_reason=forms.CharField(required=False)
    def to_dto(self): d=self.require_cleaned_data(); return CloseReconciliationDTO(d["closing_notes"],d.get("bypass_reason", ""))


__all__=[name for name in globals() if name.endswith("Form") and name != "InventoryForm"]
