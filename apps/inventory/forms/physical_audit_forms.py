from django import forms
from django.utils import timezone
from apps.inventory.dtos import CancelPhysicalAuditDTO, ClosePhysicalAuditDTO, CreatePhysicalAuditSessionDTO, FreezePhysicalAuditDTO, GeoPointDTO, MarkAuditItemNotFoundDTO, ReconcilePhysicalAuditItemDTO, RegisterUnlistedAuditItemDTO, ScanPhysicalAuditItemDTO, StartPhysicalAuditDTO
from apps.inventory.forms.base_forms import DATETIME_WIDGET, InventoryForm, UUIDChoiceField
from apps.inventory.models import PhysicalAuditResult, PhysicalAuditScope, PhysicalCondition


class PhysicalAuditCreateForm(InventoryForm):
    name=forms.CharField(max_length=180); fiscal_year=forms.IntegerField(min_value=2000,max_value=9999); scope=forms.ChoiceField(choices=PhysicalAuditScope.choices); site_id=UUIDChoiceField(required=False); department_id=UUIDChoiceField(required=False); area_id=UUIDChoiceField(required=False); notes=forms.CharField(required=False,widget=forms.Textarea(attrs={"rows":3}))
    def clean(self):
        d=super().clean()
        if d.get("scope")==PhysicalAuditScope.DEPARTMENT and not d.get("department_id"): self.add_error("department_id","Requerida para este alcance.")
        if d.get("scope")==PhysicalAuditScope.LOCATION and not d.get("site_id"): self.add_error("site_id","Requerida para este alcance.")
        return d
    def to_dto(self): d=self.require_cleaned_data(); return CreatePhysicalAuditSessionDTO(d["name"],d["fiscal_year"],d["scope"],d.get("site_id"),d.get("department_id"),d.get("area_id"),d.get("notes", ""))


class PhysicalAuditFreezeForm(InventoryForm):
    snapshot_at=forms.DateTimeField(widget=DATETIME_WIDGET,initial=timezone.now); comment=forms.CharField(required=False)
    def to_dto(self): d=self.require_cleaned_data(); return FreezePhysicalAuditDTO(d["snapshot_at"],d.get("comment", ""))


class PhysicalAuditStartForm(InventoryForm):
    started_at=forms.DateTimeField(widget=DATETIME_WIDGET,initial=timezone.now); comment=forms.CharField(required=False)
    def to_dto(self): d=self.require_cleaned_data(); return StartPhysicalAuditDTO(d["started_at"],d.get("comment", ""))


class PhysicalAuditScanForm(InventoryForm):
    scanned_inventory_number=forms.CharField(max_length=100); observed_condition=forms.ChoiceField(choices=PhysicalCondition.choices); observed_site_id=UUIDChoiceField(required=False); observed_department_id=UUIDChoiceField(required=False); observed_area_id=UUIDChoiceField(required=False); observed_custodian_id=UUIDChoiceField(required=False); discrepancy_reason=forms.CharField(required=False,widget=forms.Textarea(attrs={"rows":3})); latitude=forms.DecimalField(required=False,max_digits=10,decimal_places=7); longitude=forms.DecimalField(required=False,max_digits=10,decimal_places=7); notes=forms.CharField(required=False)
    def to_dto(self):
        d=self.require_cleaned_data(); geo=GeoPointDTO(str(d["latitude"]) if d.get("latitude") is not None else None,str(d["longitude"]) if d.get("longitude") is not None else None)
        return ScanPhysicalAuditItemDTO(d["scanned_inventory_number"],d["observed_condition"],d.get("observed_site_id"),d.get("observed_department_id"),d.get("observed_area_id"),d.get("observed_custodian_id"),d.get("discrepancy_reason", ""),geo,{},d.get("notes", ""))


class PhysicalAuditUnlistedItemForm(PhysicalAuditScanForm):
    def to_dto(self):
        d=self.require_cleaned_data(); geo=GeoPointDTO(str(d["latitude"]) if d.get("latitude") is not None else None,str(d["longitude"]) if d.get("longitude") is not None else None)
        return RegisterUnlistedAuditItemDTO(d["scanned_inventory_number"],d["observed_condition"],d.get("observed_site_id"),d.get("observed_department_id"),d.get("observed_area_id"),d.get("observed_custodian_id"),geo,{},d.get("notes", ""))


class PhysicalAuditNotFoundForm(InventoryForm):
    reason=forms.CharField(widget=forms.Textarea(attrs={"rows":3}))
    def to_dto(self): return MarkAuditItemNotFoundDTO(self.require_cleaned_data()["reason"])


class PhysicalAuditReconcileForm(InventoryForm):
    result=forms.ChoiceField(choices=PhysicalAuditResult.choices); notes=forms.CharField(widget=forms.Textarea(attrs={"rows":4})); create_corrective_movement=forms.BooleanField(required=False)
    def to_dto(self): d=self.require_cleaned_data(); return ReconcilePhysicalAuditItemDTO(d["result"],d["notes"],d.get("create_corrective_movement",False))


class PhysicalAuditCloseForm(InventoryForm):
    closing_summary=forms.CharField(widget=forms.Textarea(attrs={"rows":5}))
    def to_dto(self): return ClosePhysicalAuditDTO(self.require_cleaned_data()["closing_summary"])


class PhysicalAuditCancelForm(InventoryForm):
    reason=forms.CharField(widget=forms.Textarea(attrs={"rows":3})); bypass_reason=forms.CharField(required=False)
    def to_dto(self): d=self.require_cleaned_data(); return CancelPhysicalAuditDTO(d["reason"],d.get("bypass_reason", ""))


__all__=[name for name in globals() if name.startswith("PhysicalAudit") and name.endswith("Form")]
