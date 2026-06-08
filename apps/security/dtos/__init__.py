# apps/security/dtos/__init__.py

from .security_dtos import RoleReadOnlyDTO, RoleInputDTO, TenantConfigReadOnlyDTO
from .accounts_dtos import FuncionarioReadOnlyDTO, CrearFuncionarioInputDTO, EditarFuncionarioInputDTO
from .organigrama_dtos import (
    SedeReadOnlyDTO, SedeInputDTO,
    DependenciaReadOnlyDTO, DependenciaInputDTO,
    AreaOperativaReadOnlyDTO, AreaOperativaInputDTO,
    CapabilityReadOnlyDTO, CapabilityInputDTO
)

__all__ = [
    'RoleReadOnlyDTO', 'RoleInputDTO', 'TenantConfigReadOnlyDTO',
    'FuncionarioReadOnlyDTO', 'CrearFuncionarioInputDTO', 'EditarFuncionarioInputDTO',
    'SedeReadOnlyDTO', 'SedeInputDTO',
    'DependenciaReadOnlyDTO', 'DependenciaInputDTO',
    'AreaOperativaReadOnlyDTO', 'AreaOperativaInputDTO',
    'CapabilityReadOnlyDTO', 'CapabilityInputDTO'
]