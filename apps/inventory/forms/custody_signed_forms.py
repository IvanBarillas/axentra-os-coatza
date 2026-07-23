from django import forms
from django.utils import timezone

from apps.inventory.forms.base_forms import DATETIME_WIDGET, InventoryForm


class CustodySignedDocumentForm(InventoryForm):
    signed_at = forms.DateTimeField(
        label="Fecha de firma",
        initial=timezone.now,
        widget=DATETIME_WIDGET,
    )
    file = forms.FileField(
        label="Resguardo firmado en PDF",
        help_text="Archivo PDF firmado físicamente por el responsable.",
    )
    notes = forms.CharField(
        label="Observaciones",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def clean_file(self):
        uploaded = self.cleaned_data["file"]
        if getattr(uploaded, "size", 0) > 25 * 1024 * 1024:
            raise forms.ValidationError(
                "El documento no puede superar 25 MB."
            )
        content_type = str(
            getattr(uploaded, "content_type", "") or ""
        ).lower()
        if content_type not in {
            "application/pdf",
            "application/x-pdf",
        }:
            raise forms.ValidationError(
                "El resguardo firmado debe cargarse en formato PDF."
            )
        header = uploaded.read(5)
        uploaded.seek(0)
        if header != b"%PDF-":
            raise forms.ValidationError(
                "El archivo no contiene una cabecera PDF válida."
            )
        return uploaded


__all__ = ["CustodySignedDocumentForm"]
