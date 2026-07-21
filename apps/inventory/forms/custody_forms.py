from django import forms
from django.utils import timezone
from apps.inventory.dtos import AcceptCustodyAssignmentDTO, AuthorizeCustodyAssignmentDTO, CancelCustodyAssignmentDTO, CreateCustodyAssignmentDTO, RejectCustodyAssignmentDTO, ReturnCustodyAssignmentDTO
from apps.inventory.forms.base_forms import DATETIME_WIDGET, InventoryForm, UUIDChoiceField
from apps.inventory.models import CustodyAcceptanceMethod, PhysicalCondition


class CustodyCreateForm(InventoryForm):
    asset_id=UUIDChoiceField(label="Bien patrimonial")
    site_id=UUIDChoiceField(label="Sede física")
    department_id=UUIDChoiceField(label="Dependencia")
    area_id=UUIDChoiceField(label="Área operativa", required=False)
    assigned_to_id=UUIDChoiceField(
        label="Servidor público resguardatario",
        help_text="Se muestran únicamente servidores adscritos a la dependencia y área seleccionadas.",
    )
    notes=forms.CharField(label="Notas internas", required=False,widget=forms.Textarea(attrs={"rows":3}))
    bypass_reason=forms.CharField(label="Justificación del bypass", required=False,widget=forms.Textarea(attrs={"rows":2}))
    def to_dto(self):
        d=self.require_cleaned_data(); return CreateCustodyAssignmentDTO(d["asset_id"],d["assigned_to_id"],d["department_id"],timezone.now(),d.get("area_id"),d.get("site_id"),d.get("notes", ""),d.get("bypass_reason", ""))


class CustodyAuthorizeForm(InventoryForm):
    comment=forms.CharField(label="Comentario de autorización",required=False,widget=forms.Textarea(attrs={"rows":3})); bypass_reason=forms.CharField(label="Justificación del bypass",required=False)
    def to_dto(self): d=self.require_cleaned_data(); return AuthorizeCustodyAssignmentDTO(d.get("comment", ""),d.get("bypass_reason", ""))


class CustodyAcceptForm(InventoryForm):
    acceptance_method=forms.ChoiceField(label="Método de aceptación",choices=CustodyAcceptanceMethod.choices); signature_hash=forms.CharField(label="Hash de firma digital",required=False,max_length=255); comment=forms.CharField(label="Comentario",required=False,widget=forms.Textarea(attrs={"rows":3}))
    def to_dto(self): d=self.require_cleaned_data(); return AcceptCustodyAssignmentDTO(d["acceptance_method"],d.get("signature_hash", ""),d.get("comment", ""))


class CustodyRejectForm(InventoryForm):
    reason=forms.CharField(label="Motivo del rechazo",widget=forms.Textarea(attrs={"rows":3}))
    def to_dto(self): return RejectCustodyAssignmentDTO(self.require_cleaned_data()["reason"])


class CustodyReturnForm(InventoryForm):
    returned_at=forms.DateTimeField(label="Fecha de devolución",widget=DATETIME_WIDGET,initial=timezone.now); physical_condition=forms.ChoiceField(label="Condición física al devolver",choices=PhysicalCondition.choices); notes=forms.CharField(label="Observaciones de devolución",required=False,widget=forms.Textarea(attrs={"rows":3}))
    def to_dto(self): d=self.require_cleaned_data(); return ReturnCustodyAssignmentDTO(d["returned_at"],d["physical_condition"],d.get("notes", ""))


class CustodyCancelForm(InventoryForm):
    reason=forms.CharField(label="Motivo de cancelación",widget=forms.Textarea(attrs={"rows":3})); bypass_reason=forms.CharField(label="Justificación del bypass",required=False)
    def to_dto(self): d=self.require_cleaned_data(); return CancelCustodyAssignmentDTO(d["reason"],d.get("bypass_reason", ""))


class CustodyDeliverForm(InventoryForm):
    comment=forms.CharField(label="Observaciones de la entrega física",required=False,widget=forms.Textarea(attrs={"rows":3}))


__all__=[name for name in globals() if name.startswith("Custody") and name.endswith("Form")]
