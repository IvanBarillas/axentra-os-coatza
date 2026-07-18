# apps/inventory/services/exceptions.py

"""Excepciones públicas de la capa de servicios de Inventory."""

from typing import Any, Mapping


class InventoryServiceError(Exception):
    """Error base controlado de la lógica de Inventory."""

    default_code = "inventory_service_error"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        details: Mapping[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code or self.default_code
        self.details = dict(details or {})

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }


class InventoryValidationError(InventoryServiceError):
    default_code = "inventory_validation_error"


class InventoryNotFoundError(InventoryServiceError):
    default_code = "inventory_not_found"


class InventoryConflictError(InventoryServiceError):
    default_code = "inventory_conflict"


class InventoryStateError(InventoryServiceError):
    default_code = "inventory_invalid_state"


class InventoryAuthorizationError(InventoryServiceError):
    default_code = "inventory_authorization_denied"


class InventoryBypassReasonRequired(InventoryAuthorizationError):
    default_code = "inventory_bypass_reason_required"


class InventoryConfigurationError(InventoryServiceError):
    default_code = "inventory_configuration_error"


class FolioGenerationError(InventoryServiceError):
    default_code = "inventory_folio_generation_error"


class FolioPolicyNotFound(FolioGenerationError):
    default_code = "inventory_folio_policy_not_found"


class FolioPolicyConflict(FolioGenerationError):
    default_code = "inventory_folio_policy_conflict"


class FolioSequenceExhausted(FolioGenerationError):
    default_code = "inventory_folio_sequence_exhausted"


class InventoryDocumentError(InventoryServiceError):
    default_code = "inventory_document_error"


class InventoryWorkflowError(InventoryServiceError):
    default_code = "inventory_workflow_error"


class InventoryConcurrencyError(InventoryServiceError):
    default_code = "inventory_concurrency_error"


__all__ = [
    "FolioGenerationError",
    "FolioPolicyConflict",
    "FolioPolicyNotFound",
    "FolioSequenceExhausted",
    "InventoryAuthorizationError",
    "InventoryBypassReasonRequired",
    "InventoryConcurrencyError",
    "InventoryConfigurationError",
    "InventoryConflictError",
    "InventoryDocumentError",
    "InventoryNotFoundError",
    "InventoryServiceError",
    "InventoryStateError",
    "InventoryValidationError",
    "InventoryWorkflowError",
]
