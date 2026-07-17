# apps/inventory/integrations/contracts.py

"""
Contratos de lectura entre Inventory y el directorio institucional del Core.

Este archivo no debe importar Django ni modelos de ``apps.security``.
Define estructuras inmutables que Inventory puede consumir sin conocer la
implementación interna del Core.

El adaptador ``core_directory.py`` será responsable de convertir modelos del
Core en estas estructuras.
"""

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping
from uuid import UUID


def _immutable_mapping(
    value: Mapping[str, Any] | None,
) -> Mapping[str, Any]:
    """Devuelve una copia superficial de solo lectura."""

    return MappingProxyType(dict(value or {}))


@dataclass(frozen=True, slots=True)
class UserIdentity:
    """Identidad mínima de un usuario del Core."""

    id: UUID
    email: str
    display_name: str
    first_name: str = ""
    last_name: str = ""
    is_active: bool = True
    is_deleted: bool = False
    is_staff: bool = False
    is_superuser: bool = False
    is_manager: bool = False

    @property
    def is_available(self) -> bool:
        return self.is_active and not self.is_deleted

    @property
    def has_global_bypass(self) -> bool:
        return (
            self.is_available
            and (self.is_superuser or self.is_manager)
        )

    @property
    def normalized_email(self) -> str:
        return self.email.strip().lower()


@dataclass(frozen=True, slots=True)
class DepartmentIdentity:
    """Dependencia, dirección o unidad administrativa del Core."""

    id: UUID
    name: str
    code: str = ""
    slug: str = ""
    parent_id: UUID | None = None
    manager_user_id: UUID | None = None
    is_active: bool = True
    is_deleted: bool = False

    @property
    def is_available(self) -> bool:
        return self.is_active and not self.is_deleted

    @property
    def normalized_code(self) -> str:
        value = self.code.strip()
        return value.zfill(3) if value else ""


@dataclass(frozen=True, slots=True)
class SiteIdentity:
    """Sede o edificio físico del Core."""

    id: UUID
    name: str
    address: str = ""
    technical_manager_user_id: UUID | None = None
    is_active: bool = True
    is_deleted: bool = False

    @property
    def is_available(self) -> bool:
        return self.is_active and not self.is_deleted


@dataclass(frozen=True, slots=True)
class AreaContext:
    """
    Contexto organizacional completo de un área operativa.

    Incluye snapshots de dependencia y sede para evitar que los servicios de
    Inventory tengan que navegar relaciones de modelos pertenecientes al Core.
    """

    id: UUID
    name: str
    slug: str
    department: DepartmentIdentity
    site: SiteIdentity
    is_active: bool = True
    is_deleted: bool = False

    @property
    def is_available(self) -> bool:
        return (
            self.is_active
            and not self.is_deleted
            and self.department.is_available
            and self.site.is_available
        )

    @property
    def department_id(self) -> UUID:
        return self.department.id

    @property
    def department_code(self) -> str:
        return self.department.normalized_code

    @property
    def department_name(self) -> str:
        return self.department.name

    @property
    def site_id(self) -> UUID:
        return self.site.id

    @property
    def site_name(self) -> str:
        return self.site.name


@dataclass(frozen=True, slots=True)
class UserOrganizationalContext:
    """Adscripción laboral vigente de un funcionario."""

    user: UserIdentity
    profile_id: UUID | None = None
    position: str = ""
    office_phone: str = ""
    area: AreaContext | None = None

    @property
    def has_profile(self) -> bool:
        return self.profile_id is not None

    @property
    def department(self) -> DepartmentIdentity | None:
        return self.area.department if self.area else None

    @property
    def site(self) -> SiteIdentity | None:
        return self.area.site if self.area else None

    @property
    def department_id(self) -> UUID | None:
        department = self.department
        return department.id if department else None

    @property
    def area_id(self) -> UUID | None:
        return self.area.id if self.area else None

    @property
    def site_id(self) -> UUID | None:
        site = self.site
        return site.id if site else None


@dataclass(frozen=True, slots=True)
class ModuleRoleIdentity:
    """Rol y permisos finos de un usuario dentro de un módulo."""

    app_id: UUID
    app_slug: str
    role: str
    permissions: tuple[str, ...] = field(default_factory=tuple)
    is_active: bool = True
    is_deleted: bool = False

    @property
    def is_available(self) -> bool:
        return self.is_active and not self.is_deleted

    @property
    def is_owner(self) -> bool:
        return self.role.strip().lower() == "owner"

    def has_permission(self, permission: str) -> bool:
        if not self.is_available:
            return False

        if self.is_owner:
            return True

        normalized_permission = permission.strip()
        return normalized_permission in self.permissions


@dataclass(frozen=True, slots=True)
class DepartmentCapabilityIdentity:
    """Capacidades de una dependencia para operar un módulo."""

    app_id: UUID
    app_slug: str
    department_id: UUID
    can_operate: bool = False
    can_supervise: bool = False
    can_authorize: bool = False
    custom_settings: Mapping[str, Any] = field(
        default_factory=lambda: MappingProxyType({})
    )
    is_active: bool = True
    is_deleted: bool = False

    def __post_init__(self):
        object.__setattr__(
            self,
            "custom_settings",
            _immutable_mapping(self.custom_settings),
        )

    @property
    def is_available(self) -> bool:
        return self.is_active and not self.is_deleted


@dataclass(frozen=True, slots=True)
class MunicipalityIdentity:
    """Identidad oficial del municipio asociado al tenant."""

    id: UUID
    code: str
    name: str
    state_code: str = ""
    state_name: str = ""
    is_active: bool = True
    is_deleted: bool = False

    @property
    def is_available(self) -> bool:
        return self.is_active and not self.is_deleted

    @property
    def normalized_code(self) -> str:
        return self.code.strip().zfill(3)


@dataclass(frozen=True, slots=True)
class TenantIdentity:
    """Configuración institucional necesaria para Inventory."""

    id: UUID
    institution_name: str
    acronym: str
    municipality: MunicipalityIdentity | None = None
    official_address: str = ""
    tax_id: str = ""
    is_active: bool = True
    is_deleted: bool = False

    @property
    def is_available(self) -> bool:
        return self.is_active and not self.is_deleted


@dataclass(frozen=True, slots=True)
class DepartmentApprovalAuthority:
    """
    Resultado explicable de evaluar si un usuario puede autorizar por una
    dependencia.

    Este contrato no decide permisos; solamente transporta el resultado
    calculado por el adaptador o por la capa de permisos.
    """

    user_id: UUID
    department_id: UUID
    allowed: bool
    reason: str
    bypass_used: bool = False
    source: str = ""


__all__ = [
    "AreaContext",
    "DepartmentApprovalAuthority",
    "DepartmentCapabilityIdentity",
    "DepartmentIdentity",
    "ModuleRoleIdentity",
    "MunicipalityIdentity",
    "SiteIdentity",
    "TenantIdentity",
    "UserIdentity",
    "UserOrganizationalContext",
]


