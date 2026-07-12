# apps/inventory/models/__init__.py

from apps.inventory.models.catalog_models import (
    AccountingAccount,
    AcquisitionType,
    AssetCategory,
    AssetControlType,
    AssetLifecycleStatus,
    AssetNature,
    Contract,
    DisposalReason,
    DocumentType,
    InventoryBaseModel,
    Manufacturer,
    MovementType,
    PhysicalCondition,
    RelationType,
    Supplier,
    AssetModel,
)

from apps.inventory.models.asset_models import (
    Asset,
    ImmovableAssetDetail,
)

from apps.inventory.models.technical_models import (
    AssetRelation,
    TechnicalAssetProfile,
    TechnicalAssetType,
)

from apps.inventory.models.custody_models import (
    CustodyAssignment,
    CustodyStatus,
)

from apps.inventory.models.movement_models import (
    DisposalRequest,
    DisposalStatus,
    InventoryMovement,
)

from apps.inventory.models.financial_models import (
    AccountingExportBatch,
    DepreciationFrequency,
    DepreciationMethod,
    DepreciationPolicy,
    DepreciationRecord,
)

from apps.inventory.models.document_models import (
    AssetDocument,
    AssetPhoto,
)

from apps.inventory.models.audit_models import (
    InventoryAuditLog,
    PhysicalAuditItem,
    PhysicalAuditResult,
    PhysicalAuditSession,
    PhysicalAuditStatus,
)

from apps.inventory.models.consumable_models import (
    Consumable,
    ConsumableMovement,
    ConsumableMovementType,
)