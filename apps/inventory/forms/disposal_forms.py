from django import forms
from django.utils import timezone
from apps.inventory.dtos import CancelDisposalDTO, CreateDisposalRequestDTO, ExecuteDisposalDTO, ExternalReferenceDTO, FinalizeDisposalApprovalDTO, ResolveDisposalStageDTO, SubmitDisposalRequestDTO
from apps.inventory.forms.base_forms import DATETIME_WIDGET, InventoryForm
from apps.inventory.models import DisposalApprovalDecision, DisposalApprovalStage, DisposalReason, DocumentType


class DisposalRequestCreateForm(InventoryForm):
    asset_id=forms.UUIDField(); reason=forms.ChoiceField(choices=DisposalReason.choices); description=forms.CharField(widget=forms.Textarea(attrs={"rows":4})); legal_reference=forms.CharField(required=False,widget=forms.Textarea(attrs={"rows":2})); technical_report_required=forms.BooleanField(required=False); required_document_types=forms.MultipleChoiceField(required=False,choices=DocumentType.choices)
    source_app=forms.CharField(required=False,max_length=80); source_model=forms.CharField(required=False,max_length=120); source_object_id=forms.UUIDField(required=False); source_folio=forms.CharField(required=False,max_length=120)
    def clean(self):
        d=super().clean(); parts=[d.get("source_app"),d.get("source_model"),d.get("source_object_id")]
        if any(parts) and not all(parts): raise forms.ValidationError("La referencia externa debe incluir app, modelo y UUID.")
        return d
    def to_dto(self):
        d=self.require_cleaned_data(); ref=ExternalReferenceDTO(d["source_app"],d["source_model"],d["source_object_id"],d.get("source_folio", "")) if d.get("source_object_id") else None
        return CreateDisposalRequestDTO(d["asset_id"],d["reason"],d["description"],d.get("legal_reference", ""),d.get("technical_report_required",False),tuple(d.get("required_document_types",[])),ref)


class DisposalSubmitForm(InventoryForm):
    comment=forms.CharField(required=False,widget=forms.Textarea(attrs={"rows":3}))
    def to_dto(self): return SubmitDisposalRequestDTO(self.require_cleaned_data().get("comment", ""))


class DisposalStageResolutionForm(InventoryForm):
    stage=forms.ChoiceField(choices=DisposalApprovalStage.choices); decision=forms.ChoiceField(choices=DisposalApprovalDecision.choices); comment=forms.CharField(widget=forms.Textarea(attrs={"rows":3})); bypass_reason=forms.CharField(required=False)
    def to_dto(self): d=self.require_cleaned_data(); return ResolveDisposalStageDTO(d["stage"],d["decision"],d["comment"],d.get("bypass_reason", ""))


class DisposalFinalApprovalForm(InventoryForm):
    approve=forms.BooleanField(required=False); comment=forms.CharField(widget=forms.Textarea(attrs={"rows":3})); bypass_reason=forms.CharField(required=False)
    def to_dto(self): d=self.require_cleaned_data(); return FinalizeDisposalApprovalDTO(d.get("approve",False),d["comment"],d.get("bypass_reason", ""))


class DisposalExecuteForm(InventoryForm):
    executed_at=forms.DateTimeField(widget=DATETIME_WIDGET,initial=timezone.now); execution_notes=forms.CharField(widget=forms.Textarea(attrs={"rows":4})); bypass_reason=forms.CharField(required=False)
    def to_dto(self): d=self.require_cleaned_data(); return ExecuteDisposalDTO(d["executed_at"],d["execution_notes"],d.get("bypass_reason", ""))


class DisposalCancelForm(InventoryForm):
    reason=forms.CharField(widget=forms.Textarea(attrs={"rows":3})); bypass_reason=forms.CharField(required=False)
    def to_dto(self): d=self.require_cleaned_data(); return CancelDisposalDTO(d["reason"],d.get("bypass_reason", ""))


__all__=[name for name in globals() if name.startswith("Disposal") and name.endswith("Form")]
