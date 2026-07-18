from django import forms
from apps.inventory.dtos import ChangeAssetLocationDTO, GeoPointDTO, MaintenanceMovementDTO, ReassignAssetDTO, TransferAssetDTO
from apps.inventory.forms.base_forms import DATETIME_WIDGET, InventoryForm, UUIDChoiceField


class AssetTransferForm(InventoryForm):
    asset_id=UUIDChoiceField(); destination_department_id=UUIDChoiceField(); destination_area_id=UUIDChoiceField(required=False); destination_site_id=UUIDChoiceField(required=False); destination_custodian_id=UUIDChoiceField(required=False)
    reason=forms.CharField(widget=forms.Textarea(attrs={"rows":3})); occurred_at=forms.DateTimeField(required=False,widget=DATETIME_WIDGET); bypass_reason=forms.CharField(required=False)
    def to_dto(self):
        d=self.require_cleaned_data(); return TransferAssetDTO(d["asset_id"],d["destination_department_id"],d["reason"],d.get("destination_area_id"),d.get("destination_site_id"),d.get("destination_custodian_id"),d.get("occurred_at"),d.get("bypass_reason", ""))


class AssetReassignmentForm(InventoryForm):
    asset_id=UUIDChoiceField(); user_id=UUIDChoiceField(label="Nuevo resguardatario"); department_id=UUIDChoiceField(required=False); area_id=UUIDChoiceField(required=False); site_id=UUIDChoiceField(required=False)
    reason=forms.CharField(widget=forms.Textarea(attrs={"rows":3})); occurred_at=forms.DateTimeField(required=False,widget=DATETIME_WIDGET)
    def to_dto(self): d=self.require_cleaned_data(); return ReassignAssetDTO(d["asset_id"],d["user_id"],d["reason"],d.get("department_id"),d.get("area_id"),d.get("site_id"),d.get("occurred_at"))


class AssetLocationChangeForm(InventoryForm):
    asset_id=UUIDChoiceField(); department_id=UUIDChoiceField(required=False); area_id=UUIDChoiceField(required=False); site_id=UUIDChoiceField(required=False)
    latitude=forms.DecimalField(required=False,max_digits=10,decimal_places=7); longitude=forms.DecimalField(required=False,max_digits=10,decimal_places=7); reason=forms.CharField(widget=forms.Textarea(attrs={"rows":3})); occurred_at=forms.DateTimeField(required=False,widget=DATETIME_WIDGET)
    def to_dto(self):
        d=self.require_cleaned_data(); geo=GeoPointDTO(str(d["latitude"]) if d.get("latitude") is not None else None,str(d["longitude"]) if d.get("longitude") is not None else None)
        return ChangeAssetLocationDTO(d["asset_id"],d["reason"],d.get("department_id"),d.get("area_id"),d.get("site_id"),geo,d.get("occurred_at"))


class MaintenanceMovementForm(InventoryForm):
    asset_id=UUIDChoiceField(); reason=forms.CharField(widget=forms.Textarea(attrs={"rows":3})); service_order_id=forms.UUIDField(); service_order_folio=forms.CharField(required=False); physical_condition=forms.CharField(required=False); occurred_at=forms.DateTimeField(required=False,widget=DATETIME_WIDGET)
    def to_dto(self):
        from apps.inventory.dtos import ExternalReferenceDTO
        d=self.require_cleaned_data(); ref=ExternalReferenceDTO("maintenance","ServiceOrder",d["service_order_id"],d.get("service_order_folio", "")); return MaintenanceMovementDTO(d["asset_id"],d["reason"],ref,d.get("physical_condition", ""),d.get("occurred_at"))


__all__=["AssetLocationChangeForm","AssetReassignmentForm","AssetTransferForm","MaintenanceMovementForm"]
