# apps/inventory/models/catalog_models.py

import uuid

from django.db import models


class InventoryBaseModel(models.Model):
    """
    Base local para Inventory.

    No usamos save() para lógica crítica.
    Las mutaciones importantes vivirán en services/.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AssetNature(models.TextChoices):
    MOVABLE = "MOVABLE", "Bien Mueble"
    IMMOVABLE = "IMMOVABLE", "Bien Inmueble"
    INTANGIBLE = "INTANGIBLE", "Bien Intangible"


class AssetControlType(models.TextChoices):
    CAPITALIZED_ASSET = "CAPITALIZED_ASSET", "Activo Fijo Capitalizado"
    INTERNAL_CONTROL = "INTERNAL_CONTROL", "Control Interno"
    CONSUMABLE = "CONSUMABLE", "Consumible / Insumo"


class AssetLifecycleStatus(models.TextChoices):
    DRAFT = "DRAFT", "Borrador"
    REGISTERED = "REGISTERED", "Registrado"
    IN_STOCK = "IN_STOCK", "En Almacén / Bodega"
    ASSIGNED = "ASSIGNED", "En Resguardo"
    IN_USE = "IN_USE", "En Uso"
    IN_MAINTENANCE = "IN_MAINTENANCE", "En Mantenimiento"
    LOANED = "LOANED", "En Préstamo"
    PENDING_DISPOSAL = "PENDING_DISPOSAL", "Pendiente de Baja"
    DISPOSED = "DISPOSED", "Dado de Baja"
    LOST = "LOST", "Extraviado"
    STOLEN = "STOLEN", "Robado"
    DAMAGED = "DAMAGED", "Dañado"
    ARCHIVED = "ARCHIVED", "Archivado"


class PhysicalCondition(models.TextChoices):
    NEW = "NEW", "Nuevo"
    GOOD = "GOOD", "Bueno"
    REGULAR = "REGULAR", "Regular"
    BAD = "BAD", "Malo"
    UNSERVICEABLE = "UNSERVICEABLE", "Inservible"


class AcquisitionType(models.TextChoices):
    PURCHASE = "PURCHASE", "Compra"
    DONATION = "DONATION", "Donación"
    PUBLIC_WORK = "PUBLIC_WORK", "Obra Pública"
    TRANSFER = "TRANSFER", "Transferencia"
    REGULARIZATION = "REGULARIZATION", "Regularización"
    POSITIVE_PRESCRIPTION = "POSITIVE_PRESCRIPTION", "Prescripción Positiva"
    UNKNOWN = "UNKNOWN", "Origen No Documentado"


class MovementType(models.TextChoices):
    REGISTRATION = "REGISTRATION", "Alta"
    ASSIGNMENT = "ASSIGNMENT", "Asignación"
    REASSIGNMENT = "REASSIGNMENT", "Reasignación"
    LOAN = "LOAN", "Préstamo"
    RETURN = "RETURN", "Devolución"
    LOCATION_CHANGE = "LOCATION_CHANGE", "Cambio de Ubicación"
    MAINTENANCE_OUT = "MAINTENANCE_OUT", "Salida a Mantenimiento"
    MAINTENANCE_IN = "MAINTENANCE_IN", "Retorno de Mantenimiento"
    DISPOSAL_REQUEST = "DISPOSAL_REQUEST", "Solicitud de Baja"
    DISPOSAL_APPROVED = "DISPOSAL_APPROVED", "Baja Aprobada"
    DISPOSAL_REJECTED = "DISPOSAL_REJECTED", "Baja Rechazada"
    PHYSICAL_AUDIT = "PHYSICAL_AUDIT", "Auditoría Física"
    ADJUSTMENT = "ADJUSTMENT", "Ajuste Administrativo"


class DisposalReason(models.TextChoices):
    OBSOLESCENCE = "OBSOLESCENCE", "Obsolescencia"
    DAMAGE = "DAMAGE", "Daño Irreparable"
    THEFT = "THEFT", "Robo"
    LOSS = "LOSS", "Extravío"
    DISASTER = "DISASTER", "Siniestro"
    SCRAP = "SCRAP", "Desecho / Chatarra"
    DONATION = "DONATION", "Donación / Transferencia"
    SALE = "SALE", "Enajenación / Venta"
    LEGAL_DISINCORPORATION = "LEGAL_DISINCORPORATION", "Desincorporación Legal"


class DocumentType(models.TextChoices):
    INVOICE_XML = "INVOICE_XML", "Factura XML"
    INVOICE_PDF = "INVOICE_PDF", "Factura PDF"
    PURCHASE_ORDER = "PURCHASE_ORDER", "Orden de Compra"
    CONTRACT = "CONTRACT", "Contrato"
    WARRANTY = "WARRANTY", "Garantía"
    CUSTODY_RECEIPT = "CUSTODY_RECEIPT", "Vale de Resguardo"
    SIGNED_CUSTODY_RECEIPT = "SIGNED_CUSTODY_RECEIPT", "Vale de Resguardo Firmado"
    TECHNICAL_REPORT = "TECHNICAL_REPORT", "Dictamen Técnico"
    DISPOSAL_REQUEST = "DISPOSAL_REQUEST", "Oficio de Solicitud de Baja"
    DISPOSAL_MINUTES = "DISPOSAL_MINUTES", "Acta Circunstanciada"
    POLICE_REPORT = "POLICE_REPORT", "Acta / Denuncia MP"
    PHOTO_FRONT = "PHOTO_FRONT", "Foto Frontal"
    PHOTO_SERIAL = "PHOTO_SERIAL", "Foto Serie / Placa"
    PHOTO_CONDITION = "PHOTO_CONDITION", "Foto Estado General"
    DEED = "DEED", "Escritura / Título"
    CADASTRAL_CERTIFICATE = "CADASTRAL_CERTIFICATE", "Cédula / Clave Catastral"
    OTHER = "OTHER", "Otro Documento"


class RelationType(models.TextChoices):
    INCLUDES = "INCLUDES", "Incluye / Contiene"
    CONNECTED_TO = "CONNECTED_TO", "Conectado a"
    DEPENDS_ON = "DEPENDS_ON", "Depende de"
    ASSIGNED_WITH = "ASSIGNED_WITH", "Asignado con"
    REPLACES = "REPLACES", "Reemplaza a"
    PART_OF = "PART_OF", "Parte de"
    USES_SERVICE = "USES_SERVICE", "Usa Servicio"
    BACKS_UP = "BACKS_UP", "Respalda a"


class AssetCategory(InventoryBaseModel):
    """
    Categoría patrimonial alineada a CONAC / control municipal.

    Ejemplos:
    - Mobiliario y Equipo de Administración
    - Equipo de Cómputo y Tecnologías de Información
    - Vehículos y Equipo de Transporte
    - Bienes Inmuebles
    - Licencias de Software
    """

    code = models.CharField(
        "Código interno",
        max_length=50,
        unique=True,
    )
    name = models.CharField(
        "Nombre de categoría",
        max_length=180,
        unique=True,
    )
    nature = models.CharField(
        "Naturaleza",
        max_length=20,
        choices=AssetNature.choices,
    )
    description = models.TextField(
        "Descripción",
        blank=True,
    )

    class Meta:
        db_table = "inventory_asset_categories"
        ordering = ["nature", "name"]

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        self.name = self.name.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} · {self.name}"


class AccountingAccount(InventoryBaseModel):
    """
    Cuenta contable armonizada.

    Ejemplos:
    1.2.4.1.1 Muebles de Oficina y Estantería
    1.2.4.1.3 Equipo de Cómputo y Tecnologías de Información
    1.2.6.3 Depreciación Acumulada de Bienes Muebles
    """

    code = models.CharField(
        "Código de cuenta",
        max_length=50,
        unique=True,
    )
    name = models.CharField(
        "Nombre de cuenta",
        max_length=255,
    )
    category = models.ForeignKey(
        AssetCategory,
        on_delete=models.PROTECT,
        related_name="accounting_accounts",
        null=True,
        blank=True,
    )
    is_depreciable = models.BooleanField(
        "Es depreciable",
        default=True,
    )
    default_useful_life_months = models.PositiveIntegerField(
        "Vida útil predeterminada en meses",
        null=True,
        blank=True,
    )
    default_annual_depreciation_rate = models.DecimalField(
        "Tasa anual de depreciación",
        max_digits=6,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Ejemplo: 33.300 para 33.3%",
    )

    class Meta:
        db_table = "inventory_accounting_accounts"
        ordering = ["code"]

    def save(self, *args, **kwargs):
        self.code = self.code.strip()
        self.name = self.name.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} · {self.name}"


class Manufacturer(InventoryBaseModel):
    name = models.CharField(
        "Fabricante",
        max_length=120,
        unique=True,
    )

    class Meta:
        db_table = "inventory_manufacturers"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        self.name = self.name.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class AssetModel(InventoryBaseModel):
    manufacturer = models.ForeignKey(
        Manufacturer,
        on_delete=models.PROTECT,
        related_name="asset_models",
    )
    name = models.CharField(
        "Modelo",
        max_length=160,
    )
    description = models.TextField(
        "Descripción",
        blank=True,
    )

    class Meta:
        db_table = "inventory_asset_models"
        unique_together = ("manufacturer", "name")
        ordering = ["manufacturer__name", "name"]

    def save(self, *args, **kwargs):
        self.name = self.name.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.manufacturer.name} · {self.name}"


class Supplier(InventoryBaseModel):
    razon_social = models.CharField(
        "Razón social",
        max_length=255,
        unique=True,
    )
    rfc = models.CharField(
        "RFC",
        max_length=13,
        unique=True,
        null=True,
        blank=True,
    )
    contacto_nombre = models.CharField(
        "Contacto",
        max_length=150,
        blank=True,
    )
    telefono = models.CharField(
        "Teléfono",
        max_length=30,
        blank=True,
    )
    email = models.EmailField(
        "Correo",
        blank=True,
    )

    class Meta:
        db_table = "inventory_suppliers"
        ordering = ["razon_social"]

    def save(self, *args, **kwargs):
        self.razon_social = self.razon_social.strip().upper()
        if self.rfc:
            self.rfc = self.rfc.strip().upper()
        if self.contacto_nombre:
            self.contacto_nombre = self.contacto_nombre.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.razon_social


class Contract(InventoryBaseModel):
    numero_contrato = models.CharField(
        "Número de contrato / licitación",
        max_length=120,
        unique=True,
    )
    nombre = models.CharField(
        "Objeto del contrato",
        max_length=255,
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name="contracts",
    )
    fecha_inicio = models.DateField(
        "Fecha de inicio",
        null=True,
        blank=True,
    )
    fecha_fin = models.DateField(
        "Fecha de vencimiento",
        null=True,
        blank=True,
    )
    monto_total = models.DecimalField(
        "Monto total",
        max_digits=16,
        decimal_places=2,
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "inventory_contracts"
        ordering = ["-fecha_inicio", "numero_contrato"]

    def save(self, *args, **kwargs):
        self.numero_contrato = self.numero_contrato.strip().upper()
        self.nombre = self.nombre.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.numero_contrato} · {self.nombre}"