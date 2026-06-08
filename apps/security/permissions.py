# apps/security/permissions.py
from apps.shared.apps_config import AppIdentifier

# =========================================================================
# 🛡️ CLASE 1: DOMINIO DE CIBERSEGURIDAD CENTRAL
# =========================================================================
class SecurityPermissions:
    APP_CODE = AppIdentifier.SECURITY

    LAUNCHER_CARD = {
        'title': 'Ciberseguridad & Control Global',
        'description': 'Consola táctica de gobernanza. Gestión atómica de llaves JSON, monitoreo forense de bitácoras e identidad legal de la entidad.',
        'icon': 'shield-check',
        'badge_text': 'Core Security',
        'hover_color': 'hover:border-blue-600',
        'text_hover_color': 'group-hover:text-blue-600',
        'url_name': 'security:dashboard',
        'is_core': True,
    }

    PERMISSIONS = {
        'security__has_access': 'Permite el ingreso general a la Consola de Ciberseguridad.',
        'security__can_view_matrix': 'Permite auditar y visualizar las rejillas de privilegios JSON.',
        'security__can_modify_matrix': 'Acción Crítica Máxima: Permite re-grabar y mutar llaves JSON de funcionarios.',
        'security__can_configure_tenant': 'Acción Crítica Core: Permite alterar la identidad visual, logos y RFC legal de la entidad.',
    }

    ROLE_MAPPING = {
        'owner': ['security__has_access', 'security__can_view_matrix', 'security__can_modify_matrix', 'security__can_configure_tenant'],
        'admin': ['security__has_access', 'security__can_view_matrix', 'security__can_modify_matrix', 'security__can_configure_tenant'],
    }

    SIDEBAR_MENU = [
        ["sliders", "Cabina de Mando", "security:dashboard", 1, "security__has_access"],
        ["grid", "Matriz de Permisos", "security:dynamic_matrix", 2, "security__can_view_matrix"],
        ["settings", "Identidad Global", "security:tenant_config", 3, "security__can_configure_tenant"],
    ]


# =========================================================================
# 👥 CLASE 2: DOMINIO DE CAPITAL HUMANO (ACCOUNTS)
# =========================================================================
class AccountsPermissions:
    APP_CODE = AppIdentifier.ACCOUNTS

    LAUNCHER_CARD = {
        'title': 'Plantilla de Personal',
        'description': 'CRUD de alta densidad para la gestión de expedientes, captura de datos duros y movimientos de los funcionarios públicos.',
        'icon': 'users',
        'badge_text': 'Cuentas',
        'hover_color': 'hover:border-slate-400',
        'text_hover_color': 'group-hover:text-slate-700',
        'url_name': 'accounts:dashboard',
        'is_core': True,
    }

    PERMISSIONS = {
        'accounts__has_access': 'Permite el ingreso perimetral al control operativo de personal.',
        'accounts__can_view_list': 'Permite consultar el padrón institucional de expedientes laborales.',
        'accounts__can_create_user': 'Acción Operativa: Permite dar de alta nuevos funcionarios.',
        'accounts__can_edit_user': 'Acción Operativa: Permite modificar la ficha de identidad laboral.',
        'accounts__can_change_password': 'Acción Crítica: Permite forzar el reseteo administrativo de contraseñas.',
        'accounts__can_delete_user': 'Acción Crítica: Permite aplicar bajas del sistema.',
    }

    ROLE_MAPPING = {
        'owner': ['accounts__has_access', 'accounts__can_view_list', 'accounts__can_create_user', 'accounts__can_edit_user', 'accounts__can_change_password', 'accounts__can_delete_user'],
        'editor_rh': ['accounts__has_access', 'accounts__can_view_list', 'accounts__can_create_user', 'accounts__can_edit_user'],
    }

    SIDEBAR_MENU = [
        ["sliders", "Cabina de Mando", "accounts:dashboard", 1, "accounts__has_access"],
        ["users", "Padrón de Empleados", "accounts:funcionario_list_table", 2, "accounts__can_view_list"],
        ["user-plus", "Alta de Servidor", "accounts:funcionario_create", 3, "accounts__can_create_user"],
    ]


# =========================================================================
# 🏛️ CLASE 3: DOMINIO DE ESTRUCTURA ORGÁNICA (ORGANIGRAMA)
# =========================================================================
class OrganigramaPermissions:
    APP_CODE = AppIdentifier.ORGANIGRAMA

    LAUNCHER_CARD = {
        'title': 'Estructura Orgánica',
        'description': 'Modelado de Direcciones Generales, Oficinas Internas, Departamentos y control geográfico de Sedes físicas del Ayuntamiento.',
        'icon': 'git-fork',
        'badge_text': 'Estructura',
        'hover_color': 'hover:border-blue-600',
        'text_hover_color': 'group-hover:text-blue-600',
        'url_name': 'organigrama:dashboard', 
        'is_core': True,
    }

    PERMISSIONS = {
        'organigrama__has_access': 'Permite visualizar el mapa estructural e interactivo del Ayuntamiento.',
        'organigrama__can_view_analytics': 'Permite auditar reportes de densidad laboral y KPIs institucionales.',
        'organigrama__can_manage_infrastructure': 'Acción Crítica Inmueble: Permite administrar, crear y desactivar Sedes y Palacios.',
        'organigrama__can_mutate_structure': 'Acción Crítica Orgánica: Permite dar de alta Secretarías, Direcciones y Oficinas.',
    }

    ROLE_MAPPING = {
        'owner': ['organigrama__has_access', 'organigrama__can_view_analytics', 'organigrama__can_manage_infrastructure', 'organigrama__can_mutate_structure'],
    }

    SIDEBAR_MENU = [
        ["bar-chart-3", "Dashboard del Core", "organigrama:dashboard", 1, "organigrama__can_view_analytics"],
        ["git-fork", "Estructura Orgánica", "organigrama:estructura_list", 2, "organigrama__has_access"],
        ["map-pin", "Sedes e Inmuebles", "organigrama:sede_list", 3, "organigrama__can_manage_infrastructure"],
    ]