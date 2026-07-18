from django import forms
from django.utils import timezone
from apps.inventory.dtos import AcceptCustodyAssignmentDTO, AuthorizeCustodyAssignmentDTO, CancelCustodyAssignmentDTO, CreateCustodyAssignmentDTO, RejectCustodyAssignmentDTO, ReturnCustodyAssignmentDTO
from apps.inventory.forms.base_forms import DATETIME_WIDGET, InventoryForm, UUIDChoiceField
from apps.inventory.models import CustodyAcceptanceMethod, PhysicalCondition


class CustodyCreateForm(InventoryForm):
    asset_id=UUIDChoiceField(); assigned_to_id=UUIDChoiceField(); department_id=UUIDChoiceField(); area_id=UUIDChoiceField(required=False); site_id=UUIDChoiceField(required=False)
    assigned_at=forms.DateTimeField(widget=DATETIME_WIDGET,initial=timezone.now); notes=forms.CharField(required=False,widget=forms.Textarea(attrs={"rows":3})); bypass_reason=forms.CharField(required=False,widget=forms.Textarea(attrs={"rows":2}))
    def to_dto(self):
        d=self.require_cleaned_data(); return CreateCustodyAssignmentDTO(d["asset_id"],d["assigned_to_id"],d["department_id"],d["assigned_at"],d.get("area_id"),d.get("site_id"),d.get("notes", ""),d.get("bypass_reason", ""))


class CustodyAuthorizeForm(InventoryForm):
    comment=forms.CharField(required=False,widget=forms.Textarea(attrs={"rows":3})); bypass_reason=forms.CharField(required=False)
    def to_dto(self): d=self.require_cleaned_data(); return AuthorizeCustodyAssignmentDTO(d.get("comment", ""),d.get("bypass_reason", ""))


class CustodyAcceptForm(InventoryForm):
    acceptance_method=forms.ChoiceField(choices=CustodyAcceptanceMethod.choices); signature_hash=forms.CharField(required=False,max_length=255); comment=forms.CharField(required=False,widget=forms.Textarea(attrs={"rows":3}))
    def to_dto(self): d=self.require_cleaned_data(); return AcceptCustodyAssignmentDTO(d["acceptance_method"],d.get("signature_hash", ""),d.get("comment", ""))


class CustodyRejectForm(InventoryForm):
    reason=forms.CharField(widget=forms.Textarea(attrs={"rows":3}))
    def to_dto(self): return RejectCustodyAssignmentDTO(self.require_cleaned_data()["reason"])


class CustodyReturnForm(InventoryForm):
    returned_at=forms.DateTimeField(widget=DATETIME_WIDGET,initial=timezone.now); physical_condition=forms.ChoiceField(choices=PhysicalCondition.choices); notes=forms.CharField(required=False,widget=forms.Textarea(attrs={"rows":3}))
    def to_dto(self): d=self.require_cleaned_data(); return ReturnCustodyAssignmentDTO(d["returned_at"],d["physical_condition"],d.get("notes", ""))


class CustodyCancelForm(InventoryForm):
    reason=forms.CharField(widget=forms.Textarea(attrs={"rows":3})); bypass_reason=forms.CharField(required=False)
    def to_dto(self): d=self.require_cleaned_data(); return CancelCustodyAssignmentDTO(d["reason"],d.get("bypass_reason", ""))


__all__=[name for name in globals() if name.startswith("Custody") and name.endswith("Form")]
