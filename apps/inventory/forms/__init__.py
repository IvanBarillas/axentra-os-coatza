"""API pública de formularios de la aplicación Inventory."""

from apps.inventory.forms.asset_forms import (
    AssetConditionUpdateForm,
    AssetCorrectionForm,
    AssetLocationUpdateForm,
)
from apps.inventory.forms.custody_forms import (
    CustodyAcceptForm,
    CustodyAuthorizeForm,
    CustodyCancelForm,
    CustodyCreateForm,
    CustodyRejectForm,
    CustodyReturnForm,
)
from apps.inventory.forms.disposal_forms import (
    DisposalCancelForm,
    DisposalExecuteForm,
    DisposalFinalApprovalForm,
    DisposalRequestCreateForm,
    DisposalStageResolutionForm,
    DisposalSubmitForm,
)
from apps.inventory.forms.document_forms import (
    DocumentValidationResolveForm,
    DocumentValidationSubmitForm,
    InventoryDocumentReplaceForm,
    InventoryDocumentUploadForm,
    InventoryPhotoUploadForm,
    InventoryPhotoValidationForm,
)
from apps.inventory.forms.financial_forms import (
    AccountingExportCreateForm,
    DepreciationCalculateForm,
    DepreciationCompleteForm,
    DepreciationPostForm,
    DepreciationRunCreateForm,
    ReconciliationCloseForm,
    ReconciliationCreateForm,
    ReconciliationItemReviewForm,
    ReconciliationProcessForm,
)
from apps.inventory.forms.intake_forms import (
    AssetIntakeCreateForm,
    AssetIntakeUpdateForm,
    CancelAssetIntakeForm,
    DepartmentIntakeDecisionForm,
    PatrimonyApprovalForm,
    PatrimonyObservationForm,
)
from apps.inventory.forms.loan_forms import (
    AssetLoanAuthorizationForm,
    AssetLoanCancelForm,
    AssetLoanCreateForm,
    AssetLoanDeliveryForm,
    AssetLoanReturnForm,
    AssetLoanReturnRequestForm,
    DepartmentLoanDecisionForm,
)
from apps.inventory.forms.movement_forms import (
    AssetLocationChangeForm,
    AssetReassignmentForm,
    AssetTransferForm,
    MaintenanceMovementForm,
)
from apps.inventory.forms.physical_audit_forms import (
    PhysicalAuditCancelForm,
    PhysicalAuditCloseForm,
    PhysicalAuditCreateForm,
    PhysicalAuditFreezeForm,
    PhysicalAuditNotFoundForm,
    PhysicalAuditReconcileForm,
    PhysicalAuditScanForm,
    PhysicalAuditStartForm,
    PhysicalAuditUnlistedItemForm,
)


__all__ = [
    # Activos
    "AssetConditionUpdateForm",
    "AssetCorrectionForm",
    "AssetLocationUpdateForm",

    # Resguardos
    "CustodyAcceptForm",
    "CustodyAuthorizeForm",
    "CustodyCancelForm",
    "CustodyCreateForm",
    "CustodyRejectForm",
    "CustodyReturnForm",

    # Bajas
    "DisposalCancelForm",
    "DisposalExecuteForm",
    "DisposalFinalApprovalForm",
    "DisposalRequestCreateForm",
    "DisposalStageResolutionForm",
    "DisposalSubmitForm",

    # Documentos y fotografías
    "DocumentValidationResolveForm",
    "DocumentValidationSubmitForm",
    "InventoryDocumentReplaceForm",
    "InventoryDocumentUploadForm",
    "InventoryPhotoUploadForm",
    "InventoryPhotoValidationForm",

    # Finanzas y conciliación
    "AccountingExportCreateForm",
    "DepreciationCalculateForm",
    "DepreciationCompleteForm",
    "DepreciationPostForm",
    "DepreciationRunCreateForm",
    "ReconciliationCloseForm",
    "ReconciliationCreateForm",
    "ReconciliationItemReviewForm",
    "ReconciliationProcessForm",

    # Solicitudes de alta
    "AssetIntakeCreateForm",
    "AssetIntakeUpdateForm",
    "CancelAssetIntakeForm",
    "DepartmentIntakeDecisionForm",
    "PatrimonyApprovalForm",
    "PatrimonyObservationForm",

    # Préstamos
    "AssetLoanAuthorizationForm",
    "AssetLoanCancelForm",
    "AssetLoanCreateForm",
    "AssetLoanDeliveryForm",
    "AssetLoanReturnForm",
    "AssetLoanReturnRequestForm",
    "DepartmentLoanDecisionForm",

    # Movimientos
    "AssetLocationChangeForm",
    "AssetReassignmentForm",
    "AssetTransferForm",
    "MaintenanceMovementForm",

    # Auditoría física
    "PhysicalAuditCancelForm",
    "PhysicalAuditCloseForm",
    "PhysicalAuditCreateForm",
    "PhysicalAuditFreezeForm",
    "PhysicalAuditNotFoundForm",
    "PhysicalAuditReconcileForm",
    "PhysicalAuditScanForm",
    "PhysicalAuditStartForm",
    "PhysicalAuditUnlistedItemForm",
]

