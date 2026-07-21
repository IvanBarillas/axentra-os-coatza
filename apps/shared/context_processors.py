# apps/shared/context_processors.py

import logging

from django.core.exceptions import ObjectDoesNotExist

from apps.security.models import TenantConfig, UserAppRole
from apps.shared.apps_config import AppIdentifier
from apps.shared.manifest_registry import AxentraOSRegistry
from apps.security.services.permission_loader import get_user_permissions_for_app
from apps.shared.utils.telemetry import AxentraRadar

logger = logging.getLogger(__name__)


def _normalizar_module_identifier(module_identifier) -> str:
    if hasattr(module_identifier, "value"):
        return str(module_identifier.value).strip().lower()
    return str(module_identifier).strip().lower()


def _usuario_es_root(request) -> bool:
    profile = getattr(request.user, "axentra_profile", None)
    return bool(
        getattr(request.user, "is_superuser", False)
        or getattr(request.user, "is_manager", False)
        or getattr(profile, "is_root_admin", False)
    )


def _usuario_dado_de_baja(user) -> bool:
    return bool(getattr(user, "is_deleted", False))


def _operator_identity(request, modulo_activo="launcher"):
    """Identidad laboral y membresía visible para la barra global."""
    user = request.user
    full_name = (
        getattr(user, "full_name", "")
        or user.get_full_name()
        or user.email
    )
    identity = {
        "name": full_name,
        "email": user.email,
        "role": "Sesión activa",
        "role_code": "",
        "department": "Sin dependencia asignada",
        "area": "Sin área asignada",
        "position": "Sin puesto registrado",
        "module": modulo_activo,
        "is_global_admin": _usuario_es_root(request),
    }

    try:
        profile = user.axentra_profile
    except (AttributeError, ObjectDoesNotExist):
        profile = None

    if profile:
        identity["position"] = profile.puesto or identity["position"]
        area = getattr(profile, "area", None)
        if area:
            identity["area"] = area.nombre
            dependencia = getattr(area, "dependencia", None)
            if dependencia:
                identity["department"] = dependencia.nombre

    if identity["is_global_admin"]:
        identity["role"] = "Administrador global"
        identity["role_code"] = "root"
        return identity

    if modulo_activo and modulo_activo != "launcher":
        membership = (
            UserAppRole.objects
            .filter(
                user=user,
                app__slug=modulo_activo,
                is_active=True,
                is_deleted=False,
                app__is_active=True,
                app__is_deleted=False,
            )
            .only("role")
            .first()
        )
        if membership:
            identity["role_code"] = membership.role
            identity["role"] = membership.role.replace("_", " ").title()
        else:
            identity["role"] = "Sin rol en este módulo"

    return identity


def _normalizar_sidebar_item(item):
    """
    Soporta SIDEBAR_MENU viejo y nuevo.

    Viejo:
        ["users", "Usuarios", "accounts:funcionario_list", 1, "can_view_list"]

    Nuevo:
        {
            "icon": "users",
            "name": "Usuarios",
            "url": "accounts:funcionario_list",
            "order": 1,
            "permission": "can_view_list",
        }
    """
    if isinstance(item, dict):
        return {
            "icon": item.get("icon", "circle"),
            "name": item.get("name") or item.get("title") or "Sin título",
            "url": item.get("url") or item.get("url_name"),
            "order": item.get("order", 99),
            "permission": item.get("permission"),
        }

    try:
        icon, name, url, order, permission = item
        return {
            "icon": icon,
            "name": name,
            "url": url,
            "order": order,
            "permission": permission,
        }
    except Exception:
        return None


def _tiene_permiso_fino(permisos, lista_llaves, modulo_activo, permiso_req) -> bool:
    if not permiso_req:
        return True

    llave_compuesta = f"{modulo_activo}__{permiso_req}"

    return bool(
        permisos.get(permiso_req, False)
        or permisos.get(llave_compuesta, False)
        or permiso_req in lista_llaves
        or llave_compuesta in lista_llaves
    )


def _filtrar_sidebar_menu(request, modulo_activo, menu_crudo):
    es_root = _usuario_es_root(request)
    menu_filtrado = []

    if es_root:
        for raw_item in menu_crudo:
            item = _normalizar_sidebar_item(raw_item)
            if not item:
                continue

            menu_filtrado.append({
                "icon": item["icon"],
                "name": item["name"],
                "url": item["url"],
                "order": item["order"],
                "permission": item.get("permission"),
            })

        menu_filtrado.sort(key=lambda item: item["order"])
        return menu_filtrado

    permisos = get_user_permissions_for_app(request.user, modulo_activo)
    lista_llaves = permisos.get("permissions_list", []) or []

    for raw_item in menu_crudo:
        item = _normalizar_sidebar_item(raw_item)
        if not item:
            continue

        permiso_req = item.get("permission")

        if _tiene_permiso_fino(
            permisos=permisos,
            lista_llaves=lista_llaves,
            modulo_activo=modulo_activo,
            permiso_req=permiso_req,
        ):
            menu_filtrado.append({
                "icon": item["icon"],
                "name": item["name"],
                "url": item["url"],
                "order": item["order"],
                "permission": permiso_req,
            })

    menu_filtrado.sort(key=lambda item: item["order"])
    return menu_filtrado


