from apps.inventory.dtos.asset_dtos import (
    AssetStateResultDTO,
    CorrectAssetDTO,
    UpdateAssetConditionDTO,
    UpdateAssetLocationDTO,
)
from apps.inventory.dtos.audit_dtos import (
    AuditRequestContext,
    CreateAuditEventDTO,
)
from apps.inventory.dtos.common_dtos import (
    ExternalReferenceDTO,
    GeoPointDTO,
    OperationContextDTO,
    ServiceResultDTO,
)
from apps.inventory.dtos.custody_dtos import (
    AcceptCustodyAssignmentDTO,
    AuthorizeCustodyAssignmentDTO,
    CancelCustodyAssignmentDTO,
    CreateCustodyAssignmentDTO,
    CustodyTransitionResultDTO,
    RejectCustodyAssignmentDTO,
    ReturnCustodyAssignmentDTO,
)
from apps.inventory.dtos.disposal_dtos import (
    CancelDisposalDTO,
    CreateDisposalRequestDTO,
    DisposalTransitionResultDTO,
    ExecuteDisposalDTO,
    FinalizeDisposalApprovalDTO,
    ResolveDisposalStageDTO,
    SubmitDisposalRequestDTO,
)
from apps.inventory.dtos.document_dtos import (
    DocumentOperationResultDTO,
    ReplaceInventoryDocumentDTO,
    ResolveDocumentValidationDTO,
    ResolvePhotoValidationDTO,
    SubmitDocumentValidationDTO,
    UploadInventoryDocumentDTO,
    UploadInventoryPhotoDTO,
)
from apps.inventory.dtos.financial_dtos import (
    CalculateDepreciationDTO,
    CloseReconciliationDTO,
    CompleteDepreciationRunDTO,
    CreateAccountingExportDTO,
    CreateDepreciationRunDTO,
    CreateReconciliationDTO,
    DepreciationRunResultDTO,
    PostDepreciationRunDTO,
    ProcessReconciliationDTO,
    ReconciliationResultDTO,
    ReviewReconciliationItemDTO,
)
from apps.inventory.dtos.folio_dtos import (
    FolioScope,
    GenerateInventoryFolioDTO,
    GeneratedInventoryFolio,
)
from apps.inventory.dtos.intake_dtos import (
    AssetRegistrationResultDTO,
    CancelAssetIntakeDTO,
    CapitalizationResultDTO,
    CreateAssetIntakeDTO,
    DepartmentIntakeDecisionDTO,
    IntakeTransitionResultDTO,
    PatrimonyApprovalDTO,
    PatrimonyObservationDTO,
    UpdateAssetIntakeDTO,
)
from apps.inventory.dtos.loan_dtos import (
    AuthorizeAssetLoanDTO,
    CancelAssetLoanDTO,
    CreateAssetLoanDTO,
    DeliverAssetLoanDTO,
    DepartmentLoanDecisionDTO,
    LoanTransitionResultDTO,
    RequestLoanReturnDTO,
    ReturnAssetLoanDTO,
)
from apps.inventory.dtos.movement_dtos import (
    ChangeAssetLocationDTO,
    CreateInventoryMovementDTO,
    MaintenanceMovementDTO,
    MovementResultDTO,
    OrganizationalDestinationDTO,
    ReassignAssetDTO,
    TransferAssetDTO,
)
from apps.inventory.dtos.physical_audit_dtos import (
    CancelPhysicalAuditDTO,
    ClosePhysicalAuditDTO,
    CreatePhysicalAuditSessionDTO,
    FreezePhysicalAuditDTO,
    MarkAuditItemNotFoundDTO,
    PhysicalAuditTransitionResultDTO,
    ReconcilePhysicalAuditItemDTO,
    RegisterUnlistedAuditItemDTO,
    ScanPhysicalAuditItemDTO,
    StartPhysicalAuditDTO,
)


__all__ = [name for name in globals() if name.endswith("DTO")]
