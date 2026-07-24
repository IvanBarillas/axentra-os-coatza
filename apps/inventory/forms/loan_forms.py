from django import forms
from django.utils import timezone

from apps.inventory.dtos import (
    AuthorizeAssetLoanDTO,
    CancelAssetLoanDTO,
    CreateAssetLoanDTO,
    DeliverAssetLoanDTO,
    DepartmentLoanDecisionDTO,
    RequestLoanReturnDTO,
    ReturnAssetLoanDTO,
)
from apps.inventory.forms.base_forms import DATETIME_WIDGET, InventoryForm, UUIDChoiceField
from apps.inventory.models import PhysicalCondition


class AssetLoanCreateForm(InventoryForm):
    asset_id = UUIDChoiceField(label="Bien que será prestado")
    borrower_id = UUIDChoiceField(label="Receptor interno", required=False)
    borrower_name = forms.CharField(label="Nombre del receptor externo", max_length=300, required=False)
    borrower_email = forms.EmailField(label="Correo del receptor externo", required=False)
    borrower_position = forms.CharField(label="Cargo del receptor", required=False, max_length=180)
    external_borrower = forms.BooleanField(label="El receptor es externo", required=False)
    external_organization = forms.CharField(label="Institución externa", required=False, max_length=255)
    external_identification = forms.CharField(label="Identificación oficial", required=False, max_length=120)
    origin_site_id = UUIDChoiceField(label="Sede de origen")
    origin_department_id = UUIDChoiceField(label="Dependencia propietaria")
    origin_area_id = UUIDChoiceField(label="Área de origen", required=False)
    destination_site_id = UUIDChoiceField(label="Sede receptora", required=False)
    destination_department_id = UUIDChoiceField(label="Dependencia receptora", required=False)
    destination_area_id = UUIDChoiceField(label="Área receptora", required=False)
    external_destination = forms.CharField(label="Ubicación externa", required=False, max_length=255)
    due_at = forms.DateTimeField(label="Fecha límite de devolución", widget=DATETIME_WIDGET)
    purpose = forms.CharField(label="Motivo y objeto del préstamo", widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.order_fields([
            "origin_site_id", "origin_department_id", "origin_area_id",
            "asset_id", "destination_site_id", "destination_department_id",
            "destination_area_id", "borrower_id", "external_borrower",
            "borrower_name", "borrower_email", "borrower_position",
            "external_organization", "external_identification",
            "external_destination", "due_at", "purpose",
        ])

    def clean(self):
        data = super().clean()
        if data.get("external_borrower"):
            for field in ("borrower_name", "external_organization", "external_identification", "external_destination"):
                if not data.get(field):
                    self.add_error(field, "Este campo es obligatorio para un receptor externo.")
        else:
            if not data.get("destination_department_id"):
                self.add_error("destination_department_id", "Seleccione la dependencia receptora.")
            if not getattr(self, "defer_destination_assignment", False):
                if not data.get("borrower_id"):
                    self.add_error("borrower_id", "Seleccione el receptor interno.")
                if not data.get("destination_site_id"):
                    self.add_error("destination_site_id", "Seleccione la sede receptora.")
        if data.get("due_at") and data["due_at"] <= timezone.now():
            self.add_error("due_at", "La fecha límite debe ser futura.")
        return data

    def to_dto(self):
        data = self.require_cleaned_data()
        return CreateAssetLoanDTO(
            data["asset_id"], data.get("borrower_name", ""),
            data["origin_department_id"], data["due_at"], data["purpose"],
            data.get("borrower_id"), data.get("borrower_email", ""),
            data.get("borrower_position", ""), data.get("external_borrower", False),
            data.get("external_organization", ""), data.get("external_identification", ""),
            data.get("origin_area_id"), data.get("origin_site_id"),
            data.get("destination_department_id"), data.get("destination_area_id"),
            data.get("destination_site_id"), data.get("external_destination", ""),
        )


class AssetLoanFromAssetForm(AssetLoanCreateForm):
    """Solicitud simplificada: el bien y su origen vienen del expediente."""

    def __init__(
        self,
        *args,
        asset_id,
        origin_department_id,
        origin_area_id=None,
        origin_site_id=None,
        **kwargs,
    ):
        self.defer_destination_assignment = True
        self.fixed_asset_id = asset_id
        self.fixed_origin_department_id = origin_department_id
        self.fixed_origin_area_id = origin_area_id
        self.fixed_origin_site_id = origin_site_id
        super().__init__(*args, **kwargs)
        for field_name in (
            "asset_id",
            "origin_department_id",
            "origin_area_id",
            "origin_site_id",
            "destination_area_id",
            "destination_site_id",
            "borrower_id",
            "borrower_name",
            "borrower_email",
            "borrower_position",
            "external_borrower",
            "external_organization",
            "external_identification",
            "external_destination",
        ):
            self.fields.pop(field_name, None)

    def to_dto(self):
        data = self.require_cleaned_data()
        return CreateAssetLoanDTO(
            asset_id=self.fixed_asset_id,
            borrower_name=data.get("borrower_name", ""),
            origin_department_id=self.fixed_origin_department_id,
            due_at=data["due_at"],
            purpose=data["purpose"],
            borrower_id=data.get("borrower_id"),
            borrower_email=data.get("borrower_email", ""),
            borrower_position=data.get("borrower_position", ""),
            external_borrower=data.get("external_borrower", False),
            external_organization=data.get("external_organization", ""),
            external_identification=data.get("external_identification", ""),
            origin_area_id=self.fixed_origin_area_id,
            origin_site_id=self.fixed_origin_site_id,
            destination_department_id=data.get("destination_department_id"),
            destination_area_id=data.get("destination_area_id"),
            destination_site_id=data.get("destination_site_id"),
            external_destination=data.get("external_destination", ""),
        )


class DepartmentLoanDecisionForm(InventoryForm):
    approve = forms.BooleanField(label="Aceptar el préstamo", required=False)
    destination_area_id = UUIDChoiceField(label="Área que recibirá el bien", required=False)
    borrower_id = UUIDChoiceField(label="Responsable temporal (opcional)", required=False)
    comment = forms.CharField(label="Comentario o motivo del rechazo", required=False, widget=forms.Textarea(attrs={"rows": 3}))
    bypass_reason = forms.CharField(label="Motivo de excepción", required=False)

    def clean(self):
        data = super().clean()
        if not data.get("approve") and not str(data.get("comment", "")).strip():
            self.add_error("comment", "Debe indicar el motivo del rechazo.")
        if data.get("approve") and not data.get("destination_area_id"):
            self.add_error("destination_area_id", "Seleccione el área que recibirá el bien.")
        return data

    def to_dto(self):
        data = self.require_cleaned_data()
        return DepartmentLoanDecisionDTO(
            approve=data.get("approve", False),
            comment=data.get("comment", ""),
            bypass_reason=data.get("bypass_reason", ""),
            destination_area_id=data.get("destination_area_id"),
            borrower_id=data.get("borrower_id"),
        )


class AssetLoanAuthorizationForm(DepartmentLoanDecisionForm):
    approve = forms.BooleanField(label="Autorizar el préstamo", required=False)

    def to_dto(self):
        data = self.require_cleaned_data()
        return AuthorizeAssetLoanDTO(data.get("approve", False), data.get("comment", ""), data.get("bypass_reason", ""))


class AssetLoanDeliveryForm(InventoryForm):
    delivered_at = forms.DateTimeField(label="Fecha de entrega", widget=DATETIME_WIDGET, initial=timezone.now)
    delivery_condition = forms.ChoiceField(label="Condición física al entregar", choices=PhysicalCondition.choices)
    notes = forms.CharField(label="Observaciones de entrega", required=False, widget=forms.Textarea(attrs={"rows": 3}))

    def to_dto(self):
        data = self.require_cleaned_data()
        return DeliverAssetLoanDTO(data["delivered_at"], data["delivery_condition"], data.get("notes", ""))


class AssetLoanReturnRequestForm(InventoryForm):
    requested_at = forms.DateTimeField(label="Fecha de solicitud de devolución", widget=DATETIME_WIDGET, initial=timezone.now)
    notes = forms.CharField(label="Observaciones", required=False, widget=forms.Textarea(attrs={"rows": 2}))

    def to_dto(self):
        data = self.require_cleaned_data()
        return RequestLoanReturnDTO(data["requested_at"], data.get("notes", ""))


class AssetLoanReturnForm(InventoryForm):
    returned_at = forms.DateTimeField(label="Fecha de devolución", widget=DATETIME_WIDGET, initial=timezone.now)
    return_condition = forms.ChoiceField(label="Condición física al devolver", choices=PhysicalCondition.choices)
    returned_by_id = UUIDChoiceField(label="Persona que devuelve el bien")
    notes = forms.CharField(label="Observaciones de devolución", required=False, widget=forms.Textarea(attrs={"rows": 3}))

    def to_dto(self):
        data = self.require_cleaned_data()
        return ReturnAssetLoanDTO(data["returned_at"], data["return_condition"], data["returned_by_id"], data.get("notes", ""))


class AssetLoanCancelForm(InventoryForm):
    reason = forms.CharField(label="Motivo de cancelación", widget=forms.Textarea(attrs={"rows": 3}))
    bypass_reason = forms.CharField(label="Motivo de excepción", required=False)

    def to_dto(self):
        data = self.require_cleaned_data()
        return CancelAssetLoanDTO(data["reason"], data.get("bypass_reason", ""))


__all__ = [name for name in globals() if name.endswith("Form") and name != "InventoryForm"]
