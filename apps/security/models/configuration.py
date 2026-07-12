# apps/security/models/configuration.py

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from apps.shared.models import AxentraBaseModel


class OfficialParameter(AxentraBaseModel):
    """
    Parámetros oficiales anuales o institucionales usados por Axentra OS.

    Ejemplos:
    - UMA 2026
    - Salario mínimo 2026
    - Factor de actualización
    - Parámetro municipal personalizado

    Este modelo vive en Core/Security porque estos valores pueden ser usados por
    varios módulos: Inventario, Predial, Catastro, Comercio, Tesorería, Multas, etc.
    """

    class ParameterType(models.TextChoices):
        UMA = "UMA", "Unidad de Medida y Actualización"
        MINIMUM_WAGE = "MINIMUM_WAGE", "Salario Mínimo"
        UPDATE_FACTOR = "UPDATE_FACTOR", "Factor de Actualización"
        SURCHARGE_RATE = "SURCHARGE_RATE", "Tasa de Recargo"
        DISCOUNT_RATE = "DISCOUNT_RATE", "Tasa de Descuento"
        CUSTOM = "CUSTOM", "Parámetro Personalizado"

    parameter_type = models.CharField(
        "Tipo de parámetro",
        max_length=50,
        choices=ParameterType.choices,
        db_index=True,
        help_text="Tipo de parámetro oficial. Ejemplo: UMA.",
    )

    year = models.PositiveIntegerField(
        "Año",
        db_index=True,
        help_text="Año fiscal o ejercicio aplicable. Ejemplo: 2026.",
    )

    name = models.CharField(
        "Nombre",
        max_length=150,
        help_text="Nombre descriptivo del parámetro. Ejemplo: UMA 2026.",
    )

    code = models.CharField(
        "Código interno",
        max_length=80,
        blank=True,
        db_index=True,
        help_text="Código interno opcional. Ejemplo: UMA_2026.",
    )

    value = models.DecimalField(
        "Valor",
        max_digits=14,
        decimal_places=4,
        help_text="Valor numérico del parámetro.",
    )

    unit = models.CharField(
        "Unidad",
        max_length=50,
        default="MXN",
        help_text="Unidad del valor. Ejemplo: MXN, %, FACTOR.",
    )

    valid_from = models.DateField(
        "Vigente desde",
        null=True,
        blank=True,
    )

    valid_to = models.DateField(
        "Vigente hasta",
        null=True,
        blank=True,
    )

    source = models.CharField(
        "Fuente oficial",
        max_length=255,
        blank=True,
        help_text="Referencia o fuente oficial del parámetro.",
    )

    notes = models.TextField(
        "Notas",
        blank=True,
    )

    class Meta:
        db_table = "axentra_core_official_parameters"
        verbose_name = "Parámetro oficial"
        verbose_name_plural = "Parámetros oficiales"
        ordering = [
            "-year",
            "parameter_type",
            "name",
        ]
        indexes = [
            models.Index(fields=["parameter_type"]),
            models.Index(fields=["year"]),
            models.Index(fields=["code"]),
            models.Index(fields=["parameter_type", "year"]),
            models.Index(fields=["is_active", "is_deleted"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["parameter_type", "year"],
                condition=models.Q(is_deleted=False),
                name="uq_official_parameter_type_year_active",
            ),
        ]

    def clean(self):
        if self.year < 1900:
            raise ValidationError(
                {
                    "year": "El año del parámetro oficial no es válido.",
                }
            )

        if self.value is None:
            raise ValidationError(
                {
                    "value": "El valor del parámetro oficial es obligatorio.",
                }
            )

        if self.value < Decimal("0"):
            raise ValidationError(
                {
                    "value": "El valor del parámetro oficial no puede ser negativo.",
                }
            )

        if self.valid_from and self.valid_to and self.valid_to < self.valid_from:
            raise ValidationError(
                {
                    "valid_to": "La fecha final de vigencia no puede ser anterior a la fecha inicial.",
                }
            )

    def save(self, *args, **kwargs):
        if self.name:
            self.name = self.name.strip().upper()

        if self.code:
            self.code = self.code.strip().upper()
        else:
            self.code = f"{self.parameter_type}_{self.year}".upper()

        if self.unit:
            self.unit = self.unit.strip().upper()

        if self.source:
            self.source = self.source.strip()

        if self.notes:
            self.notes = self.notes.strip()

        self.full_clean()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_parameter_type_display()} {self.year}: {self.value} {self.unit}"

    @property
    def display_value(self):
        if self.unit == "MXN":
            return f"${self.value:,.4f}"

        if self.unit == "%":
            return f"{self.value:,.4f}%"

        return f"{self.value:,.4f} {self.unit}"

    @classmethod
    def get_uma_for_year(cls, year: int):
        """
        Devuelve la UMA activa de un año específico.

        Uso:
            uma = OfficialParameter.get_uma_for_year(2026)
        """

        return cls.objects.get(
            parameter_type=cls.ParameterType.UMA,
            year=year,
            is_active=True,
            is_deleted=False,
        )

    @classmethod
    def get_value(cls, parameter_type: str, year: int):
        """
        Devuelve sólo el valor numérico de un parámetro.

        Uso:
            valor_uma = OfficialParameter.get_value(
                OfficialParameter.ParameterType.UMA,
                2026,
            )
        """

        parameter = cls.objects.get(
            parameter_type=parameter_type,
            year=year,
            is_active=True,
            is_deleted=False,
        )

        return parameter.value
    
