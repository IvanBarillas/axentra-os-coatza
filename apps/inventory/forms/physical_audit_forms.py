from django import forms
from django.utils import timezone
from apps.inventory.dtos import CancelPhysicalAuditDTO, ClosePhysicalAuditDTO, CreatePhysicalAuditSessionDTO, FreezePhysicalAuditDTO, GeoPointDTO, MarkAuditItemNotFoundDTO, ReconcilePhysicalAuditItemDTO, RegisterUnlistedAuditItemDTO, ScanPhysicalAuditItemDTO, StartPhysicalAuditDTO
from apps.inventory.forms.base_forms import DATETIME_WIDGET, InventoryForm, UUIDChoiceField
from apps.inventory.models import PhysicalAuditResult, PhysicalAuditScope, PhysicalCondition


class PhysicalAuditCreateForm(InventoryForm):
    name=forms.CharField(label="Nombre de la auditoría",max_length=180); fiscal_year=forms.IntegerField(label="Ejercicio fiscal",min_value=2000,max_value=9999); scope=forms.ChoiceField(label="Tipo de revisión",choices=PhysicalAuditScope.choices); site_id=UUIDChoiceField(label="Sede que será revisada",required=True); department_id=UUIDChoiceField(label="Dependencia que será revisada",required=True); notes=forms.CharField(label="Notas",required=False,widget=forms.Textarea(attrs={"rows":3}))
    def clean(self):
        d=super().clean()
        if not d.get("site_id"): self.add_error("site_id","Seleccione la sede que será revisada.")
        if not d.get("department_id"): self.add_error("department_id","Seleccione la dependencia que será revisada.")
        return d
    def to_dto(self): d=self.require_cleaned_data(); return CreatePhysicalAuditSessionDTO(d["name"],d["fiscal_year"],d["scope"],d["site_id"],d["department_id"],None,d.get("notes", ""))


class PhysicalAuditFreezeForm(InventoryForm):
    snapshot_at=forms.DateTimeField(label="Fecha y hora de corte",widget=DATETIME_WIDGET,initial=timezone.now); comment=forms.CharField(label="Comentario",required=False)
    def to_dto(self): d=self.require_cleaned_data(); return FreezePhysicalAuditDTO(d["snapshot_at"],d.get("comment", ""))


class PhysicalAuditStartForm(InventoryForm):
    started_at=forms.DateTimeField(label="Fecha y hora de inicio",widget=DATETIME_WIDGET,initial=timezone.now); comment=forms.CharField(label="Comentario",required=False)
    def to_dto(self): d=self.require_cleaned_data(); return StartPhysicalAuditDTO(d["started_at"],d.get("comment", ""))


class PhysicalAuditScanForm(InventoryForm):
    scanned_inventory_number=forms.CharField(label="Folio, serie o código escaneado",max_length=100); observed_condition=forms.ChoiceField(label="Condición encontrada",choices=PhysicalCondition.choices); observed_site_id=UUIDChoiceField(label="Sede encontrada",required=False); observed_department_id=UUIDChoiceField(label="Dependencia encontrada",required=False); observed_area_id=UUIDChoiceField(label="Área encontrada",required=False); observed_custodian_id=UUIDChoiceField(label="Resguardatario encontrado",required=False); discrepancy_reason=forms.CharField(label="Descripción de la diferencia",required=False,widget=forms.Textarea(attrs={"rows":3})); latitude=forms.DecimalField(label="Latitud",required=False,max_digits=10,decimal_places=7); longitude=forms.DecimalField(label="Longitud",required=False,max_digits=10,decimal_places=7); notes=forms.CharField(label="Notas",required=False)
    def to_dto(self):
        d=self.require_cleaned_data(); geo=GeoPointDTO(str(d["latitude"]) if d.get("latitude") is not None else None,str(d["longitude"]) if d.get("longitude") is not None else None)
        return ScanPhysicalAuditItemDTO(d["scanned_inventory_number"],d["observed_condition"],d.get("observed_site_id"),d.get("observed_department_id"),d.get("observed_area_id"),d.get("observed_custodian_id"),d.get("discrepancy_reason", ""),geo,{},d.get("notes", ""))


class PhysicalAuditUnlistedItemForm(PhysicalAuditScanForm):
    def to_dto(self):
        d=self.require_cleaned_data(); geo=GeoPointDTO(str(d["latitude"]) if d.get("latitude") is not None else None,str(d["longitude"]) if d.get("longitude") is not None else None)
        return RegisterUnlistedAuditItemDTO(d["scanned_inventory_number"],d["observed_condition"],d.get("observed_site_id"),d.get("observed_department_id"),d.get("observed_area_id"),d.get("observed_custodian_id"),geo,{},d.get("notes", ""))


class PhysicalAuditNotFoundForm(InventoryForm):
    reason=forms.CharField(label="Motivo por el que no fue localizado",widget=forms.Textarea(attrs={"rows":3}))
    def to_dto(self): return MarkAuditItemNotFoundDTO(self.require_cleaned_data()["reason"])


class PhysicalAuditReconcileForm(InventoryForm):
    result=forms.ChoiceField(label="Resultado final",choices=PhysicalAuditResult.choices); notes=forms.CharField(label="Conclusión de la conciliación",widget=forms.Textarea(attrs={"rows":4})); create_corrective_movement=forms.BooleanField(label="Solicitar movimiento correctivo",required=False,help_text="La corrección deberá completarse desde el módulo de Movimientos.")
    def to_dto(self): d=self.require_cleaned_data(); return ReconcilePhysicalAuditItemDTO(d["result"],d["notes"],d.get("create_corrective_movement",False))


class PhysicalAuditCloseForm(InventoryForm):
    closing_summary=forms.CharField(label="Conclusiones del levantamiento",widget=forms.Textarea(attrs={"rows":5}))
    def to_dto(self): return ClosePhysicalAuditDTO(self.require_cleaned_data()["closing_summary"])


class PhysicalAuditCancelForm(InventoryForm):
    reason=forms.CharField(label="Motivo de cancelación",widget=forms.Textarea(attrs={"rows":3})); bypass_reason=forms.CharField(label="Justificación de excepción",required=False)
    def to_dto(self): d=self.require_cleaned_data(); return CancelPhysicalAuditDTO(d["reason"],d.get("bypass_reason", ""))


__all__=[name for name in globals() if name.startswith("PhysicalAudit") and name.endswith("Form")]
