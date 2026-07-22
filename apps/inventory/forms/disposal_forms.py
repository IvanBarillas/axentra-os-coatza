from django import forms
from django.utils import timezone
from apps.inventory.dtos import CancelDisposalDTO, CreateDisposalRequestDTO, ExecuteDisposalDTO, ExternalReferenceDTO, FinalizeDisposalApprovalDTO, ResolveDisposalStageDTO, SubmitDisposalRequestDTO
from apps.inventory.forms.base_forms import DATETIME_WIDGET, InventoryForm, UUIDChoiceField
from apps.inventory.models import DisposalApprovalDecision, DisposalApprovalStage, DisposalReason, DocumentType


class DisposalRequestCreateForm(InventoryForm):
    asset_id=UUIDChoiceField(label="Bien patrimonial")
    reason=forms.ChoiceField(label="Motivo de la baja", choices=DisposalReason.choices)
    description=forms.CharField(label="Justificación detallada", widget=forms.Textarea(attrs={"rows":4}))
    legal_reference=forms.CharField(label="Fundamento u oficio de referencia", required=False,widget=forms.Textarea(attrs={"rows":2}))
    def clean(self):
        d=super().clean()
        reason=d.get("reason")
        documents=[]
        technical=reason in {DisposalReason.OBSOLESCENCE, DisposalReason.IRREPARABLE_DAMAGE, DisposalReason.DISASTER, DisposalReason.SCRAP}
        if technical: documents.append(DocumentType.TECHNICAL_REPORT)
        if reason in {DisposalReason.THEFT, DisposalReason.LOSS}: documents.append(DocumentType.POLICE_REPORT)
        if reason in {DisposalReason.SCRAP, DisposalReason.DONATION, DisposalReason.SALE, DisposalReason.DESTRUCTION, DisposalReason.LEGAL_DISINCORPORATION}:
            documents.extend([DocumentType.COUNCIL_MINUTES, DocumentType.DISINCORPORATION_AUTHORIZATION])
        d["technical_report_required"]=technical
        d["required_document_types"]=tuple(dict.fromkeys(documents))
        return d
    def to_dto(self):
        d=self.require_cleaned_data(); ref=None
        return CreateDisposalRequestDTO(d["asset_id"],d["reason"],d["description"],d.get("legal_reference", ""),d.get("technical_report_required",False),tuple(d.get("required_document_types",[])),ref)


class DisposalSubmitForm(InventoryForm):
    comment=forms.CharField(label="Comentario de envío", required=False,widget=forms.Textarea(attrs={"rows":3}))
    def to_dto(self): return SubmitDisposalRequestDTO(self.require_cleaned_data().get("comment", ""))


class DisposalStageResolutionForm(InventoryForm):
    stage=forms.ChoiceField(label="Etapa", choices=DisposalApprovalStage.choices); decision=forms.ChoiceField(label="Decisión", choices=DisposalApprovalDecision.choices); comment=forms.CharField(label="Justificación", widget=forms.Textarea(attrs={"rows":3})); bypass_reason=forms.CharField(label="Motivo de excepción", required=False)
    def to_dto(self): d=self.require_cleaned_data(); return ResolveDisposalStageDTO(d["stage"],d["decision"],d["comment"],d.get("bypass_reason", ""))


class DisposalFinalApprovalForm(InventoryForm):
    approve=forms.BooleanField(label="Autorizar la baja", required=False); comment=forms.CharField(label="Justificación de la decisión", widget=forms.Textarea(attrs={"rows":3})); bypass_reason=forms.CharField(label="Motivo de excepción", required=False)
    def to_dto(self): d=self.require_cleaned_data(); return FinalizeDisposalApprovalDTO(d.get("approve",False),d["comment"],d.get("bypass_reason", ""))


class DisposalExecuteForm(InventoryForm):
    executed_at=forms.DateTimeField(label="Fecha efectiva de la baja", widget=DATETIME_WIDGET,initial=timezone.now); execution_notes=forms.CharField(label="Acta, destino y observaciones finales", widget=forms.Textarea(attrs={"rows":4})); bypass_reason=forms.CharField(label="Motivo de excepción", required=False)
    def to_dto(self): d=self.require_cleaned_data(); return ExecuteDisposalDTO(d["executed_at"],d["execution_notes"],d.get("bypass_reason", ""))


class DisposalCancelForm(InventoryForm):
    reason=forms.CharField(label="Motivo de cancelación", widget=forms.Textarea(attrs={"rows":3})); bypass_reason=forms.CharField(label="Motivo de excepción", required=False)
    def to_dto(self): d=self.require_cleaned_data(); return CancelDisposalDTO(d["reason"],d.get("bypass_reason", ""))


__all__=[name for name in globals() if name.startswith("Disposal") and name.endswith("Form")]
