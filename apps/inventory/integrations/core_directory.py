# apps/inventory/integrations/core_directory.py

"""
Adaptador entre Inventory y el directorio institucional del Core.

Este es el único archivo de Inventory que debe importar modelos de
``apps.security``. Los servicios de negocio deben consumir exclusivamente las
funciones y contratos publicados aquí.
"""

from uuid import UUID

from apps.inventory.integrations.contracts import (
    AreaContext,
    DepartmentApprovalAuthority,
    DepartmentCapabilityIdentity,
    DepartmentIdentity,
    ModuleRoleIdentity,
    MunicipalityIdentity,
    SiteIdentity,
    TenantIdentity,
    UserIdentity,
    UserOrganizationalContext,
)
from apps.security.models import (
    AppDependencyCapability,
    AreaOperativa,
    Dependencia,
    Municipality,
    Sede,
    TenantConfig,
    User,
    UserAppRole,
    UserProfile,
)


INVENTORY_APP_SLUG = "inventory"
DEPARTMENT_APPROVAL_PERMISSION = (
    "inventory.intake.approve_department"
)
INVENTORY_MANAGE_PERMISSION = "inventory.manage"


class CoreDirectoryError(Exception):
    """Error base de integración con el directorio del Core."""


class InvalidDirectoryIdentifier(CoreDirectoryError):
    """El identificador recibido no es un UUID válido."""


class DirectoryEntityNotFound(CoreDirectoryError):
    """La entidad solicitada no existe o no está disponible."""


class OrganizationalContextError(CoreDirectoryError):
    """La estructura organizacional recibida es inconsistente."""


def _as_uuid(value, *, field_name: str) -> UUID:
    if isinstance(value, UUID):
        return value

    try:
        return UUID(str(value))
    except (TypeError, ValueError, AttributeError) as exc:
        raise InvalidDirectoryIdentifier(
            f"{field_name} debe ser un UUID válido."
        ) from exc


def _user_to_identity(user: User) -> UserIdentity:
    display_name = (
        getattr(user, "full_name", "")
        or user.get_full_name()
        or user.email
    )

    return UserIdentity(
        id=user.pk,
        email=user.email or "",
        display_name=display_name.strip(),
        first_name=(user.first_name or "").strip(),
        last_name=(user.last_name or "").strip(),
        is_active=user.is_active,
        is_deleted=user.is_deleted,
        is_staff=user.is_staff,
        is_superuser=user.is_superuser,
        is_manager=user.is_manager,
    )


def _department_to_identity(
    department: Dependencia,
) -> DepartmentIdentity:
    return DepartmentIdentity(
        id=department.pk,
        name=(department.nombre or "").strip(),
        code=(department.codigo_presupuestal or "").strip(),
        slug=(department.slug or "").strip(),
        parent_id=department.parent_id,
        manager_user_id=department.encargado_departamento_id,
        is_active=department.is_active,
        is_deleted=department.is_deleted,
    )


def _site_to_identity(site: Sede) -> SiteIdentity:
    return SiteIdentity(
        id=site.pk,
        name=(site.nombre or "").strip(),
        address=(site.direccion or "").strip(),
        technical_manager_user_id=site.encargado_sede_id,
        is_active=site.is_active,
        is_deleted=site.is_deleted,
    )


def _area_to_context(area: AreaOperativa) -> AreaContext:
    return AreaContext(
        id=area.pk,
        name=(area.nombre or "").strip(),
        slug=(area.slug or "").strip(),
        department=_department_to_identity(area.dependencia),
        site=_site_to_identity(area.sede_fisica),
        is_active=area.is_active,
        is_deleted=area.is_deleted,
    )


def get_user_identity(
    user_id,
    *,
    include_unavailable: bool = False,
) -> UserIdentity:
    resolved_id = _as_uuid(user_id, field_name="user_id")

    try:
        user = User.objects.get(pk=resolved_id)
    except User.DoesNotExist as exc:
        raise DirectoryEntityNotFound(
            "El usuario solicitado no existe."
        ) from exc

    identity = _user_to_identity(user)

    if not include_unavailable and not identity.is_available:
        raise DirectoryEntityNotFound(
            "El usuario solicitado no está disponible."
        )

    return identity


def get_department(
    department_id,
    *,
    include_unavailable: bool = False,
) -> DepartmentIdentity:
    resolved_id = _as_uuid(
        department_id,
        field_name="department_id",
    )

    try:
        department = (
            Dependencia.objects
            .select_related("parent", "encargado_departamento")
            .get(pk=resolved_id)
        )
    except Dependencia.DoesNotExist as exc:
        raise DirectoryEntityNotFound(
            "La dependencia solicitada no existe."
        ) from exc

    identity = _department_to_identity(department)

    if not include_unavailable and not identity.is_available:
        raise DirectoryEntityNotFound(
            "La dependencia solicitada no está disponible."
        )

    return identity


