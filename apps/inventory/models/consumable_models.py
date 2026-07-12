# apps/inventory/models/consumable_models.py

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.inventory.models.catalog_models import InventoryBaseModel


class Consumable(InventoryBaseModel):
    """
    Insumos, refacciones y consumibles.

    No todos son activo fijo.
    Ejemplos:
    tóner, tinta, cables, mouse barato, teclado, refacción.
    """

    code = models.CharField(
        "Código de almacén",
        max_length=80,
        unique=True,
    )
    name = models.CharField(
        "Descripción",
        max_length=255,
    )
    dependencia = models.ForeignKey(
        "security.Dependencia",
        on_delete=models.PROTECT,
        related_name="inventory_consumables",
    )
    sede = models.ForeignKey(
        "security.Sede",
        on_delete=models.PROTECT,
        related_name="inventory_consumables",
        null=True,
        blank=True,
    )

    stock_actual = models.IntegerField(
        "Existencia actual",
        default=0,
    )
    stock_minimo = models.IntegerField(
        "Stock mínimo",
        default=0,
    )
    unit = models.CharField(
        "Unidad",
        max_length=50,
        default="PIEZA",
    )

    class Meta:
        db_table = "inventory_consumables"
        ordering = ["name"]

    def clean(self):
        if self.stock_actual < 0:
            raise ValidationError(
                {
                    "stock_actual": "El stock actual no puede ser negativo."
                }
            )

        if self.stock_minimo < 0:
            raise ValidationError(
                {
                    "stock_minimo": "El stock mínimo no puede ser negativo."
                }
            )

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        self.name = self.name.strip().upper()
        self.unit = self.unit.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} · {self.name}"


class ConsumableMovementType(models.TextChoices):
    ENTRY = "ENTRY", "Entrada"
    EXIT = "EXIT", "Salida"
    ADJUSTMENT = "ADJUSTMENT", "Ajuste"


class ConsumableMovement(InventoryBaseModel):
    """
    Movimiento de consumible.

    No actualiza stock en save().
    Eso lo hará ConsumableService con transaction.atomic().
    """

    consumable = models.ForeignKey(
        Consumable,
        on_delete=models.PROTECT,
        related_name="movements",
    )
    movement_type = models.CharField(
        "Tipo de movimiento",
        max_length=20,
        choices=ConsumableMovementType.choices,
    )
    quantity = models.PositiveIntegerField(
        "Cantidad",
    )
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_consumable_movements",
    )

    related_asset = models.ForeignKey(
        "inventory.Asset",
        on_delete=models.PROTECT,
        related_name="consumable_movements",
        null=True,
        blank=True,
    )

    reason = models.TextField(
        "Justificación",
    )
    reference = models.CharField(
        "Referencia",
        max_length=120,
        blank=True,
    )

    class Meta:
        db_table = "inventory_consumable_movements"
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        self.reason = self.reason.strip()
        if self.reference:
            self.reference = self.reference.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.consumable.code} · {self.get_movement_type_display()} · {self.quantity}"