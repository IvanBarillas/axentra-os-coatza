from dataclasses import replace

from django import forms
from apps.inventory.dtos import GeoPointDTO, ReplaceInventoryDocumentDTO, ResolveDocumentValidationDTO, ResolvePhotoValidationDTO, SubmitDocumentValidationDTO, UploadInventoryDocumentDTO, UploadInventoryPhotoDTO
from apps.inventory.forms.base_forms import InventoryForm
from apps.inventory.models import DocumentAccessLevel, DocumentType, InventoryDocumentOwnerType, InventoryPhotoType


class InventoryDocumentUploadForm(InventoryForm):
    owner_type=forms.ChoiceField(choices=InventoryDocumentOwnerType.choices); owner_id=forms.UUIDField(); document_type=forms.ChoiceField(label="Tipo de documento", choices=DocumentType.choices); title=forms.CharField(label="Título", max_length=180); description=forms.CharField(label="Descripción", required=False,widget=forms.Textarea(attrs={"rows":3})); file=forms.FileField(label="Archivo PDF"); external_reference=forms.CharField(label="Folio externo relacionado", required=False, max_length=180, help_text="Ejemplo: ticket, diagnóstico u oficio emitido por otra área."); access_level=forms.ChoiceField(label="Nivel de acceso", choices=DocumentAccessLevel.choices); is_required_evidence=forms.BooleanField(label="Evidencia obligatoria", required=False)
    def to_dto(self):
        d=self.require_cleaned_data(); f=d["file"]; return UploadInventoryDocumentDTO(d["owner_type"],d["owner_id"],d["document_type"],d["title"],f,f.name,getattr(f,"content_type","") or "",d.get("description", ""),d["access_level"],d.get("is_required_evidence",False),d.get("external_reference", ""))

    def clean_file(self):
        uploaded = self.cleaned_data["file"]
        if getattr(uploaded, "size", 0) > 25 * 1024 * 1024:
            raise forms.ValidationError("El documento no puede superar 25 MB.")
        content_type = str(getattr(uploaded, "content_type", "") or "").lower()
        if content_type not in {"application/pdf", "application/x-pdf"}:
            raise forms.ValidationError("El expediente documental admite únicamente archivos PDF.")
        return uploaded