def get_site(
    site_id,
    *,
    include_unavailable: bool = False,
) -> SiteIdentity:
    resolved_id = _as_uuid(site_id, field_name="site_id")

    try:
        site = (
            Sede.objects
            .select_related("encargado_sede")
            .get(pk=resolved_id)
        )
    except Sede.DoesNotExist as exc:
        raise DirectoryEntityNotFound(
            "La sede solicitada no existe."
        ) from exc

    identity = _site_to_identity(site)

    if not include_unavailable and not identity.is_available:
        raise DirectoryEntityNotFound(
            "La sede solicitada no está disponible."
        )

    return identity


def get_area_context(
    area_id,
    *,
    include_unavailable: bool = False,
) -> AreaContext:
    resolved_id = _as_uuid(area_id, field_name="area_id")

    try:
        area = (
            AreaOperativa.objects
            .select_related(
                "dependencia",
                "dependencia__parent",
                "dependencia__encargado_departamento",
                "sede_fisica",
                "sede_fisica__encargado_sede",
            )
            .get(pk=resolved_id)
        )
    except AreaOperativa.DoesNotExist as exc:
        raise DirectoryEntityNotFound(
            "El área operativa solicitada no existe."
        ) from exc

    context = _area_to_context(area)

    if not include_unavailable and not context.is_available:
        raise DirectoryEntityNotFound(
            "El área operativa solicitada no está disponible."
        )

    return context


def get_user_organizational_context(
    user_id,
    *,
    require_profile: bool = False,
    include_unavailable: bool = False,
) -> UserOrganizationalContext:
    user = get_user_identity(
        user_id,
        include_unavailable=include_unavailable,
    )

    profile = (
        UserProfile.objects
        .select_related(
            "area",
            "area__dependencia",
            "area__dependencia__parent",
            "area__dependencia__encargado_departamento",
            "area__sede_fisica",
            "area__sede_fisica__encargado_sede",
        )
        .filter(user_id=user.id)
        .first()
    )

    if not profile:
        if require_profile:
            raise OrganizationalContextError(
                "El usuario no tiene un perfil laboral configurado."
            )

        return UserOrganizationalContext(user=user)

    area_context = _area_to_context(profile.area)

    if (
        not include_unavailable
        and not area_context.is_available
    ):
        raise OrganizationalContextError(
            "La adscripción organizacional del usuario no está disponible."
        )

    return UserOrganizationalContext(
        user=user,
        profile_id=profile.pk,
        position=(profile.puesto or "").strip(),
        office_phone=(profile.telefono_oficina or "").strip(),
        area=area_context,
    )


def list_sites(*, department_id=None):
    queryset = Sede.objects.filter(
        is_active=True,
        is_deleted=False,
    )
    if department_id:
        queryset = queryset.filter(
            areas__dependencia_id=_as_uuid(
                department_id,
                field_name="department_id",
            ),
            areas__is_active=True,
            areas__is_deleted=False,
        )
    return tuple(
        _site_to_identity(site)
        for site in queryset.distinct().order_by("nombre")
    )


def list_departments(*, site_id=None):
    queryset = Dependencia.objects.filter(
        is_active=True,
        is_deleted=False,
    ).select_related("parent", "encargado_departamento")
    if site_id:
        queryset = queryset.filter(
            areas__sede_fisica_id=_as_uuid(site_id, field_name="site_id"),
            areas__is_active=True,
            areas__is_deleted=False,
        )
    return tuple(
        _department_to_identity(department)
        for department in queryset.distinct().order_by("nombre")
    )


def list_areas(*, department_id=None, site_id=None):
    queryset = AreaOperativa.objects.filter(
        is_active=True,
        is_deleted=False,
        dependencia__is_active=True,
        dependencia__is_deleted=False,
        sede_fisica__is_active=True,
        sede_fisica__is_deleted=False,
    ).select_related(
        "dependencia",
        "dependencia__parent",
        "dependencia__encargado_departamento",
        "sede_fisica",
        "sede_fisica__encargado_sede",
    )
    if department_id:
        queryset = queryset.filter(
            dependencia_id=_as_uuid(department_id, field_name="department_id")
        )
    if site_id:
        queryset = queryset.filter(
            sede_fisica_id=_as_uuid(site_id, field_name="site_id")
        )
    return tuple(_area_to_context(area) for area in queryset.order_by("nombre"))


