# apps/inventory/models/audit_models.py

from django.conf import settings
from django.db import models

from apps.inventory.models.catalog_models import InventoryBaseModel


class PhysicalAuditStatus(models.TextChoices):
    DRAFT = "DRAFT", "Borrador"
    IN_PROGRESS = "IN_PROGRESS", "En Proceso"
    CLOSED = "CLOSED", "Cerrada"
    CANCELLED = "CANCELLED", "Cancelada"


class PhysicalAuditResult(models.TextChoices):
    FOUND = "FOUND", "Encontrado"
    NOT_FOUND = "NOT_FOUND", "No Encontrado"
    FOUND_DIFFERENT_LOCATION = (
        "FOUND_DIFFERENT_LOCATION",
        "Encontrado en Ubicación Diferente",
    )
    DAMAGED = "DAMAGED", "Encontrado con Daño"
    UNREGISTERED = "UNREGISTERED", "Sobrante No Registrado"


class PhysicalAuditSession(InventoryBaseModel):
    """
    Levantamiento físico de inventario.

    Permite comparar lo registrado en sistema contra lo encontrado físicamente.
    """

    folio = models.CharField(
        "Folio de auditoría física",
        max_length=80,
        unique=True,
    )
    name = models.CharField(
        "Nombre de auditoría",
        max_length=180,
    )
    status = models.CharField(
        "Estado",
        max_length=30,
        choices=PhysicalAuditStatus.choices,
        default=PhysicalAuditStatus.DRAFT,
    )

    sede = models.ForeignKey(
        "security.Sede",
        on_delete=models.PROTECT,
        related_name="inventory_audit_sessions",
        null=True,
        blank=True,
    )
    dependencia = models.ForeignKey(
        "security.Dependencia",
        on_delete=models.PROTECT,
        related_name="inventory_audit_sessions",
        null=True,
        blank=True,
    )
    area = models.ForeignKey(
        "security.AreaOperativa",
        on_delete=models.PROTECT,
        related_name="inventory_audit_sessions",
        null=True,
        blank=True,
    )

    started_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_audits_started",
    )
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_audits_closed",
        null=True,
        blank=True,
    )

    started_at = models.DateTimeField(
        "Inicio",
        null=True,
        blank=True,
    )
    closed_at = models.DateTimeField(
        "Cierre",
        null=True,
        blank=True,
    )
    notes = models.TextField(
        "Notas",
        blank=True,
    )

    class Meta:
        db_table = "inventory_physical_audit_sessions"
        verbose_name = "Auditoría física"
        verbose_name_plural = "Auditorías físicas"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["folio"]),
            models.Index(fields=["status"]),
            models.Index(fields=["sede"]),
            models.Index(fields=["dependencia"]),
            models.Index(fields=["area"]),
            models.Index(fields=["started_at"]),
            models.Index(fields=["closed_at"]),
        ]

    def save(self, *args, **kwargs):
        self.folio = self.folio.strip().upper()
        self.name = self.name.strip().upper()

        if self.notes:
            self.notes = self.notes.strip()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.folio} · {self.name}"


class PhysicalAuditItem(InventoryBaseModel):
    """
    Lectura individual dentro de una auditoría física.

    Puede apuntar a un activo registrado o guardar únicamente el número escaneado
    cuando se detecta un sobrante no registrado.
    """

    session = models.ForeignKey(
        PhysicalAuditSession,
        on_delete=models.CASCADE,
        related_name="items",
    )
    asset = models.ForeignKey(
        "inventory.Asset",
        on_delete=models.PROTECT,
        related_name="physical_audit_items",
        null=True,
        blank=True,
    )
    scanned_inventory_number = models.CharField(
        "Número escaneado",
        max_length=100,
        blank=True,
        help_text="Puede ser folio oficial, folio interno, folio anterior, QR o código de barras.",
    )
    result = models.CharField(
        "Resultado",
        max_length=40,
        choices=PhysicalAuditResult.choices,
    )
    scanned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_audit_items_scanned",
    )
    scanned_at = models.DateTimeField(
        "Fecha de lectura",
        auto_now_add=True,
    )

    latitude = models.DecimalField(
        "Latitud",
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
    )
    longitude = models.DecimalField(
        "Longitud",
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
    )
    notes = models.TextField(
        "Notas",
        blank=True,
    )

    class Meta:
        db_table = "inventory_physical_audit_items"
        verbose_name = "Lectura de auditoría física"
        verbose_name_plural = "Lecturas de auditoría física"
        ordering = ["-scanned_at"]
        indexes = [
            models.Index(fields=["session"]),
            models.Index(fields=["asset"]),
            models.Index(fields=["scanned_inventory_number"]),
            models.Index(fields=["result"]),
            models.Index(fields=["scanned_by"]),
            models.Index(fields=["scanned_at"]),
        ]

    def save(self, *args, **kwargs):
        if self.scanned_inventory_number:
            self.scanned_inventory_number = self.scanned_inventory_number.strip().upper()

        if self.notes:
            self.notes = self.notes.strip()

        super().save(*args, **kwargs)

    def __str__(self):
        target = (
            self.asset.display_inventory_number
            if self.asset
            else self.scanned_inventory_number or "SIN-LECTURA"
        )

        return f"{self.session.folio} · {target} · {self.get_result_display()}"


class InventoryAuditLog(InventoryBaseModel):
    """
    Auditoría interna del módulo Inventory.

    Registra mutaciones relevantes del expediente patrimonial:
    altas, cambios, resguardos, movimientos, bajas, auditorías físicas,
    documentos, fotos y procesos financieros.
    """

    action_type = models.CharField(
        "Acción",
        max_length=80,
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_audit_logs",
        null=True,
        blank=True,
    )
    asset = models.ForeignKey(
        "inventory.Asset",
        on_delete=models.PROTECT,
        related_name="audit_logs",
        null=True,
        blank=True,
    )
    target_model = models.CharField(
        "Modelo objetivo",
        max_length=120,
        blank=True,
    )
    target_id = models.CharField(
        "ID objetivo",
        max_length=120,
        blank=True,
    )
    summary = models.CharField(
        "Resumen",
        max_length=255,
    )
    old_value = models.JSONField(
        "Valor anterior",
        default=dict,
        blank=True,
    )
    new_value = models.JSONField(
        "Valor nuevo",
        default=dict,
        blank=True,
    )
    ip_address = models.GenericIPAddressField(
        "IP",
        null=True,
        blank=True,
    )
    user_agent = models.TextField(
        "User Agent",
        blank=True,
    )

    class Meta:
        db_table = "inventory_audit_logs"
        verbose_name = "Bitácora de inventario"
        verbose_name_plural = "Bitácora de inventario"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["action_type"]),
            models.Index(fields=["asset"]),
            models.Index(fields=["actor"]),
            models.Index(fields=["target_model", "target_id"]),
            models.Index(fields=["created_at"]),
        ]

    def save(self, *args, **kwargs):
        self.action_type = self.action_type.strip().upper()
        self.summary = self.summary.strip()

        if self.target_model:
            self.target_model = self.target_model.strip()

        if self.target_id:
            self.target_id = self.target_id.strip()

        if self.user_agent:
            self.user_agent = self.user_agent.strip()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.action_type} · {self.summary}"
    
