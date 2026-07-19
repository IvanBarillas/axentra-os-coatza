"""API pública de consultas de Inventory.

Los selectores son exclusivamente de lectura. Las transiciones y escrituras
pertenecen a :mod:`apps.inventory.services`.
"""

from .asset_selectors import AssetSelectors, IntakeSelectors, InventoryScope
from .audit_selectors import PhysicalAuditSelectors, PhysicalAuditVisibilityScope
from .catalog_selectors import CatalogSelectors, CoreDirectorySelectors
from .custody_selectors import CustodyScope, CustodySelectors
from .document_selectors import DocumentScope, DocumentSelectors
from .financial_selectors import FinancialScope, FinancialSelectors
from .movement_selectors import (
    DisposalSelectors,
    LoanSelectors,
    MovementSelectors,
    RegistryScope,
)


__all__ = [
    "AssetSelectors",
    "CatalogSelectors",
    "CoreDirectorySelectors",
    "CustodyScope",
    "CustodySelectors",
    "DisposalSelectors",
    "DocumentScope",
    "DocumentSelectors",
    "FinancialScope",
    "FinancialSelectors",
    "IntakeSelectors",
    "InventoryScope",
    "LoanSelectors",
    "MovementSelectors",
    "PhysicalAuditSelectors",
    "PhysicalAuditVisibilityScope",
    "RegistryScope",
]