def global_tenant_settings(request):
    """
    Inyecta activos de marca e identidad legal a todos los templates.
    """
    try:
        config = TenantConfig.objects.filter(is_deleted=False).first()

        if not config:
            config = TenantConfig.objects.create(
                app_name="Axentra OS",
                entidad_nombre="Axentra Infrastructure",
                siglas="AXN",
                is_active=True,
                is_deleted=False,
            )

        return {"tenant": config}

    except Exception as e:
        logger.error(f"Error en global_tenant_settings: {e}")
        return {"tenant": None}


def user_module_permissions(request):
    """
    Inyecta módulos autorizados para el launcher y sidebar global.
    """
    context = {
        "allowed_modules": [],
        "is_global_admin": False,
    }

    if not request.user.is_authenticated:
        return context

    if _usuario_dado_de_baja(request.user):
        return context

    if _usuario_es_root(request):
        slugs_totales = [
            choice[0]
            for choice in AppIdentifier.get_choices()
        ]

        AxentraRadar.imprimir_auditoria(
            componente="user_module_permissions",
            request=request,
            titulo="Bypass de Nivel Maestro Detectado",
            icono="👑",
            extra_data={
                "Estado Privilegios": (
                    f"SUPERUSER={request.user.is_superuser} | "
                    f"MANAGER={getattr(request.user, 'is_manager', False)} | "
                    f"ROOT_ADMIN={_usuario_es_root(request)}"
                ),
                "Módulos Forzados Globales": slugs_totales,
            },
        )

        return {
            "is_global_admin": True,
            "allowed_modules": slugs_totales,
        }

    roles_activos = (
        UserAppRole.objects
        .select_related("app")
        .filter(
            user=request.user,
            is_active=True,
            is_deleted=False,
            app__is_active=True,
            app__is_deleted=False,
        )
    )

    allowed_slugs = [
        role.app.slug
        for role in roles_activos
    ]

    AxentraRadar.imprimir_auditoria(
        componente="user_module_permissions",
        request=request,
        titulo="Radar Perimetral de Launcher",
        icono="🔍",
        extra_data={
            "Celdas Localizadas en BD": roles_activos.count(),
            "Slugs Despachados al DOM": allowed_slugs,
            "Análisis de Permisos": [
                f"App: '{role.app.slug}' | Rol: '{role.role}' | Llaves: {role.permissions_list}"
                for role in roles_activos
            ] if roles_activos.exists() else "⚠️ ADVERTENCIA: 0 aplicativos para este ID.",
        },
    )

    return {
        "is_global_admin": False,
        "allowed_modules": allowed_slugs,
    }


def menu_dinamico_processor(request):
    """
    Expone menú contextual calculado por el decorador o reconstruido por fallback.

    Importante:
    - No fuerza sidebar secundario en pantallas directas.
    - Si una vista necesita sidebar contextual, debe enviar show_module_sidebar=True.
    - Este processor sólo expone menu_actual/sidebar_menu para compatibilidad.
    """
    context = {
        "menu_actual": [],
        "modulo_actual": "launcher",
        "sidebar_menu": [],
        "sidebar_secundario": False,
    }

    if not request.user.is_authenticated:
        return context

    if _usuario_dado_de_baja(request.user):
        return context

    modulo_activo = getattr(request, "axentra_active_module", None)

    if not modulo_activo and getattr(request, "resolver_match", None):
        modulo_activo = request.resolver_match.namespace

    modulo_activo = _normalizar_module_identifier(modulo_activo or "launcher")

    context["operator_identity"] = _operator_identity(
        request,
        modulo_activo,
    )

    if not modulo_activo or modulo_activo == "launcher":
        return context

    context["modulo_actual"] = modulo_activo

    if hasattr(request, "axentra_sidebar_menu"):
        menu_final = request.axentra_sidebar_menu or []
        context["menu_actual"] = menu_final
        context["sidebar_menu"] = menu_final
        context["sidebar_secundario"] = False
        return context

    manifiesto_modulo = AxentraOSRegistry.get_manifest_by_slug(modulo_activo)

    if not manifiesto_modulo or not hasattr(manifiesto_modulo, "SIDEBAR_MENU"):
        return context

    menu_filtrado = _filtrar_sidebar_menu(
        request=request,
        modulo_activo=modulo_activo,
        menu_crudo=manifiesto_modulo.SIDEBAR_MENU,
    )

    context["menu_actual"] = menu_filtrado
    context["sidebar_menu"] = menu_filtrado
    context["sidebar_secundario"] = False

    return context
