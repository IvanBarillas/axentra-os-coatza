"""API pública de consultas de Inventory.

Los selectores son exclusivamente de lectura. Las transiciones y escrituras
pertenecen a ``apps.inventory.services``.
"""

from .asset_selectors import AssetSelectors, IntakeSelectors
from .audit_selectors import PhysicalAuditSelectors
from .catalog_selectors import CatalogSelectors, CoreDirectorySelectors
from .custody_selectors import CustodySelectors
from .document_selectors import DocumentSelectors
from .financial_selectors import FinancialSelectors
from .movement_selectors import DisposalSelectors, LoanSelectors, MovementSelectors

__all__ = [
    "AssetSelectors", "CatalogSelectors", "CoreDirectorySelectors",
    "CustodySelectors", "DisposalSelectors", "DocumentSelectors",
    "FinancialSelectors", "IntakeSelectors", "LoanSelectors",
    "MovementSelectors", "PhysicalAuditSelectors",
]
