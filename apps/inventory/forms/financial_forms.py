from django import forms
from django.utils import timezone
from apps.inventory.dtos import CalculateDepreciationDTO, CloseReconciliationDTO, CompleteDepreciationRunDTO, CreateAccountingExportDTO, CreateDepreciationRunDTO, CreateReconciliationDTO, PostDepreciationRunDTO, ProcessReconciliationDTO, ReviewReconciliationItemDTO
from apps.inventory.forms.base_forms import DATE_WIDGET, DATETIME_WIDGET, InventoryForm
from apps.inventory.models import AccountingExportBatch, DepreciationFrequency
from apps.inventory.models.financial_models import (
    AccountingExportFormat,
    ReconciliationItemResult,
)


class DepreciationRunCreateForm(InventoryForm):
    frequency=forms.ChoiceField(choices=DepreciationFrequency.choices); period_year=forms.IntegerField(min_value=2000,max_value=9999); period_month=forms.IntegerField(required=False,min_value=1,max_value=12); period_start=forms.DateField(widget=DATE_WIDGET); period_end=forms.DateField(widget=DATE_WIDGET); cutoff_at=forms.DateTimeField(widget=DATETIME_WIDGET,initial=timezone.now); notes=forms.CharField(required=False,widget=forms.Textarea(attrs={"rows":3}))
    def clean(self):
        d=super().clean()
        if d.get("period_start") and d.get("period_end") and d["period_end"]<d["period_start"]: self.add_error("period_end","No puede ser anterior al inicio.")
        if d.get("frequency")==DepreciationFrequency.MONTHLY and not d.get("period_month"): self.add_error("period_month","El mes es obligatorio para frecuencia mensual.")
        return d
    def to_dto(self): d=self.require_cleaned_data(); return CreateDepreciationRunDTO(d["frequency"],d["period_year"],d["period_start"],d["period_end"],d["cutoff_at"],d.get("period_month"),d.get("notes", ""))


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
    posting_reference=forms.CharField(max_length=120); notes=forms.CharField(required=False,widget=forms.Textarea(attrs={"rows":3})); bypass_reason=forms.CharField(required=False)
    def to_dto(self): d=self.require_cleaned_data(); return PostDepreciationRunDTO(d["posting_reference"],d.get("notes", ""),d.get("bypass_reason", ""))


class AccountingExportCreateForm(InventoryForm):
    export_type=forms.ChoiceField(choices=AccountingExportBatch.ExportType.choices); file_format=forms.ChoiceField(choices=AccountingExportFormat.choices); destination_system=forms.CharField(max_length=120,initial="SIGMAVER"); period_start=forms.DateField(widget=DATE_WIDGET); period_end=forms.DateField(widget=DATE_WIDGET); cutoff_at=forms.DateTimeField(widget=DATETIME_WIDGET,initial=timezone.now)
    def clean(self):
        d=super().clean()
        if d.get("period_start") and d.get("period_end") and d["period_end"]<d["period_start"]: self.add_error("period_end","No puede ser anterior al inicio.")
        return d
    def to_dto(self): d=self.require_cleaned_data(); return CreateAccountingExportDTO(d["export_type"],d["file_format"],d["destination_system"],d["period_start"],d["period_end"],d["cutoff_at"])


class ReconciliationCreateForm(InventoryForm):
    source_system=forms.CharField(max_length=120,initial="SIGMAVER"); period_start=forms.DateField(widget=DATE_WIDGET); period_end=forms.DateField(widget=DATE_WIDGET); cutoff_at=forms.DateTimeField(widget=DATETIME_WIDGET,initial=timezone.now); source_file=forms.FileField()
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