class ContextDocumentUploadForm(InventoryDocumentUploadForm):
    """Carga vinculada a un expediente ya validado por la vista."""

    def __init__(self, *args, owner_type, owner_id, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["owner_type"].initial = owner_type
        self.fields["owner_type"].widget = forms.HiddenInput()
        self.fields["owner_id"].initial = owner_id
        self.fields["owner_id"].widget = forms.HiddenInput()
        self.fields["access_level"].initial = DocumentAccessLevel.INTERNAL


class DisposalStageDocumentUploadForm(InventoryDocumentUploadForm):
    def __init__(
        self,
        *args,
        approval_id,
        document_choices=(),
        custodial_integration=False,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.fields["owner_type"].initial = InventoryDocumentOwnerType.DISPOSAL_APPROVAL
        self.fields["owner_type"].widget = forms.HiddenInput()
        self.fields["owner_id"].initial = approval_id
        self.fields["owner_id"].widget = forms.HiddenInput()
        # Nunca heredar el catálogo completo: una etapa de baja sólo admite
        # los tipos congelados específicamente para ella.
        self.fields["document_type"].choices = list(document_choices)
        self.custodial_integration = bool(custodial_integration)
        if self.custodial_integration:
            self.fields["issuing_authority"] = forms.CharField(
                label="Área que emitió el documento",
                max_length=180,
                required=False,
                help_text="Nombre del área o autoridad que emitió y firmó el documento.",
                widget=forms.TextInput(attrs={
                    "placeholder": "Ejemplo: Dirección de Innovación Gubernamental",
                }),
            )
            self.fields["issuing_official_role"] = forms.CharField(
                label="Cargo de la persona firmante",
                max_length=180,
                required=False,
                help_text="Indique el cargo institucional, no el nombre del integrador.",
                widget=forms.TextInput(attrs={
                    "placeholder": "Ejemplo: Director de Innovación Gubernamental",
                }),
            )
            self.fields["document_date"] = forms.DateField(
                label="Fecha de emisión",
                required=False,
                widget=forms.DateInput(attrs={"type": "date"}),
            )
            self.fields["external_reference"].label = "Folio del oficio o acuerdo"
            self.fields["external_reference"].widget.attrs.setdefault(
                "placeholder", "Ejemplo: DIT-STI-TM001-26"
            )

        # Los campos de autoría se crean dinámicamente después del __init__
        # del formulario base; aplicar nuevamente el estilizador garantiza que
        # tengan la misma presentación institucional que el resto del módulo.
        self.aplicar_estilos_institucionales()

    def clean(self):
        data = super().clean()
        custodial_types = {
            DocumentType.TECHNICAL_REPORT,
            DocumentType.ACCOUNTING_DISPOSAL_CONFIRMATION,
        }
        if self.custodial_integration and data.get("document_type") in custodial_types:
            required_fields = {
                "issuing_authority": "Indique el área o autoridad emisora.",
                "issuing_official_role": "Indique el cargo de quien suscribe.",
                "document_date": "Indique la fecha de emisión.",
                "external_reference": "Indique el folio o número del documento.",
            }
            for field_name, message in required_fields.items():
                if not data.get(field_name):
                    self.add_error(field_name, message)
        return data

    def to_dto(self):
        dto = super().to_dto()
        custodial_types = {
            DocumentType.TECHNICAL_REPORT,
            DocumentType.ACCOUNTING_DISPOSAL_CONFIRMATION,
        }
        data = self.require_cleaned_data()
        if (
            not self.custodial_integration
            or data.get("document_type") not in custodial_types
        ):
            return dto
        return replace(dto, metadata={
            "document_origin": "CUSTODIAL_INTEGRATION",
            "issuing_authority": data["issuing_authority"],
            "issuing_official_role": data["issuing_official_role"],
            "document_date": data["document_date"].isoformat(),
        })

    def clean_file(self):
        uploaded = self.cleaned_data["file"]
        if getattr(uploaded, "size", 0) > 25 * 1024 * 1024:
            raise forms.ValidationError("El documento no puede superar 25 MB.")
        content_type = str(getattr(uploaded, "content_type", "") or "").lower()
        if content_type not in {"application/pdf", "application/x-pdf"}:
            raise forms.ValidationError("Para este expediente debe cargar un archivo PDF.")
        return uploaded


class DocumentValidationSubmitForm(InventoryForm):
    comment=forms.CharField(required=False,widget=forms.Textarea(attrs={"rows":3}))
    def to_dto(self): return SubmitDocumentValidationDTO(self.require_cleaned_data().get("comment", ""))


class DocumentValidationResolveForm(InventoryForm):
    approve=forms.BooleanField(required=False); comment=forms.CharField(widget=forms.Textarea(attrs={"rows":3})); bypass_reason=forms.CharField(required=False)
    def to_dto(self): d=self.require_cleaned_data(); return ResolveDocumentValidationDTO(d.get("approve",False),d["comment"],d.get("bypass_reason", ""))


class InventoryDocumentReplaceForm(InventoryForm):
    file=forms.FileField(); reason=forms.CharField(widget=forms.Textarea(attrs={"rows":3}))
    def to_dto(self): d=self.require_cleaned_data(); f=d["file"]; return ReplaceInventoryDocumentDTO(f,f.name,getattr(f,"content_type","") or "",d["reason"])


class InventoryPhotoUploadForm(InventoryForm):
    owner_type=forms.ChoiceField(choices=InventoryDocumentOwnerType.choices); owner_id=forms.UUIDField(); photo_type=forms.ChoiceField(choices=InventoryPhotoType.choices); image=forms.ImageField(); caption=forms.CharField(required=False,max_length=255); is_required_evidence=forms.BooleanField(required=False); latitude=forms.DecimalField(required=False,max_digits=10,decimal_places=7); longitude=forms.DecimalField(required=False,max_digits=10,decimal_places=7)
    def to_dto(self):
        d=self.require_cleaned_data(); f=d["image"]; geo=GeoPointDTO(str(d["latitude"]) if d.get("latitude") is not None else None,str(d["longitude"]) if d.get("longitude") is not None else None)
        return UploadInventoryPhotoDTO(d["owner_type"],d["owner_id"],d["photo_type"],f,f.name,getattr(f,"content_type","") or "",d.get("caption", ""),d.get("is_required_evidence",False),geo)


class AssetPhotoUploadForm(InventoryPhotoUploadForm):
    """Carga acotada al activo abierto; el propietario no se captura manualmente."""

    def __init__(self, *args, asset_id, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["owner_type"].initial = InventoryDocumentOwnerType.ASSET
        self.fields["owner_type"].widget = forms.HiddenInput()
        self.fields["owner_id"].initial = asset_id
        self.fields["owner_id"].widget = forms.HiddenInput()

    def clean_image(self):
        image = self.cleaned_data["image"]
        if getattr(image, "size", 0) > 15 * 1024 * 1024:
            raise forms.ValidationError(
                "La fotografía no puede superar 15 MB."
            )
        content_type = str(getattr(image, "content_type", "") or "").lower()
        if content_type not in {"image/jpeg", "image/png", "image/webp"}:
            raise forms.ValidationError(
                "Utilice una imagen JPG, PNG o WEBP."
            )
        return image


class PhysicalAuditDocumentUploadForm(InventoryDocumentUploadForm):
    def __init__(self, *args, owner_type, owner_id, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["owner_type"].initial = owner_type
        self.fields["owner_type"].widget = forms.HiddenInput()
        self.fields["owner_id"].initial = owner_id
        self.fields["owner_id"].widget = forms.HiddenInput()
        self.fields["document_type"].choices = [
            (DocumentType.PHYSICAL_AUDIT_EVIDENCE, "Evidencia de auditoría física"),
            (DocumentType.OTHER, "Otro documento de soporte"),
        ]
        self.fields["access_level"].initial = DocumentAccessLevel.INTERNAL

    def clean_file(self):
        uploaded = self.cleaned_data["file"]
        if getattr(uploaded, "size", 0) > 25 * 1024 * 1024:
            raise forms.ValidationError("El documento no puede superar 25 MB.")
        content_type = str(getattr(uploaded, "content_type", "") or "").lower()
        if content_type not in {"application/pdf", "application/x-pdf"}:
            raise forms.ValidationError("La evidencia documental debe estar en formato PDF.")
        return uploaded


class PhysicalAuditPhotoUploadForm(InventoryPhotoUploadForm):
    def __init__(self, *args, owner_type, owner_id, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["owner_type"].initial = owner_type
        self.fields["owner_type"].widget = forms.HiddenInput()
        self.fields["owner_id"].initial = owner_id
        self.fields["owner_id"].widget = forms.HiddenInput()
        self.fields["photo_type"].choices = [
            (InventoryPhotoType.PHYSICAL_AUDIT, "Evidencia de auditoría física"),
            (InventoryPhotoType.LOCATION, "Ubicación encontrada"),
            (InventoryPhotoType.DAMAGE, "Daño encontrado"),
            (InventoryPhotoType.INVENTORY_LABEL, "Etiqueta de inventario"),
            (InventoryPhotoType.OTHER, "Otra fotografía"),
        ]

    def clean_image(self):
        image = self.cleaned_data["image"]
        if getattr(image, "size", 0) > 15 * 1024 * 1024:
            raise forms.ValidationError("La fotografía no puede superar 15 MB.")
        content_type = str(getattr(image, "content_type", "") or "").lower()
        if content_type not in {"image/jpeg", "image/png", "image/webp"}:
            raise forms.ValidationError("Utilice una imagen JPG, PNG o WEBP.")
        return image


class InventoryPhotoValidationForm(InventoryForm):
    approve=forms.BooleanField(required=False); comment=forms.CharField(required=False,widget=forms.Textarea(attrs={"rows":3}))
    def to_dto(self): d=self.require_cleaned_data(); return ResolvePhotoValidationDTO(d.get("approve",False),d.get("comment", ""))


__all__=[name for name in globals() if name.endswith("Form") and name != "InventoryForm"]
