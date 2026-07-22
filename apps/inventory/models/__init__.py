# apps/inventory/models/__init__.py

"""
API pública de modelos de la aplicación Inventory.

Los demás componentes deben importar los modelos desde:

    from apps.inventory.models import Asset, CustodyAssignment

en lugar de importar directamente desde cada archivo interno.
"""

# =============================================================================
# CATÁLOGOS Y MODELOS BASE
# =============================================================================

from apps.inventory.models.catalog_models import (
    AccountingAccount,
    AccountingAccountType,
    AcquisitionType,
    AssetCategory,
    AssetControlType,
    AssetModel,
    AssetNature,
    CapitalizationRule,
    Contract,
    DisposalReason,
    DocumentType,
    ExpenditureObject,
    InventoryAssetTypeCode,
    InventoryBaseModel,
    Manufacturer,
    MovementType,
    PhysicalCondition,
    Supplier,
    UmaValue,
)

# =============================================================================
# ACTIVOS, SOLICITUDES DE ALTA Y FOLIOS
# =============================================================================

from apps.inventory.models.asset_models import (
    Asset,
    AssetIntakeDecision,
    AssetIntakeDecisionType,
    AssetIntakeRequest,
    AssetIntakeStatus,
    AssetOperationalStatus,
    AssetPatrimonialStatus,
    ImmovableAssetDetail,
    InventoryFolioPolicy,
    InventoryFolioSequence,
)

# =============================================================================
# RESGUARDOS
# =============================================================================

from apps.inventory.models.custody_models import (
    CustodyAcceptanceMethod,
    CustodyAssignment,
    CustodyAssignmentEvent,
    CustodyEventType,
    CustodyStatus,
)

# =============================================================================
# MOVIMIENTOS, PRÉSTAMOS Y BAJAS
# =============================================================================

from apps.inventory.models.movement_models import (
    AssetMovementRequest,
    AssetMovementRequestStatus,
    AssetLoan,
    AssetLoanStatus,
    DisposalApproval,
    DisposalApprovalDecision,
    DisposalApprovalStage,
    DisposalRequest,
    DisposalStatus,
    InventoryMovement,
    MovementReferenceType,
)

# =============================================================================
# DOCUMENTOS Y EVIDENCIAS FOTOGRÁFICAS
# =============================================================================

from apps.inventory.models.document_models import (
    AssetDocument,
    AssetPhoto,
    DocumentAccessLevel,
    DocumentRequirementLevel,
    DocumentValidationEvent,
    DocumentValidationEventType,
    DocumentValidationStatus,
    InventoryDocumentOwnerType,
    InventoryPhotoType,
    DisposalStageDocumentRequirement,
)

# =============================================================================
# DEPRECIACIÓN, EXPORTACIÓN Y CONCILIACIÓN CONTABLE
# =============================================================================

from apps.inventory.models.financial_models import (
    AccountingExportBatch,
    AccountingReconciliation,
    AccountingReconciliationItem,
    DepreciationFrequency,
    DepreciationMethod,
    DepreciationPolicy,
    DepreciationRecord,
    DepreciationRun,
)

# =============================================================================
# AUDITORÍA FÍSICA Y BITÁCORA INTERNA
# =============================================================================

from apps.inventory.models.audit_models import (
    InventoryAuditAction,
    InventoryAuditLevel,
    InventoryAuditLog,
    PhysicalAuditItem,
    PhysicalAuditResult,
    PhysicalAuditScope,
    PhysicalAuditSession,
    PhysicalAuditStatus,
)


__all__ = [
    # Catálogos y base
    "AccountingAccount",
    "AccountingAccountType",
    "AcquisitionType",
    "AssetCategory",
    "AssetControlType",
    "AssetModel",
    "AssetNature",
    "CapitalizationRule",
    "Contract",
    "DisposalReason",
    "DocumentType",
    "ExpenditureObject",
    "InventoryAssetTypeCode",
    "InventoryBaseModel",
    "Manufacturer",
    "MovementType",
    "PhysicalCondition",
    "Supplier",
    "UmaValue",

    # Activos, solicitudes y folios
    "Asset",
    "AssetIntakeDecision",
    "AssetIntakeDecisionType",
    "AssetIntakeRequest",
    "AssetIntakeStatus",
    "AssetOperationalStatus",
    "AssetPatrimonialStatus",
    "ImmovableAssetDetail",
    "InventoryFolioPolicy",
    "InventoryFolioSequence",

    # Resguardos
    "CustodyAcceptanceMethod",
    "CustodyAssignment",
    "CustodyAssignmentEvent",
    "CustodyEventType",
    "CustodyStatus",

    # Movimientos, préstamos y bajas
    "AssetLoan",
    "AssetMovementRequest",
    "AssetMovementRequestStatus",
    "AssetLoanStatus",
    "DisposalApproval",
    "DisposalApprovalDecision",
    "DisposalApprovalStage",
    "DisposalRequest",
    "DisposalStatus",
    "InventoryMovement",
    "MovementReferenceType",

    # Documentos y fotografías
    "AssetDocument",
    "AssetPhoto",
    "DocumentAccessLevel",
    "DocumentRequirementLevel",
    "DocumentValidationEvent",
    "DocumentValidationEventType",
    "DocumentValidationStatus",
    "InventoryDocumentOwnerType",
    "InventoryPhotoType",
    "DisposalStageDocumentRequirement",

    # Finanzas y contabilidad
    "AccountingExportBatch",
    "AccountingReconciliation",
    "AccountingReconciliationItem",
    "DepreciationFrequency",
    "DepreciationMethod",
    "DepreciationPolicy",
    "DepreciationRecord",
    "DepreciationRun",

    # Auditoría
    "InventoryAuditAction",
    "InventoryAuditLevel",
    "InventoryAuditLog",
    "PhysicalAuditItem",
    "PhysicalAuditResult",
    "PhysicalAuditScope",
    "PhysicalAuditSession",
    "PhysicalAuditStatus",
]
