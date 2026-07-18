from django import forms
from django.utils import timezone
from apps.inventory.dtos import AuthorizeAssetLoanDTO, CancelAssetLoanDTO, CreateAssetLoanDTO, DeliverAssetLoanDTO, DepartmentLoanDecisionDTO, RequestLoanReturnDTO, ReturnAssetLoanDTO
from apps.inventory.forms.base_forms import DATETIME_WIDGET, InventoryForm, UUIDChoiceField
from apps.inventory.models import PhysicalCondition


class AssetLoanCreateForm(InventoryForm):
    asset_id=forms.UUIDField(); borrower_id=UUIDChoiceField(required=False); borrower_name=forms.CharField(max_length=300); borrower_email=forms.EmailField(required=False); borrower_position=forms.CharField(required=False,max_length=180)
    external_borrower=forms.BooleanField(required=False); external_organization=forms.CharField(required=False,max_length=255); external_identification=forms.CharField(required=False,max_length=120)
    origin_department_id=UUIDChoiceField(); origin_area_id=UUIDChoiceField(required=False); origin_site_id=UUIDChoiceField(required=False); destination_department_id=UUIDChoiceField(required=False); destination_area_id=UUIDChoiceField(required=False); destination_site_id=UUIDChoiceField(required=False); external_destination=forms.CharField(required=False,max_length=255)
    due_at=forms.DateTimeField(widget=DATETIME_WIDGET); purpose=forms.CharField(widget=forms.Textarea(attrs={"rows":3}))
    def clean(self):
        d=super().clean()
        if d.get("external_borrower"):
            if not d.get("external_organization"): self.add_error("external_organization","Campo obligatorio para receptor externo.")
            if not d.get("external_identification"): self.add_error("external_identification","Campo obligatorio para receptor externo.")
        elif not d.get("borrower_id"): self.add_error("borrower_id","Seleccione el receptor interno.")
        return d
    def to_dto(self):
        d=self.require_cleaned_data(); return CreateAssetLoanDTO(d["asset_id"],d["borrower_name"],d["origin_department_id"],d["due_at"],d["purpose"],d.get("borrower_id"),d.get("borrower_email", ""),d.get("borrower_position", ""),d.get("external_borrower",False),d.get("external_organization", ""),d.get("external_identification", ""),d.get("origin_area_id"),d.get("origin_site_id"),d.get("destination_department_id"),d.get("destination_area_id"),d.get("destination_site_id"),d.get("external_destination", ""))


class DepartmentLoanDecisionForm(InventoryForm):
    approve=forms.BooleanField(required=False); comment=forms.CharField(required=False,widget=forms.Textarea(attrs={"rows":3})); bypass_reason=forms.CharField(required=False)
    def to_dto(self): d=self.require_cleaned_data(); return DepartmentLoanDecisionDTO(d.get("approve",False),d.get("comment", ""),d.get("bypass_reason", ""))


class AssetLoanAuthorizationForm(DepartmentLoanDecisionForm):
    def to_dto(self): d=self.require_cleaned_data(); return AuthorizeAssetLoanDTO(d.get("approve",False),d.get("comment", ""),d.get("bypass_reason", ""))


class AssetLoanDeliveryForm(InventoryForm):
    delivered_at=forms.DateTimeField(widget=DATETIME_WIDGET,initial=timezone.now); delivery_condition=forms.ChoiceField(choices=PhysicalCondition.choices); notes=forms.CharField(required=False,widget=forms.Textarea(attrs={"rows":3}))
    def to_dto(self): d=self.require_cleaned_data(); return DeliverAssetLoanDTO(d["delivered_at"],d["delivery_condition"],d.get("notes", ""))


class AssetLoanReturnRequestForm(InventoryForm):
    requested_at=forms.DateTimeField(widget=DATETIME_WIDGET,initial=timezone.now); notes=forms.CharField(required=False)
    def to_dto(self): d=self.require_cleaned_data(); return RequestLoanReturnDTO(d["requested_at"],d.get("notes", ""))


class AssetLoanReturnForm(InventoryForm):
    returned_at=forms.DateTimeField(widget=DATETIME_WIDGET,initial=timezone.now); return_condition=forms.ChoiceField(choices=PhysicalCondition.choices); returned_by_id=UUIDChoiceField(); notes=forms.CharField(required=False,widget=forms.Textarea(attrs={"rows":3}))
    def to_dto(self): d=self.require_cleaned_data(); return ReturnAssetLoanDTO(d["returned_at"],d["return_condition"],d["returned_by_id"],d.get("notes", ""))


class AssetLoanCancelForm(InventoryForm):
    reason=forms.CharField(widget=forms.Textarea(attrs={"rows":3})); bypass_reason=forms.CharField(required=False)
    def to_dto(self): d=self.require_cleaned_data(); return CancelAssetLoanDTO(d["reason"],d.get("bypass_reason", ""))


__all__=[name for name in globals() if name.endswith("Form") and name != "InventoryForm"]
