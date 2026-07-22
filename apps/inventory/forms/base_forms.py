from uuid import UUID

from django import forms

from apps.inventory.forms.base_styler import AxentraFormStylerMixin


class UUIDChoiceField(forms.ChoiceField):
    def __init__(self, *args, **kwargs):
        self.allow_empty = not kwargs.get("required", True)
        super().__init__(*args, **kwargs)

    def clean(self, value):
        configured_values = {
            str(choice[0])
            for choice in self.choices
            if choice[0] not in self.empty_values
        }

        if configured_values:
            value = super().clean(value)
        else:
            value = forms.Field.clean(self, value)
        if value in self.empty_values:
            return None
        try:
            return UUID(str(value))
        except (TypeError, ValueError, AttributeError) as exc:
            raise forms.ValidationError(
                "Seleccione una opción válida."
            ) from exc


class InventoryFormMixin(AxentraFormStylerMixin):
    spanish_labels = {
        "approve": "Aprobar", "comment": "Comentario",
        "bypass_reason": "Motivo de excepción", "reason": "Justificación",
        "notes": "Notas", "name": "Nombre", "description": "Descripción",
        "status": "Estado", "result": "Resultado", "file": "Archivo",
        "image": "Imagen", "caption": "Descripción de la imagen",
        "owner_type": "Tipo de expediente", "owner_id": "Expediente relacionado",
        "photo_type": "Tipo de fotografía", "latitude": "Latitud",
        "longitude": "Longitud", "period_year": "Ejercicio fiscal",
        "period_month": "Mes", "period_start": "Inicio del periodo",
        "period_end": "Fin del periodo", "cutoff_at": "Fecha de corte",
        "source_file": "Archivo de origen", "source_system": "Sistema de origen",
        "destination_system": "Sistema de destino", "file_format": "Formato del archivo",
        "export_type": "Tipo de exportación", "closing_notes": "Conclusiones de cierre",
        "posting_reference": "Referencia contable", "occurred_at": "Fecha del movimiento",
        "physical_condition": "Condición física", "operational_status": "Estado operativo",
        "serial_number": "Número de serie", "acquisition_cost": "Costo de adquisición",
        "residual_value": "Valor residual", "useful_life_months": "Vida útil en meses",
        "acquisition_date": "Fecha de adquisición", "reception_date": "Fecha de recepción",
        "acquisition_type": "Tipo de adquisición", "service_order_id": "Orden de servicio",
        "service_order_folio": "Folio de la orden de servicio", "asset_id": "Bien patrimonial",
    }
    core_choice_fields = {
        "department_id": "department_choices",
        "requested_department_id": "department_choices",
        "destination_department_id": "department_choices",
        "origin_department_id": "department_choices",
        "observed_department_id": "department_choices",
        "site_id": "site_choices",
        "requested_site_id": "site_choices",
        "destination_site_id": "site_choices",
        "origin_site_id": "site_choices",
        "observed_site_id": "site_choices",
        "area_id": "area_choices",
        "requested_area_id": "area_choices",
        "destination_area_id": "area_choices",
        "origin_area_id": "area_choices",
        "observed_area_id": "area_choices",
        "user_id": "user_choices",
        "custodian_id": "user_choices",
        "proposed_custodian_id": "user_choices",
        "assigned_to_id": "user_choices",
        "borrower_id": "user_choices",
        "returned_by_id": "user_choices",
        "observed_custodian_id": "user_choices",
    }

    def __init__(self, *args, **kwargs):
        choice_sets = {
            key: kwargs.pop(key, ())
            for key in set(self.core_choice_fields.values())
        }
        super().__init__(*args, **kwargs)

        for field_name, field in self.fields.items():
            if field_name in self.spanish_labels and (
                not field.label
                or field.label == field_name.replace("_", " ").capitalize()
            ):
                field.label = self.spanish_labels[field_name]

        for field_name, choices_name in self.core_choice_fields.items():
            if field_name in self.fields:
                self.fields[field_name].choices = [
                    ("", "--- Seleccione ---"),
                    *list(choice_sets[choices_name]),
                ]

        self.aplicar_estilos_institucionales()

    def require_cleaned_data(self):
        if not hasattr(self, "cleaned_data") or self.errors:
            raise RuntimeError(
                "Debe ejecutar is_valid() antes de to_dto()."
            )
        return self.cleaned_data


class InventoryForm(InventoryFormMixin, forms.Form):
    pass


DATE_WIDGET = forms.DateInput(attrs={"type": "date"})
DATETIME_WIDGET = forms.DateTimeInput(
    attrs={"type": "datetime-local"},
    format="%Y-%m-%dT%H:%M",
)


__all__ = [
    "DATE_WIDGET",
    "DATETIME_WIDGET",
    "InventoryForm",
    "InventoryFormMixin",
    "UUIDChoiceField",
]
