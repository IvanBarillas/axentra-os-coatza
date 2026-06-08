# apps/security/models/__init__.py

from .accounts import User, UserProfile
from .organigrama import Sede, Dependencia, AreaOperativa, AppDependencyCapability
from .infrastructure import AppModule, UserAppRole, TenantConfig
from .audit import SecurityAuditLog

# Exponer explícitamente las clases para descubrimientos limpios de Django
__all__ = [
    'User',
    'UserProfile',
    'Sede',
    'Dependencia',
    'AreaOperativa',
    'AppDependencyCapability',
    'AppModule',
    'UserAppRole',
    'TenantConfig',
    'SecurityAuditLog',
]