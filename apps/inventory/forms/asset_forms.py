# apps/inventory/forms/asset_forms.py

"""
Formulario general del activo para desarrollo.

Utiliza todos los campos editables del modelo Asset para evitar que el
formulario quede desactualizado mientras se estabilizan modelos y migraciones.

IMPORTANTE:
La creación oficial de activos deberá realizarse posteriormente mediante
AssetIntakeRequest y los services del flujo de aprobación, no mediante
AssetForm.save() directamente.
"""

from django import forms
from django.db import models
from django.utils import timezone

from apps.inventory.forms.base_styler import AxentraFormStylerMixin
from apps.inventory.models import Asset


class AssetForm(AxentraFormStylerMixin, forms.ModelForm):
    """
    Formulario completo de desarrollo para Asset.

    `fields = "__all__"` evita referencias a campos eliminados, como el antiguo
    lifecycle_status, y agrega automáticamente los nuevos campos del modelo.
    """

    class Meta:
        model = Asset
        fields = "__all__"

        widgets = {
            "official_inventory_number": forms.TextInput(
                attrs={
                    "placeholder": "Generado automáticamente",
                    "autocomplete": "off",
                }
            ),
            "internal_inventory_number": forms.TextInput(
                attrs={
                    "placeholder": "Generado automáticamente",
                    "autocomplete": "off",
                }
            ),
            "legacy_inventory_number": forms.TextInput(
                attrs={
                    "placeholder": "Número anterior, si existe",
                    "autocomplete": "off",
                }
            ),
            "name": forms.TextInput(
                attrs={
                    "placeholder": "Nombre corto del activo",
                    "autocomplete": "off",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "Descripción detallada del activo",
                }
            ),
            "serial_number": forms.TextInput(
                attrs={
                    "placeholder": "Número de serie o Service Tag",
                    "autocomplete": "off",
                }
            ),
            "acquisition_date": forms.DateInput(
                attrs={"type": "date"}
            ),
            "registration_date": forms.DateInput(
                attrs={"type": "date"}
            ),
            "notes": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "Notas internas del expediente",
                }
            ),
            "extra_attributes": forms.Textarea(
                attrs={
                    "rows": 5,
                    "class": "font-monospace",
                    "placeholder": '{"campo": "valor"}',
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._configure_initial_values()
        self._configure_querysets()
        self._configure_system_fields()

        self.aplicar_estilos_institucionales()

    def _configure_initial_values(self):
        """
        Establece fechas iniciales cuando los campos existen.
        """

        today = timezone.localdate()

        if (
            "registration_date" in self.fields
            and not self.initial.get("registration_date")
            and not getattr(self.instance, "registration_date", None)
        ):
            self.fields["registration_date"].initial = today

    def _configure_querysets(self):
        """
        Filtra automáticamente relaciones hacia modelos con borrado lógico.

        Esto evita importar directamente todos los catálogos y mantiene
        desacoplado el formulario.
        """

        for field_name, form_field in self.fields.items():
            if not isinstance(
                form_field,
                (
                    forms.ModelChoiceField,
                    forms.ModelMultipleChoiceField,
                ),
            ):
                continue

            queryset = form_field.queryset
            related_model = queryset.model

            related_field_names = {
                field.name
                for field in related_model._meta.concrete_fields
            }

            filters = {}

            if "is_active" in related_field_names:
                filters["is_active"] = True

            if "is_deleted" in related_field_names:
                filters["is_deleted"] = False

            if filters:
                queryset = queryset.filter(**filters)

            ordering = self._get_related_ordering(related_model)

            if ordering:
                queryset = queryset.order_by(*ordering)

            form_field.queryset = queryset
            form_field.empty_label = self._get_empty_label(
                field_name,
                form_field,
            )

    def _get_related_ordering(self, related_model):
        """
        Determina un orden legible sin asumir nombres obligatorios.
        """

        field_names = {
            field.name
            for field in related_model._meta.concrete_fields
        }

        if "code" in field_names and "name" in field_names:
            return ("code", "name")

        if "codigo_presupuestal" in field_names:
            return ("codigo_presupuestal",)

        if "nombre" in field_names:
            return ("nombre",)

        if "name" in field_names:
            return ("name",)

        if "razon_social" in field_names:
            return ("razon_social",)

        if "email" in field_names:
            return ("email",)

        return related_model._meta.ordering or ()

    def _get_empty_label(self, field_name, form_field):
        if form_field.required:
            return f"--- Seleccione {form_field.label.lower()} ---"

        return f"--- Sin {form_field.label.lower()} ---"

    def _configure_system_fields(self):
        """
        Identifica visualmente campos que serán administrados por services.

        No se deshabilitan en desarrollo para que puedas probarlos desde las
        pantallas internas. En producción deben excluirse del formulario.
        """

        system_fields = {
            "official_inventory_number",
            "internal_inventory_number",
            "source_intake_request",
            "patrimonial_status",
            "operational_status",
            "is_capitalizable",
            "capitalization_threshold_amount",
            "uma_value_snapshot",
            "uma_year_snapshot",
            "registered_by",
            "registered_at",
            "bypass_used",
            "bypass_reason",
        }

        for field_name in system_fields:
            if field_name not in self.fields:
                continue

            existing_help = self.fields[field_name].help_text or ""

            warning = (
                "Campo administrado normalmente por los servicios internos "
                "de Inventory."
            )

            self.fields[field_name].help_text = (
                f"{existing_help} {warning}".strip()
            )

    def clean(self):
        cleaned_data = super().clean()

        self._normalize_text_fields(cleaned_data)
        self._validate_model_relationships(cleaned_data)

        return cleaned_data

    def _normalize_text_fields(self, cleaned_data):
        """
        Normaliza identificadores y textos principales.
        """

        uppercase_fields = {
            "official_inventory_number",
            "internal_inventory_number",
            "legacy_inventory_number",
            "name",
            "serial_number",
        }

        strip_fields = {
            "description",
            "notes",
            "bypass_reason",
        }

        for field_name in uppercase_fields:
            value = cleaned_data.get(field_name)

            if isinstance(value, str):
                cleaned_data[field_name] = value.strip().upper()

        for field_name in strip_fields:
            value = cleaned_data.get(field_name)

            if isinstance(value, str):
                cleaned_data[field_name] = value.strip()

    def _validate_model_relationships(self, cleaned_data):
        """
        Valida relaciones organizacionales sin depender rígidamente de los
        nombres de los modelos de Security.
        """

        self._validate_location_group(
            cleaned_data=cleaned_data,
            dependencia_field="origin_dependencia",
            area_field="origin_area",
            sede_field="origin_sede",
        )

        self._validate_location_group(
            cleaned_data=cleaned_data,
            dependencia_field="current_dependencia",
            area_field="current_area",
            sede_field="current_sede",
        )

        # Compatibilidad temporal si el Asset conserva los nombres anteriores.
        self._validate_location_group(
            cleaned_data=cleaned_data,
            dependencia_field="dependencia",
            area_field="area",
            sede_field="sede",
        )

    def _validate_location_group(
        self,
        *,
        cleaned_data,
        dependencia_field,
        area_field,
        sede_field,
    ):
        dependencia = cleaned_data.get(dependencia_field)
        area = cleaned_data.get(area_field)
        sede = cleaned_data.get(sede_field)

        if not area:
            return

        area_dependencia_id = getattr(
            area,
            "dependencia_id",
            None,
        )
        area_sede_id = getattr(
            area,
            "sede_fisica_id",
            None,
        )

        if (
            dependencia
            and area_dependencia_id
            and area_dependencia_id != dependencia.pk
        ):
            self.add_error(
                area_field,
                "El área seleccionada no pertenece a la dependencia.",
            )

        if (
            sede
            and area_sede_id
            and area_sede_id != sede.pk
        ):
            self.add_error(
                sede_field,
                "La sede seleccionada no coincide con la sede del área.",
            )
            
