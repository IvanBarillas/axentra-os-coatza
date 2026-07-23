from django import forms
from django.utils import timezone

from apps.inventory.dtos import (
    AcceptCustodyAssignmentDTO,
    AuthorizeCustodyAssignmentDTO,
    CancelCustodyAssignmentDTO,
    CreateCustodyAssignmentDTO,
    RejectCustodyAssignmentDTO,
    ReturnCustodyAssignmentDTO,
)
from apps.inventory.forms.base_forms import (
    DATETIME_WIDGET,
    InventoryForm,
    UUIDChoiceField,
)
from apps.inventory.models import (
    CustodyAcceptanceMethod,
    CustodyAssigneeMode,
    PhysicalCondition,
)


class CustodyCreateForm(InventoryForm):
    asset_id = UUIDChoiceField(
        label="Bien patrimonial",
        help_text=(
            "Busque el bien por folio, nombre o número de serie. "
            "La ubicación se tomará directamente de su expediente."
        ),
    )
    assignee_mode = forms.ChoiceField(
        label="Tipo de responsable",
        choices=CustodyAssigneeMode.choices,
        initial=CustodyAssigneeMode.PUBLIC_SERVANT,
    )
    assigned_to_id = UUIDChoiceField(
        label="Servidor público resguardatario",
        required=False,
        help_text=(
            "Sólo se muestran servidores adscritos a la dependencia "
            "actual del bien."
        ),
    )
    notes = forms.CharField(
        label="Notas internas",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    bypass_reason = forms.CharField(
        label="Justificación de la excepción",
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
    )

    def clean(self):
        cleaned_data = super().clean()
        mode = cleaned_data.get("assignee_mode")
        assigned_to_id = cleaned_data.get("assigned_to_id")

        if (
            mode == CustodyAssigneeMode.PUBLIC_SERVANT
            and not assigned_to_id
        ):
            self.add_error(
                "assigned_to_id",
                "Seleccione al servidor público que recibirá el resguardo.",
            )

        return cleaned_data

    def to_dto(self):
        data = self.require_cleaned_data()
        return CreateCustodyAssignmentDTO(
            asset_id=data["asset_id"],
            assignee_mode=data["assignee_mode"],
            assigned_at=timezone.now(),
            assigned_to_id=data.get("assigned_to_id"),
            notes=data.get("notes", ""),
            bypass_reason=data.get("bypass_reason", ""),
        )


class CustodyAuthorizeForm(InventoryForm):
    comment = forms.CharField(
        label="Comentario de autorización",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    bypass_reason = forms.CharField(
        label="Justificación del bypass",
        required=False,
    )

    def to_dto(self):
        data = self.require_cleaned_data()
        return AuthorizeCustodyAssignmentDTO(
            data.get("comment", ""),
            data.get("bypass_reason", ""),
        )


class CustodyAcceptForm(InventoryForm):
    acceptance_method = forms.ChoiceField(
        label="Método de aceptación",
        choices=CustodyAcceptanceMethod.choices,
    )
    signature_hash = forms.CharField(
        label="Hash de firma digital",
        required=False,
        max_length=255,
    )
    comment = forms.CharField(
        label="Comentario",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def to_dto(self):
        data = self.require_cleaned_data()
        return AcceptCustodyAssignmentDTO(
            data["acceptance_method"],
            data.get("signature_hash", ""),
            data.get("comment", ""),
        )


class CustodyRejectForm(InventoryForm):
    reason = forms.CharField(
        label="Motivo del rechazo",
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def to_dto(self):
        return RejectCustodyAssignmentDTO(
            self.require_cleaned_data()["reason"]
        )


class CustodyReturnForm(InventoryForm):
    returned_at = forms.DateTimeField(
        label="Fecha de devolución",
        widget=DATETIME_WIDGET,
        initial=timezone.now,
    )
    physical_condition = forms.ChoiceField(
        label="Condición física al devolver",
        choices=PhysicalCondition.choices,
    )
    notes = forms.CharField(
        label="Observaciones de devolución",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def to_dto(self):
        data = self.require_cleaned_data()
        return ReturnCustodyAssignmentDTO(
            data["returned_at"],
            data["physical_condition"],
            data.get("notes", ""),
        )


class CustodyCancelForm(InventoryForm):
    reason = forms.CharField(
        label="Motivo de cancelación",
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    bypass_reason = forms.CharField(
        label="Justificación del bypass",
        required=False,
    )

    def to_dto(self):
        data = self.require_cleaned_data()
        return CancelCustodyAssignmentDTO(
            data["reason"],
            data.get("bypass_reason", ""),
        )


class CustodyDeliverForm(InventoryForm):
    comment = forms.CharField(
        label="Observaciones de la entrega física",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )


__all__ = [
    name
    for name in globals()
    if name.startswith("Custody") and name.endswith("Form")
]

