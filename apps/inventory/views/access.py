"""Resolución centralizada del alcance visible dentro de Inventory."""

from apps.inventory.integrations import core_directory
from apps.inventory.selectors import InventoryScope
from django.core.exceptions import PermissionDenied


def permission_keys(request):
    return {
        str(key).strip()
        for key in (getattr(request, "axentra_permissions_list", None) or [])
        if str(key).strip()
    }


def is_inventory_root(request):
    user = request.user
    return bool(
        getattr(request, "axentra_is_root", False)
        or getattr(user, "is_superuser", False)
        or getattr(user, "is_manager", False)
    )


def department_id(request):
    cache_name = "_inventory_department_id"
    if hasattr(request, cache_name):
        return getattr(request, cache_name)
    try:
        context = core_directory.get_user_organizational_context(
            request.user.pk,
            require_profile=False,
        )
        value = context.department_id if context else None
    except core_directory.CoreDirectoryError:
        value = None
    setattr(request, cache_name, value)
    return value


def asset_scope(request):
    """Patrimonio/auditoría ven todo; dirección ve su dependencia."""

    permissions = permission_keys(request)
    if is_inventory_root(request) or permissions.intersection({
        "can_validate_patrimony_intake",
        "can_register_asset",
        "can_manage_physical_audits",
        "can_view_audit",
    }):
        return InventoryScope.GLOBAL, None
    if permissions.intersection({
        "can_approve_department_intake",
        "can_authorize_movements",
        "can_authorize_loans",
    }):
        return InventoryScope.DEPARTMENT, department_id(request)
    return InventoryScope.OWN, None


def intake_scope(request):
    """Solicitudes propias, de dependencia o globales según responsabilidad."""

    permissions = permission_keys(request)
    if is_inventory_root(request) or permissions.intersection({
        "can_create_intake_for_any_department",
        "can_validate_patrimony_intake",
        "can_register_asset",
        "can_view_audit",
    }):
        return InventoryScope.GLOBAL, None
    if "can_approve_department_intake" in permissions:
        return InventoryScope.DEPARTMENT, department_id(request)
    return InventoryScope.OWN, None


def has_any_permission(request, *permissions):
    return is_inventory_root(request) or bool(
        permission_keys(request).intersection(permissions)
    )


def require_any_permission(request, *permissions):
    if not has_any_permission(request, *permissions):
        raise PermissionDenied(
            "No cuentas con permisos para realizar esta operación."
        )


def custody_scope(request):
    if has_any_permission(request, "can_manage_custody"):
        return "GLOBAL", None
    return "OWN", None


__all__ = [
    "asset_scope",
    "department_id",
    "custody_scope",
    "has_any_permission",
    "intake_scope",
    "is_inventory_root",
    "permission_keys",
    "require_any_permission",
]
