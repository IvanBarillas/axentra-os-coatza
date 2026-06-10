# apps/security/selectors/__init__.py

# 🏛️ PILAR 1: TOPOLOGÍA GUBERNAMENTAL (ORGANIGRAMA)
from .organigrama_selectors import (
    OrganigramaDashboardSelector, 
    SedeSelectors, 
    DependenciaSelectors, 
    AreaOperativaSelectors
)

# 👥 PILAR 2: EXPEDIENTES Y PERSONAL (ACCOUNTS)
from .accounts_selectors import (
    AccountsDashboardSelectors, 
    FuncionarioSelectors
)

# 🛡️ PILAR 3: CIBERSEGURIDAD CENTRAL Y MATRIZ (SECURITY)
# 🟢 CORRECCIÓN: Eliminada la clase inexistente 'SecuritySelectors' y unificado el pool
from .security_selectors import (
    SecurityDashboardSelectors, 
    PermissionSelectors,  # ◄── Tu clase premium vive aquí adentro ahora
    TenantConfigSelectors
)

# Exposición oficial libre de fantasmas para el Core de Axentra OS
__all__ = [
    # Dominios de Organigrama
    'OrganigramaDashboardSelector', 
    'SedeSelectors', 
    'DependenciaSelectors', 
    'AreaOperativaSelectors',
    
    # Dominios de Accounts
    'AccountsDashboardSelectors', 
    'FuncionarioSelectors',
    
    # Dominios de Security
    'SecurityDashboardSelectors', 
    'TenantConfigSelectors',
    'PermissionSelectors'
]