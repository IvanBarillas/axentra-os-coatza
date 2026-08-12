# apps/inventory/models/catalog_models.py

import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


# =============================================================================
# MODELO BASE AUTÓNOMO DE INVENTORY
# =============================================================================


class InventoryBaseModel(models.Model):
    """
    Modelo base autónomo del módulo Inventory.

    Inventory utiliza UUID para que sus entidades no dependan de consecutivos
    internos de otras aplicaciones. Las mutaciones importantes deben ejecutarse
    mediante servicios; este modelo sólo proporciona identidad, estado y
    trazabilidad básica.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    is_active = models.BooleanField(
        "Activo",
        default=True,
        db_index=True,
    )
    is_deleted = models.BooleanField(
        "Eliminado",
        default=False,
        db_index=True,
    )
    created_at = models.DateTimeField(
        "Creado",
        auto_now_add=True,
        db_index=True,
    )
    updated_at = models.DateTimeField(
        "Actualizado",
        auto_now=True,
    )
    deleted_at = models.DateTimeField(
        "Fecha de baja lógica",
        null=True,
        blank=True,
    )

    class Meta:
        abstract = True

    def soft_delete(self, *, save=True):
        """
        Aplica baja lógica.

        No debe utilizarse para movimientos, decisiones o eventos históricos
        append-only. Esas entidades requieren operaciones específicas.
        """
        self.is_active = False
        self.is_deleted = True
        self.deleted_at = timezone.now()

        if save:
            self.save(
                update_fields=[
                    "is_active",
                    "is_deleted",
                    "deleted_at",
                    "updated_at",
                ]
            )

    def restore(self, *, save=True):
        self.is_active = True
        self.is_deleted = False
        self.deleted_at = None

        if save:
            self.save(
                update_fields=[
                    "is_active",
                    "is_deleted",
                    "deleted_at",
                    "updated_at",
                ]
            )


# =============================================================================
# ENUMERACIONES TRANSVERSALES
# =============================================================================


class AssetNature(models.TextChoices):
    MOVABLE = "MOVABLE", "Bien Mueble"
    IMMOVABLE = "IMMOVABLE", "Bien Inmueble"
    INTANGIBLE = "INTANGIBLE", "Bien Intangible"


class AssetControlType(models.TextChoices):
    CAPITALIZED_ASSET = (
        "CAPITALIZED_ASSET",
        "Activo Fijo Capitalizado",
    )
    INTERNAL_CONTROL = (
        "INTERNAL_CONTROL",
        "Bien de Control Interno",
    )


class InventoryAssetTypeCode(models.TextChoices):
    BM = "BM", "Bien Mueble"
    BI = "BI", "Bien Inmueble"
    BP = "BP", "Bien Patrimonial de Control Interno"


class CapitalizationRule(models.TextChoices):
    UMA_THRESHOLD = (
        "UMA_THRESHOLD",
        "Aplicar umbral basado en UMA",
    )
    ALWAYS_CAPITALIZE = (
        "ALWAYS_CAPITALIZE",
        "Capitalizar siempre",
    )
    NEVER_CAPITALIZE = (
        "NEVER_CAPITALIZE",
        "No capitalizar",
    )
    MANUAL_REVIEW = (
        "MANUAL_REVIEW",
        "Requiere dictamen contable",
    )


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
    TRANSFER = "TRANSFER", "Transferencia recibida"
    COMMODATUM = "COMMODATUM", "Comodato"
    DATION_IN_PAYMENT = "DATION_IN_PAYMENT", "Dación en pago"
    ADJUDICATION = "ADJUDICATION", "Adjudicación"
    REGULARIZATION = "REGULARIZATION", "Regularización"
    POSITIVE_PRESCRIPTION = (
        "POSITIVE_PRESCRIPTION",
        "Prescripción positiva",
    )
    INVENTORY_SURPLUS = (
        "INVENTORY_SURPLUS",
        "Sobrante localizado",
    )
    UNKNOWN = "UNKNOWN", "Origen no documentado"


class MovementType(models.TextChoices):
    REGISTRATION = "REGISTRATION", "Alta patrimonial"
    ASSIGNMENT = "ASSIGNMENT", "Asignación"
    REASSIGNMENT = "REASSIGNMENT", "Reasignación"
    TRANSFER = "TRANSFER", "Transferencia definitiva"
    LOAN = "LOAN", "Préstamo temporal"
    RETURN = "RETURN", "Devolución"
    LOCATION_CHANGE = (
        "LOCATION_CHANGE",
        "Cambio de ubicación",
    )
    CUSTODY_CHANGE = (
        "CUSTODY_CHANGE",
        "Cambio de resguardatario",
    )
    MAINTENANCE_OUT = (
        "MAINTENANCE_OUT",
        "Salida a mantenimiento",
    )
    MAINTENANCE_IN = (
        "MAINTENANCE_IN",
        "Retorno de mantenimiento",
    )
    DIAGNOSIS_OUT = (
        "DIAGNOSIS_OUT",
        "Salida a diagnóstico",
    )
    DIAGNOSIS_IN = (
        "DIAGNOSIS_IN",
        "Retorno de diagnóstico",
    )
    DISPOSAL_REQUEST = (
        "DISPOSAL_REQUEST",
        "Solicitud de baja",
    )
    DISPOSAL_APPROVED = (
        "DISPOSAL_APPROVED",
        "Baja aprobada",
    )
    DISPOSAL_REJECTED = (
        "DISPOSAL_REJECTED",
        "Baja rechazada",
    )
    DISPOSAL_EXECUTED = (
        "DISPOSAL_EXECUTED",
        "Baja ejecutada",
    )
    PHYSICAL_AUDIT = (
        "PHYSICAL_AUDIT",
        "Auditoría física",
    )
    FOUND = "FOUND", "Activo localizado"
    NOT_FOUND = "NOT_FOUND", "Activo no localizado"
    ADJUSTMENT = (
        "ADJUSTMENT",
        "Ajuste administrativo",
    )
    CORRECTION = (
        "CORRECTION",
        "Corrección de movimiento",
    )


class DisposalReason(models.TextChoices):
    OBSOLESCENCE = "OBSOLESCENCE", "Obsolescencia"
    IRREPARABLE_DAMAGE = (
        "IRREPARABLE_DAMAGE",
        "Daño irreparable",
    )
    THEFT = "THEFT", "Robo"
    LOSS = "LOSS", "Extravío"
    DISASTER = "DISASTER", "Siniestro"
    SCRAP = "SCRAP", "Desecho / chatarra"
    DONATION = "DONATION", "Donación"
    TRANSFER = "TRANSFER", "Transferencia"
    SALE = "SALE", "Enajenación / venta"
    DESTRUCTION = "DESTRUCTION", "Destrucción autorizada"
    LEGAL_DISINCORPORATION = (
        "LEGAL_DISINCORPORATION",
        "Desincorporación legal",
    )
    OTHER = "OTHER", "Otro motivo autorizado"


class DocumentType(models.TextChoices):
    INVOICE_XML = "INVOICE_XML", "Factura XML"
    INVOICE_PDF = "INVOICE_PDF", "Factura PDF"
    PURCHASE_ORDER = (
        "PURCHASE_ORDER",
        "Orden de compra",
    )
    CONTRACT = "CONTRACT", "Contrato"
    WARRANTY = "WARRANTY", "Garantía"

    DELIVERY_RECEIPT = (
        "DELIVERY_RECEIPT",
        "Acta o constancia de entrega",
    )
    DEPARTMENT_ACCEPTANCE = (
        "DEPARTMENT_ACCEPTANCE",
        "Aceptación de la dependencia",
    )
    PATRIMONY_VALIDATION = (
        "PATRIMONY_VALIDATION",
        "Validación patrimonial",
    )

    DONATION_AGREEMENT = (
        "DONATION_AGREEMENT",
        "Acta o contrato de donación",
    )
    TECHNICAL_VALUATION = (
        "TECHNICAL_VALUATION",
        "Avalúo técnico",
    )
    COMMERCIAL_VALUATION = (
        "COMMERCIAL_VALUATION",
        "Estimación de valor comercial",
    )

    CUSTODY_RECEIPT = (
        "CUSTODY_RECEIPT",
        "Vale de resguardo generado",
    )
    SIGNED_CUSTODY_RECEIPT = (
        "SIGNED_CUSTODY_RECEIPT",
        "Acuse firmado de resguardo",
    )
    LOAN_RECEIPT = (
        "LOAN_RECEIPT",
        "Vale de préstamo generado",
    )
    SIGNED_LOAN_RECEIPT = (
        "SIGNED_LOAN_RECEIPT",
        "Acuse firmado de préstamo",
    )
    RETURN_RECEIPT = (
        "RETURN_RECEIPT",
        "Constancia de devolución generada",
    )
    SIGNED_RETURN_RECEIPT = (
        "SIGNED_RETURN_RECEIPT",
        "Acuse firmado de devolución",
    )
    TRANSFER_RECEIPT = (
        "TRANSFER_RECEIPT",
        "Acta de transferencia generada",
    )
    SIGNED_TRANSFER_RECEIPT = (
        "SIGNED_TRANSFER_RECEIPT",
        "Acuse firmado de transferencia",
    )

    TECHNICAL_DIAGNOSIS = (
        "TECHNICAL_DIAGNOSIS",
        "Diagnóstico técnico",
    )
    TECHNICAL_REPORT = (
        "TECHNICAL_REPORT",
        "Dictamen técnico",
    )
    TECHNICAL_REPORT_REQUEST = (
        "TECHNICAL_REPORT_REQUEST",
        "Oficio de solicitud de dictamen técnico",
    )
    SERVICE_ORDER = (
        "SERVICE_ORDER",
        "Orden de servicio",
    )
    REPAIR_EVIDENCE = (
        "REPAIR_EVIDENCE",
        "Evidencia de reparación",
    )

    DISPOSAL_REQUEST = (
        "DISPOSAL_REQUEST",
        "Oficio de solicitud de baja",
    )
    DISPOSAL_MINUTES = (
        "DISPOSAL_MINUTES",
        "Acta de baja generada",
    )
    SIGNED_DISPOSAL_MINUTES = (
        "SIGNED_DISPOSAL_MINUTES",
        "Acuse firmado del acta de baja",
    )
    COUNCIL_MINUTES = (
        "COUNCIL_MINUTES",
        "Acta de Cabildo",
    )
    POLICE_REPORT = (
        "POLICE_REPORT",
        "Denuncia ante el Ministerio Público",
    )
    DISINCORPORATION_AUTHORIZATION = (
        "DISINCORPORATION_AUTHORIZATION",
        "Autorización de desincorporación",
    )
    ACCOUNTING_DISPOSAL_REQUEST = (
        "ACCOUNTING_DISPOSAL_REQUEST",
        "Oficio de solicitud de baja contable",
    )
    ACCOUNTING_DISPOSAL_CONFIRMATION = (
        "ACCOUNTING_DISPOSAL_CONFIRMATION",
        "Constancia de baja contable",
    )

    PHYSICAL_AUDIT_EVIDENCE = (
        "PHYSICAL_AUDIT_EVIDENCE",
        "Evidencia de auditoría física",
    )
    PHYSICAL_AUDIT_REPORT = (
        "PHYSICAL_AUDIT_REPORT",
        "Reporte de auditoría física generado",
    )
    SIGNED_PHYSICAL_AUDIT_REPORT = (
        "SIGNED_PHYSICAL_AUDIT_REPORT",
        "Acuse firmado de auditoría física",
    )
    RECONCILIATION_REPORT = (
        "RECONCILIATION_REPORT",
        "Reporte de conciliación",
    )

    PHOTO_FRONT = "PHOTO_FRONT", "Foto frontal"
    PHOTO_SERIAL = "PHOTO_SERIAL", "Foto serie / placa"
    PHOTO_CONDITION = (
        "PHOTO_CONDITION",
        "Foto de condición física",
    )

    DEED = "DEED", "Escritura / título"
    CADASTRAL_CERTIFICATE = (
        "CADASTRAL_CERTIFICATE",
        "Cédula / clave catastral",
    )

    OTHER = "OTHER", "Otro documento"


class AccountingAccountType(models.TextChoices):
    ASSET = "ASSET", "Cuenta de activo"
    ACCUMULATED_DEPRECIATION = (
        "ACCUMULATED_DEPRECIATION",
        "Depreciación acumulada",
    )
    EXPENSE = "EXPENSE", "Cuenta de gasto"
    REVENUE = "REVENUE", "Cuenta de ingreso"
    CONTROL = "CONTROL", "Cuenta de orden o control"
    OTHER = "OTHER", "Otra"


# =============================================================================
# CATEGORÍAS PATRIMONIALES
# =============================================================================


class InventoryAssetType(InventoryBaseModel):
    """Catálogo configurable de tipos usados en el folio patrimonial."""

    code = models.CharField("Código para folio", max_length=10, unique=True)
    name = models.CharField("Nombre", max_length=160)
    nature = models.CharField(
        "Naturaleza",
        max_length=20,
        choices=AssetNature.choices,
    )
    is_capitalizable_default = models.BooleanField(
        "Capitalizable por defecto",
        default=False,
    )
    requires_uma_validation = models.BooleanField(
        "Requiere validación UMA",
        default=False,
    )
    allows_user_proposal = models.BooleanField(
        "Disponible como propuesta del capturista",
        default=True,
    )
    requires_override_approval = models.BooleanField(
        "Exige autorización cuando contradice el cálculo",
        default=True,
    )
    description = models.TextField("Descripción", blank=True)

    class Meta:
        db_table = "inventory_asset_types"
        verbose_name = "Tipo patrimonial configurable"
        verbose_name_plural = "Tipos patrimoniales configurables"
        ordering = ["nature", "code"]
        indexes = [
            models.Index(fields=["nature", "is_active"]),
            models.Index(fields=["allows_user_proposal", "is_active"]),
        ]

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        self.name = self.name.strip().upper()
        self.description = self.description.strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} · {self.name}"


class AssetCategory(InventoryBaseModel):
    """
    Categoría funcional del activo.

    No representa por sí misma el Clasificador por Objeto del Gasto ni la
    cuenta contable. Es una agrupación patrimonial y operativa de Inventory.

    Ejemplos:
    - Equipo de cómputo y tecnologías de información
    - Mobiliario y equipo de administración
    - Vehículos y equipo de transporte
    - Bienes inmuebles
    - Licencias de software
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
        db_index=True,
    )
    description = models.TextField(
        "Descripción",
        blank=True,
    )
    requires_serial_number = models.BooleanField(
        "Requiere número de serie",
        default=False,
    )
    requires_photographic_evidence = models.BooleanField(
        "Requiere evidencia fotográfica",
        default=True,
    )
    requires_custody_assignment = models.BooleanField(
        "Requiere resguardo",
        default=True,
    )

    class Meta:
        db_table = "inventory_asset_categories"
        verbose_name = "Categoría patrimonial"
        verbose_name_plural = "Categorías patrimoniales"
        ordering = ["nature", "name"]
        indexes = [
            models.Index(fields=["nature", "is_active"]),
            models.Index(fields=["is_active", "is_deleted"]),
        ]

    def clean(self):
        errors = {}

        if not self.code.strip():
            errors["code"] = "El código es obligatorio."

        if not self.name.strip():
            errors["name"] = "El nombre es obligatorio."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        self.name = self.name.strip().upper()

        if self.description:
            self.description = self.description.strip()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} · {self.name}"


