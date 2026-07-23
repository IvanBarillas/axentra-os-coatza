from uuid import UUID

from django import forms

from apps.inventory.forms.base_forms import InventoryForm, UUIDChoiceField
from apps.inventory.models import CustodyAssigneeMode


class CustodyDocumentCreateForm(InventoryForm):
    department_id = UUIDChoiceField(label="Dependencia")
    assignee_mode = forms.ChoiceField(
        label="Tipo de responsable",
        choices=CustodyAssigneeMode.choices,
        initial=CustodyAssigneeMode.DEPARTMENT_MANAGER,
    )
    assigned_to_id = UUIDChoiceField(
        label="Servidor público resguardatario",
        required=False,
    )
    asset_ids = forms.MultipleChoiceField(
        label="Bienes patrimoniales",
        choices=(),
        widget=forms.CheckboxSelectMultiple,
    )
    notes = forms.CharField(
        label="Notas del documento",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    bypass_reason = forms.CharField(
        label="Justificación de la excepción",
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
    )

    def clean(self):
        data = super().clean()
        if (
            data.get("assignee_mode") == CustodyAssigneeMode.PUBLIC_SERVANT
            and not data.get("assigned_to_id")
        ):
            self.add_error(
                "assigned_to_id",
                "Seleccione al servidor público responsable.",
            )
        if not data.get("asset_ids"):
            self.add_error(
                "asset_ids",
                "Seleccione al menos un bien patrimonial.",
            )
        return data

    def cleaned_asset_ids(self):
        return [UUID(value) for value in self.cleaned_data["asset_ids"]]


class CustodyDocumentReplaceForm(InventoryForm):
    assignee_mode = forms.ChoiceField(
        label="Nuevo tipo de responsable",
        choices=CustodyAssigneeMode.choices,
        initial=CustodyAssigneeMode.DEPARTMENT_MANAGER,
    )
    assigned_to_id = UUIDChoiceField(
        label="Nuevo servidor público resguardatario",
        required=False,
    )
    reason = forms.CharField(
        label="Motivo del cambio",
        initial="Cambio de titular o encargado de la dependencia.",
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def clean(self):
        data = super().clean()
        if (
            data.get("assignee_mode") == CustodyAssigneeMode.PUBLIC_SERVANT
            and not data.get("assigned_to_id")
        ):
            self.add_error(
                "assigned_to_id",
                "Seleccione al nuevo servidor público responsable.",
            )
        return data


__all__ = [
    "CustodyDocumentCreateForm",
    "CustodyDocumentReplaceForm",
]
