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
from .security_selectors import (
    SecurityDashboardSelectors, 
    TenantConfigSelectors
)

from .permission_selectors import (
    PermissionSelectors,
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
    
    'PermissionSelectors',
]