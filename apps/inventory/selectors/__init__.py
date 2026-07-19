"""API pública de consultas de Inventory.

Los selectores son exclusivamente de lectura. Las transiciones y escrituras
pertenecen a ``apps.inventory.services``.
"""

from .asset_selectors import AssetSelectors, IntakeSelectors
from .audit_selectors import (
    PhysicalAuditSelectors,
    PhysicalAuditVisibilityScope,
)
from .catalog_selectors import (
    CatalogSelectors,
    CoreDirectorySelectors,
)
from .custody_selectors import (
    CustodyScope,
    CustodySelectors,
)
from .document_selectors import (
    DocumentScope,
    DocumentSelectors,
)
from .financial_selectors import (
    FinancialScope,
    FinancialSelectors,
)
from .movement_selectors import (
    DisposalSelectors,
    LoanSelectors,
    MovementSelectors,
    RegistryScope,
)


__all__ = [
    # Activos y solicitudes
    "AssetSelectors",
    "IntakeSelectors",

    # Catálogos y directorio
    "CatalogSelectors",
    "CoreDirectorySelectors",

    # Resguardos
    "CustodyScope",
    "CustodySelectors",

    # Movimientos, préstamos y bajas
    "DisposalSelectors",
    "LoanSelectors",
    "MovementSelectors",
    "RegistryScope",

    # Documentos y fotografías
    "DocumentScope",
    "DocumentSelectors",

    # Auditoría física
    "PhysicalAuditSelectors",
    "PhysicalAuditVisibilityScope",

    # Finanzas
    "FinancialScope",
    "FinancialSelectors",
]