# =============================================================================
# CUENTAS CONTABLES
# =============================================================================


class AccountingAccount(InventoryBaseModel):
    """
    Cuenta del plan contable gubernamental o empresarial.

    Ejemplos:
    - 1.2.4.1.1 Muebles de oficina y estantería
    - 1.2.4.1.3 Equipo de cómputo y tecnologías de información
    - 1.2.6.3 Depreciación acumulada de bienes muebles
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
    account_type = models.CharField(
        "Tipo de cuenta",
        max_length=40,
        choices=AccountingAccountType.choices,
        default=AccountingAccountType.ASSET,
        db_index=True,
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
        help_text="Ejemplo: 33.300 para 33.3%.",
    )

    external_system_code = models.CharField(
        "Código en sistema contable externo",
        max_length=80,
        blank=True,
        help_text="Código utilizado por SIGMAVER u otro sistema contable.",
    )

    class Meta:
        db_table = "inventory_accounting_accounts"
        verbose_name = "Cuenta contable"
        verbose_name_plural = "Cuentas contables"
        ordering = ["code"]
        indexes = [
            models.Index(fields=["account_type", "is_active"]),
            models.Index(fields=["category", "is_active"]),
            models.Index(fields=["is_depreciable"]),
            models.Index(fields=["external_system_code"]),
            models.Index(fields=["is_active", "is_deleted"]),
        ]

    def clean(self):
        errors = {}

        if not self.code.strip():
            errors["code"] = "El código de cuenta es obligatorio."

        if not self.name.strip():
            errors["name"] = "El nombre de la cuenta es obligatorio."

        if (
            self.default_useful_life_months is not None
            and self.default_useful_life_months <= 0
        ):
            errors["default_useful_life_months"] = (
                "La vida útil debe ser mayor a cero."
            )

        if self.default_annual_depreciation_rate is not None:
            if self.default_annual_depreciation_rate < 0:
                errors["default_annual_depreciation_rate"] = (
                    "La tasa no puede ser negativa."
                )

            if self.default_annual_depreciation_rate > 100:
                errors["default_annual_depreciation_rate"] = (
                    "La tasa no puede ser mayor a 100%."
                )

        if not self.is_depreciable:
            if self.default_useful_life_months is not None:
                errors["default_useful_life_months"] = (
                    "Una cuenta no depreciable no debe tener vida útil."
                )

            if self.default_annual_depreciation_rate is not None:
                errors["default_annual_depreciation_rate"] = (
                    "Una cuenta no depreciable no debe tener tasa."
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.code = self.code.strip()
        self.name = self.name.strip().upper()

        if self.external_system_code:
            self.external_system_code = (
                self.external_system_code.strip().upper()
            )

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} · {self.name}"


# =============================================================================
# CLASIFICADOR POR OBJETO DEL GASTO
# =============================================================================


class ExpenditureObject(InventoryBaseModel):
    """
    Clasificador por Objeto del Gasto vinculado con Inventory.

    Separa explícitamente el código presupuestario, la categoría patrimonial y
    la cuenta contable. No debe confundirse el código 5151 con la cuenta
    contable 1.2.4.1.3.

    Ejemplo:
        5151
        → Equipo de cómputo y tecnologías de información
        → Cuenta 1.2.4.1.3
        → BM o BP según la regla de capitalización
    """

    code = models.CharField(
        "Código del objeto del gasto",
        max_length=10,
        unique=True,
    )
    name = models.CharField(
        "Nombre del objeto del gasto",
        max_length=255,
    )
    description = models.TextField(
        "Descripción",
        blank=True,
    )

    category = models.ForeignKey(
        AssetCategory,
        on_delete=models.PROTECT,
        related_name="expenditure_objects",
        verbose_name="Categoría patrimonial",
    )
    accounting_account = models.ForeignKey(
        AccountingAccount,
        on_delete=models.PROTECT,
        related_name="expenditure_objects",
        verbose_name="Cuenta contable relacionada",
        null=True,
        blank=True,
    )

    default_asset_type_code = models.CharField(
        "Tipo de bien predeterminado",
        max_length=2,
        choices=InventoryAssetTypeCode.choices,
        default=InventoryAssetTypeCode.BM,
    )
    capitalization_rule = models.CharField(
        "Regla de capitalización",
        max_length=30,
        choices=CapitalizationRule.choices,
        default=CapitalizationRule.UMA_THRESHOLD,
    )
    uma_multiplier = models.DecimalField(
        "Multiplicador UMA",
        max_digits=8,
        decimal_places=2,
        default=Decimal("70.00"),
        null=True,
        blank=True,
        help_text=(
            "Valor utilizado únicamente cuando la regla es UMA_THRESHOLD."
        ),
    )

    requires_inventory_control = models.BooleanField(
        "Requiere control de inventario",
        default=True,
    )
    requires_accounting_reconciliation = models.BooleanField(
        "Requiere conciliación contable",
        default=True,
    )
    external_system_code = models.CharField(
        "Código en sistema externo",
        max_length=80,
        blank=True,
        help_text="Código equivalente utilizado en SIGMAVER u otro sistema.",
    )

    class Meta:
        db_table = "inventory_expenditure_objects"
        verbose_name = "Objeto del gasto"
        verbose_name_plural = "Objetos del gasto"
        ordering = ["code"]
        indexes = [
            models.Index(fields=["category", "is_active"]),
            models.Index(fields=["accounting_account", "is_active"]),
            models.Index(fields=["capitalization_rule"]),
            models.Index(fields=["default_asset_type_code"]),
            models.Index(fields=["external_system_code"]),
            models.Index(fields=["is_active", "is_deleted"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(uma_multiplier__isnull=True)
                    | Q(uma_multiplier__gt=0)
                ),
                name="ck_inv_cog_uma_multiplier_gt_zero",
            ),
        ]

    def clean(self):
        errors = {}

        if not self.code.strip():
            errors["code"] = (
                "El código del objeto del gasto es obligatorio."
            )

        if not self.name.strip():
            errors["name"] = (
                "El nombre del objeto del gasto es obligatorio."
            )

        if self.capitalization_rule == CapitalizationRule.UMA_THRESHOLD:
            if self.uma_multiplier is None:
                errors["uma_multiplier"] = (
                    "La regla basada en UMA requiere un multiplicador."
                )
            elif self.uma_multiplier <= 0:
                errors["uma_multiplier"] = (
                    "El multiplicador debe ser mayor a cero."
                )
        elif self.uma_multiplier is not None:
            errors["uma_multiplier"] = (
                "El multiplicador sólo debe capturarse cuando la regla "
                "está basada en UMA."
            )

        if self.accounting_account_id and self.category_id:
            account_category_id = self.accounting_account.category_id

            if (
                account_category_id
                and account_category_id != self.category_id
            ):
                errors["accounting_account"] = (
                    "La cuenta contable está vinculada con una categoría "
                    "patrimonial diferente."
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        self.name = self.name.strip().upper()

        if self.description:
            self.description = self.description.strip()

        if self.external_system_code:
            self.external_system_code = (
                self.external_system_code.strip().upper()
            )

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} · {self.name}"


# =============================================================================
# VALORES HISTÓRICOS DE UMA
# =============================================================================


class UmaValue(InventoryBaseModel):
    """
    Valor histórico de la Unidad de Medida y Actualización.

    El activo guarda tanto la referencia UUID como un snapshot del valor,
    multiplicador y umbral efectivamente utilizados. De esa forma una
    actualización posterior no modifica las decisiones históricas.
    """

    year = models.PositiveSmallIntegerField(
        "Año",
        unique=True,
    )
    daily_value = models.DecimalField(
        "Valor diario",
        max_digits=16,
        decimal_places=4,
    )
    effective_from = models.DateField(
        "Vigente desde",
    )
    effective_until = models.DateField(
        "Vigente hasta",
    )
    publication_date = models.DateField(
        "Fecha de publicación",
        null=True,
        blank=True,
    )
    source_reference = models.CharField(
        "Referencia oficial",
        max_length=255,
        blank=True,
    )
    source_url = models.URLField(
        "URL de la fuente",
        max_length=500,
        blank=True,
    )

    class Meta:
        db_table = "inventory_uma_values"
        verbose_name = "Valor histórico de UMA"
        verbose_name_plural = "Valores históricos de UMA"
        ordering = ["-year"]
        indexes = [
            models.Index(fields=["effective_from", "effective_until"]),
            models.Index(fields=["is_active", "is_deleted"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(year__gte=2000),
                name="ck_inv_uma_year_gte_2000",
            ),
            models.CheckConstraint(
                condition=Q(daily_value__gt=0),
                name="ck_inv_uma_daily_value_gt_zero",
            ),
        ]

    def clean(self):
        errors = {}

        if self.year < 2000:
            errors["year"] = (
                "El año debe utilizar cuatro dígitos."
            )

        if self.daily_value <= 0:
            errors["daily_value"] = (
                "El valor diario de la UMA debe ser mayor a cero."
            )

        if self.effective_until < self.effective_from:
            errors["effective_until"] = (
                "La fecha final no puede ser anterior a la fecha inicial."
            )

        if self.effective_from.year != self.year:
            errors["effective_from"] = (
                "La fecha inicial debe pertenecer al año indicado."
            )

        if self.effective_until.year != self.year:
            errors["effective_until"] = (
                "La fecha final debe pertenecer al año indicado."
            )

        overlapping = (
            UmaValue.objects
            .filter(
                effective_from__lte=self.effective_until,
                effective_until__gte=self.effective_from,
                is_deleted=False,
            )
            .exclude(pk=self.pk)
            .exists()
        )

        if overlapping:
            errors["effective_from"] = (
                "El periodo de vigencia se traslapa con otro valor UMA."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.source_reference:
            self.source_reference = self.source_reference.strip()

        if self.source_url:
            self.source_url = self.source_url.strip()

        super().save(*args, **kwargs)

    def calculate_threshold(self, multiplier=Decimal("70.00")):
        return (
            self.daily_value * Decimal(str(multiplier))
        ).quantize(Decimal("0.01"))

    def __str__(self):
        return f"UMA {self.year} · ${self.daily_value}"


# =============================================================================
# FABRICANTES Y MODELOS
# =============================================================================


class Manufacturer(InventoryBaseModel):
    name = models.CharField(
        "Fabricante",
        max_length=120,
        unique=True,
    )

    class Meta:
        db_table = "inventory_manufacturers"
        verbose_name = "Fabricante"
        verbose_name_plural = "Fabricantes"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["is_active", "is_deleted"]),
        ]

    def clean(self):
        if not self.name.strip():
            raise ValidationError(
                {"name": "El nombre del fabricante es obligatorio."}
            )

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
        verbose_name = "Modelo de activo"
        verbose_name_plural = "Modelos de activos"
        ordering = ["manufacturer__name", "name"]
        indexes = [
            models.Index(fields=["manufacturer", "name"]),
            models.Index(fields=["is_active", "is_deleted"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["manufacturer", "name"],
                name="uq_inv_asset_model_manufacturer_name",
            ),
        ]

    def clean(self):
        if not self.name.strip():
            raise ValidationError(
                {"name": "El nombre del modelo es obligatorio."}
            )

    def save(self, *args, **kwargs):
        self.name = self.name.strip().upper()

        if self.description:
            self.description = self.description.strip()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.manufacturer.name} · {self.name}"


# =============================================================================
# PROVEEDORES Y CONTRATOS
# =============================================================================


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
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"
        ordering = ["razon_social"]
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["is_active", "is_deleted"]),
        ]

    def clean(self):
        errors = {}

        if not self.razon_social.strip():
            errors["razon_social"] = (
                "La razón social es obligatoria."
            )

        if self.rfc:
            normalized_rfc = self.rfc.strip().upper()

            if len(normalized_rfc) not in {12, 13}:
                errors["rfc"] = (
                    "El RFC debe contener 12 o 13 caracteres."
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.razon_social = self.razon_social.strip().upper()

        if self.rfc:
            self.rfc = self.rfc.strip().upper()
        else:
            self.rfc = None

        if self.contacto_nombre:
            self.contacto_nombre = (
                self.contacto_nombre.strip().upper()
            )

        if self.telefono:
            self.telefono = self.telefono.strip()

        if self.email:
            self.email = self.email.strip().lower()

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
    external_reference = models.CharField(
        "Referencia externa",
        max_length=120,
        blank=True,
    )

    class Meta:
        db_table = "inventory_contracts"
        verbose_name = "Contrato"
        verbose_name_plural = "Contratos"
        ordering = ["-fecha_inicio", "numero_contrato"]
        indexes = [
            models.Index(fields=["supplier", "fecha_inicio"]),
            models.Index(fields=["fecha_inicio", "fecha_fin"]),
            models.Index(fields=["external_reference"]),
            models.Index(fields=["is_active", "is_deleted"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(monto_total__isnull=True)
                    | Q(monto_total__gte=0)
                ),
                name="ck_inv_contract_amount_gte_zero",
            ),
        ]

    def clean(self):
        errors = {}

        if not self.numero_contrato.strip():
            errors["numero_contrato"] = (
                "El número de contrato es obligatorio."
            )

        if not self.nombre.strip():
            errors["nombre"] = (
                "El objeto del contrato es obligatorio."
            )

        if (
            self.fecha_inicio
            and self.fecha_fin
            and self.fecha_fin < self.fecha_inicio
        ):
            errors["fecha_fin"] = (
                "La fecha final no puede ser anterior a la inicial."
            )

        if self.monto_total is not None and self.monto_total < 0:
            errors["monto_total"] = (
                "El monto del contrato no puede ser negativo."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.numero_contrato = (
            self.numero_contrato.strip().upper()
        )
        self.nombre = self.nombre.strip().upper()

        if self.external_reference:
            self.external_reference = (
                self.external_reference.strip().upper()
            )

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.numero_contrato} · {self.nombre}"
    