def list_users(*, department_id=None, area_id=None):
    queryset = UserProfile.objects.filter(
        user__is_active=True,
        user__is_deleted=False,
        is_active=True,
        is_deleted=False,
        area__is_active=True,
        area__is_deleted=False,
    ).select_related("user", "area", "area__dependencia")
    if department_id:
        queryset = queryset.filter(
            area__dependencia_id=_as_uuid(
                department_id,
                field_name="department_id",
            )
        )
    if area_id:
        queryset = queryset.filter(
            area_id=_as_uuid(area_id, field_name="area_id")
        )
    return tuple(
        _user_to_identity(profile.user)
        for profile in queryset.order_by(
            "user__first_name",
            "user__last_name",
            "user__email",
        )
    )


def get_module_role(
    user_id,
    *,
    app_slug: str = INVENTORY_APP_SLUG,
    required: bool = False,
) -> ModuleRoleIdentity | None:
    resolved_user_id = _as_uuid(user_id, field_name="user_id")
    normalized_slug = app_slug.strip().lower()

    role = (
        UserAppRole.objects
        .select_related("app")
        .filter(
            user_id=resolved_user_id,
            app__slug=normalized_slug,
            app__is_active=True,
            app__is_deleted=False,
            is_active=True,
            is_deleted=False,
        )
        .first()
    )

    if not role:
        if required:
            raise DirectoryEntityNotFound(
                "El usuario no tiene un rol activo para el módulo."
            )
        return None

    permissions = tuple(
        str(permission).strip()
        for permission in (role.permissions_list or [])
        if str(permission).strip()
    )

    return ModuleRoleIdentity(
        app_id=role.app_id,
        app_slug=role.app.slug,
        role=role.role,
        permissions=permissions,
        is_active=role.is_active,
        is_deleted=role.is_deleted,
    )


def get_department_capability(
    department_id,
    *,
    app_slug: str = INVENTORY_APP_SLUG,
    required: bool = False,
) -> DepartmentCapabilityIdentity | None:
    resolved_department_id = _as_uuid(
        department_id,
        field_name="department_id",
    )
    normalized_slug = app_slug.strip().lower()

    capability = (
        AppDependencyCapability.objects
        .select_related("app", "dependencia")
        .filter(
            dependencia_id=resolved_department_id,
            app__slug=normalized_slug,
            app__is_active=True,
            app__is_deleted=False,
            is_active=True,
            is_deleted=False,
        )
        .first()
    )

    if not capability:
        if required:
            raise DirectoryEntityNotFound(
                "La dependencia no tiene capacidades para el módulo."
            )
        return None

    return DepartmentCapabilityIdentity(
        app_id=capability.app_id,
        app_slug=capability.app.slug,
        department_id=capability.dependencia_id,
        can_operate=capability.can_operate,
        can_supervise=capability.can_supervise,
        can_authorize=capability.can_authorize,
        custom_settings=capability.custom_settings or {},
        is_active=capability.is_active,
        is_deleted=capability.is_deleted,
    )


def get_active_tenant() -> TenantIdentity:
    tenant = (
        TenantConfig.objects
        .select_related("municipality")
        .filter(
            is_active=True,
            is_deleted=False,
        )
        .order_by("created_at")
        .first()
    )

    if not tenant:
        raise DirectoryEntityNotFound(
            "No existe una configuración institucional activa."
        )

    municipality = None

    if tenant.municipality_id:
        municipality_model: Municipality = tenant.municipality
        municipality = MunicipalityIdentity(
            id=municipality_model.pk,
            code=municipality_model.code,
            name=municipality_model.name,
            state_code=municipality_model.state_code,
            state_name=municipality_model.state_name,
            is_active=municipality_model.is_active,
            is_deleted=municipality_model.is_deleted,
        )

    return TenantIdentity(
        id=tenant.pk,
        institution_name=tenant.entidad_nombre,
        acronym=tenant.siglas,
        municipality=municipality,
        official_address=tenant.direccion_oficial,
        tax_id=tenant.rfc,
        is_active=tenant.is_active,
        is_deleted=tenant.is_deleted,
    )


def validate_organizational_context(
    *,
    department_id,
    area_id=None,
    site_id=None,
) -> AreaContext | None:
    department = get_department(department_id)

    if area_id is None:
        if site_id is not None:
            get_site(site_id)
        return None

    area = get_area_context(area_id)

    if area.department_id != department.id:
        raise OrganizationalContextError(
            "El área no pertenece a la dependencia indicada."
        )

    if site_id is not None:
        resolved_site_id = _as_uuid(
            site_id,
            field_name="site_id",
        )

        if area.site_id != resolved_site_id:
            raise OrganizationalContextError(
                "La sede indicada no coincide con la sede del área."
            )

    return area


