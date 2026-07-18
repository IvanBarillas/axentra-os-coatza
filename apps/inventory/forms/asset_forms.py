from django import forms
from apps.inventory.dtos import CorrectAssetDTO, GeoPointDTO, UpdateAssetConditionDTO, UpdateAssetLocationDTO
from apps.inventory.forms.base_forms import InventoryForm, UUIDChoiceField
from apps.inventory.models import AccountingAccount, AssetCategory, AssetOperationalStatus, PhysicalCondition


class AssetCorrectionForm(InventoryForm):
    reason=forms.CharField(widget=forms.Textarea(attrs={"rows":3})); name=forms.CharField(max_length=180,required=False)
    description=forms.CharField(required=False,widget=forms.Textarea(attrs={"rows":3})); category=forms.ModelChoiceField(AssetCategory.objects.none(),required=False)
    accounting_account=forms.ModelChoiceField(AccountingAccount.objects.none(),required=False); serial_number=forms.CharField(max_length=120,required=False)
    acquisition_cost=forms.DecimalField(required=False,min_value=0,max_digits=16,decimal_places=2); residual_value=forms.DecimalField(required=False,min_value=0,max_digits=16,decimal_places=2)
    notes=forms.CharField(required=False,widget=forms.Textarea(attrs={"rows":3}))
    def __init__(self,*a,**kw):
        super().__init__(*a,**kw); active={"is_active":True,"is_deleted":False}
        self.fields["category"].queryset=AssetCategory.objects.filter(**active); self.fields["accounting_account"].queryset=AccountingAccount.objects.filter(**active)
    def to_dto(self):
        d=self.require_cleaned_data(); return CorrectAssetDTO(d["reason"],d.get("name") or None,d.get("description") or None,d["category"].id if d.get("category") else None,d["accounting_account"].id if d.get("accounting_account") else None,d.get("serial_number") or None,d.get("acquisition_cost"),d.get("residual_value"),d.get("notes") or None)


class AssetConditionUpdateForm(InventoryForm):
    physical_condition=forms.ChoiceField(choices=PhysicalCondition.choices); operational_status=forms.ChoiceField(choices=[("","--- Sin cambio ---"),*AssetOperationalStatus.choices],required=False)
    reason=forms.CharField(widget=forms.Textarea(attrs={"rows":3}))
    def to_dto(self):
        d=self.require_cleaned_data(); return UpdateAssetConditionDTO(d["physical_condition"],d["reason"],d.get("operational_status") or None)


class AssetLocationUpdateForm(InventoryForm):
    department_id=UUIDChoiceField(); site_id=UUIDChoiceField(required=False); area_id=UUIDChoiceField(required=False); custodian_id=UUIDChoiceField(required=False)
    latitude=forms.DecimalField(required=False,max_digits=10,decimal_places=7); longitude=forms.DecimalField(required=False,max_digits=10,decimal_places=7)
    reason=forms.CharField(widget=forms.Textarea(attrs={"rows":3}))
    def to_dto(self):
        d=self.require_cleaned_data(); geo=GeoPointDTO(str(d["latitude"]) if d.get("latitude") is not None else None,str(d["longitude"]) if d.get("longitude") is not None else None)
        return UpdateAssetLocationDTO(d["department_id"],d.get("site_id"),d.get("area_id"),d.get("custodian_id"),d["reason"],geo)


__all__=["AssetConditionUpdateForm","AssetCorrectionForm","AssetLocationUpdateForm"]