def user_belongs_to_department(
    user_id,
    department_id,
) -> bool:
    resolved_department_id = _as_uuid(
        department_id,
        field_name="department_id",
    )

    context = get_user_organizational_context(
        user_id,
        require_profile=False,
    )

    return context.department_id == resolved_department_id


def user_can_manage_inventory(user_id) -> bool:
    user = get_user_identity(user_id)

    if user.has_global_bypass:
        return True

    role = get_module_role(user.id)

    if not role:
        return False

    normalized_role = role.role.strip().lower()

    return (
        normalized_role in {"owner", "admin"}
        or role.has_permission(INVENTORY_MANAGE_PERMISSION)
    )


def user_can_approve_department(
    user_id,
    department_id,
) -> DepartmentApprovalAuthority:
    user = get_user_identity(user_id)
    department = get_department(department_id)

    if user.has_global_bypass:
        return DepartmentApprovalAuthority(
            user_id=user.id,
            department_id=department.id,
            allowed=True,
            reason=(
                "Usuario con privilegio global root/manager. "
                "La operación debe registrar motivo de bypass."
            ),
            bypass_used=True,
            source="global_bypass",
        )

    if department.manager_user_id == user.id:
        return DepartmentApprovalAuthority(
            user_id=user.id,
            department_id=department.id,
            allowed=True,
            reason="Titular o encargado registrado de la dependencia.",
            bypass_used=False,
            source="department_manager",
        )

    context = get_user_organizational_context(
        user.id,
        require_profile=False,
    )

    if context.department_id != department.id:
        return DepartmentApprovalAuthority(
            user_id=user.id,
            department_id=department.id,
            allowed=False,
            reason=(
                "El usuario no está adscrito a la dependencia."
            ),
            source="different_department",
        )

    role = get_module_role(user.id)
    capability = get_department_capability(department.id)

    has_delegated_permission = bool(
        role
        and role.has_permission(DEPARTMENT_APPROVAL_PERMISSION)
    )
    department_can_authorize = bool(
        capability
        and capability.is_available
        and capability.can_authorize
    )

    if has_delegated_permission and department_can_authorize:
        return DepartmentApprovalAuthority(
            user_id=user.id,
            department_id=department.id,
            allowed=True,
            reason=(
                "Delegación válida mediante permiso fino y capacidad "
                "de autorización de la dependencia."
            ),
            bypass_used=False,
            source="delegated_permission",
        )

    return DepartmentApprovalAuthority(
        user_id=user.id,
        department_id=department.id,
        allowed=False,
        reason=(
            "El usuario no es titular de la dependencia ni cuenta con "
            "una delegación válida."
        ),
        bypass_used=False,
        source="insufficient_authority",
    )


def list_department_approvers(
    department_id,
) -> tuple[UserIdentity, ...]:
    department = get_department(department_id)
    user_ids: set[UUID] = set()

    if department.manager_user_id:
        user_ids.add(department.manager_user_id)

    capability = get_department_capability(department.id)

    if capability and capability.can_authorize:
        delegated_roles = (
            UserAppRole.objects
            .select_related("user")
            .filter(
                app__slug=INVENTORY_APP_SLUG,
                app__is_active=True,
                app__is_deleted=False,
                is_active=True,
                is_deleted=False,
                user__is_active=True,
                user__is_deleted=False,
                user__axentra_profile__area__dependencia_id=(
                    department.id
                ),
            )
        )

        for delegated_role in delegated_roles:
            permissions = delegated_role.permissions_list or []

            if DEPARTMENT_APPROVAL_PERMISSION in permissions:
                user_ids.add(delegated_role.user_id)

    users = (
        User.objects
        .filter(
            pk__in=user_ids,
            is_active=True,
            is_deleted=False,
        )
        .order_by("first_name", "last_name", "email")
    )

    return tuple(_user_to_identity(user) for user in users)


__all__ = [
    "CoreDirectoryError",
    "DEPARTMENT_APPROVAL_PERMISSION",
    "DirectoryEntityNotFound",
    "INVENTORY_APP_SLUG",
    "INVENTORY_MANAGE_PERMISSION",
    "InvalidDirectoryIdentifier",
    "OrganizationalContextError",
    "get_active_tenant",
    "get_area_context",
    "get_department",
    "get_department_capability",
    "get_module_role",
    "get_site",
    "get_user_identity",
    "get_user_organizational_context",
    "list_areas",
    "list_departments",
    "list_department_approvers",
    "list_sites",
    "list_users",
    "user_belongs_to_department",
    "user_can_approve_department",
    "user_can_manage_inventory",
    "validate_organizational_context",
]
