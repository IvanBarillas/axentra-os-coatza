# apps/security/permissions.py
from apps.shared.apps_config import AppIdentifier

# =========================================================================
# 🛡️ CLASE 1: DOMINIO DE CIBERSEGURIDAD CENTRAL (SECURITY)
# =========================================================================
class SecurityPermissions:
    APP_CODE = AppIdentifier.SECURITY

    LAUNCHER_CARD = {
        'title': 'Ciberseguridad & Control Global',
        'description': 'Consola táctica de gobernanza. Gestión atómica de llaves JSON, monitoreo forense de bitácoras e identidad legal de la entidad.',
        'icon': 'shield-check',
        'button_text': 'Permisos y Auditoria',       
        'badge_text': 'Core Security',
        'hover_color': 'hover:border-blue-600',
        'text_hover_color': 'group-hover:text-blue-600',
        'url_name': 'security:control_panel',
        'is_core': True,
    }

    PERMISSIONS = {
        'has_access_module': 'Permite el ingreso general a la Estación de Control de Ciberseguridad.',
        'can_view_analytics': 'Permite auditar el tráfico forense de bitácoras y telemetría en el Dashboard de Seguridad.',
        'can_view_matrix': 'Permite auditar y visualizar las rejillas de privilegios JSON.',
        'can_modify_matrix': 'Acción Crítica Máxima: Permite re-grabar y mutar llaves JSON de funcionarios.',
        'can_configure_tenant': 'Acción Crítica Core: Permite alterar la identidad visual, logos y RFC legal de la entidad.',
    }

    # 🟢 CALIBRACIÓN ATÓMICA DE LOS 5 ROLES OBLIGATORIOS
    ROLE_MAPPING = {
        'owner': ['has_access_module', 'can_view_analytics', 'can_view_matrix', 'can_modify_matrix', 'can_configure_tenant'],
        'admin': ['has_access_module', 'can_view_analytics', 'can_view_matrix', 'can_modify_matrix'],
        'editor': ['has_access_module', 'can_view_analytics', 'can_view_matrix'],
        'reviewer': ['has_access_module', 'can_view_matrix'],
        'viewer': ['has_access_module'],
    }

    # 🛰️ SIDEBAR TOTALMENTE CALIBRADO CON EL NUEVO ENDPOINT FORENSE (SIN EMOJIS)
    SIDEBAR_MENU = [
        ["layout-dashboard", "Cuarto de Control", "security:control_panel", 1, "has_access_module"],
        ["activity", "Auditoría Forense", "security:global_matrix_forensic", 3, "can_view_matrix"],
        ["bar-chart-3", "Consola Analítica", "security:dashboard", 4, "can_view_analytics"],
        ["settings", "Identidad Global", "security:tenant_config", 5, "can_configure_tenant"],
    ]
    
    # 🛰️ CONFIGURACIÓN LOGÍSTICA DE CAPACIDADES (Semántica de Negocio Local Organigrama)
    CAPABILITIES = {
        'flag_alfa': {
            'label': "🛠️ [Security] ¿Es Dependencia Proveedora de Seguridad?",
            'help_text': (
                "EFECTO EN SISTEMA: Al activar esta casilla, el personal adscrito a esta dirección "
                "será elegible para aparecer en el combo box de 'Alta de Perfil Técnico' (Comisionar Ingeniero). "
                "Úselo exclusivamente para la Dirección de Tecnologías, Innovación o Soporte de Sistemas."
            )
        },
        'flag_beta': {
            'label': "📋 [Security] ¿Es Dependencia Consumidora Estricta (Solo Reportes)?",
            'help_text': (
                "EFECTO EN SISTEMA: Indica que esta área solo puede levantar reportes y visualizar sus propios folios. "
                "El sistema aislará sus combo boxes para que al crear un ticket, solo puedan seleccionar "
                "las Sedes y Áreas Físicas que pertenezcan formalmente a su propia dirección."
            )
        }
    }


# =========================================================================
# 👥 CLASE 2: DOMINIO DE CAPITAL HUMANO (ACCOUNTS)
# =========================================================================
class AccountsPermissions:
    APP_CODE = AppIdentifier.ACCOUNTS

    LAUNCHER_CARD = {
        'title': 'Plantilla de Personal',
        'description': 'CRUD de alta densidad para la gestión de expedientes, captura de datos duros y movimientos de los funcionarios públicos.',
        'icon': 'users',
        'button_text': 'Usuarios y Perfiles',
        'badge_text': 'Cuentas',
        'hover_color': 'hover:border-slate-400',
        'text_hover_color': 'group-hover:text-slate-700',
        'url_name': 'accounts:control_panel',
        'is_core': True,
    }

    PERMISSIONS = {
        'has_access_module': 'Permite el ingreso general a la Estación de Control de Personal.',
        'can_view_analytics': 'Permite auditar reportes de densidad laboral, gráficas de personal y KPIs de nómina en el Dashboard.',
        'can_view_list': 'Permite consultar el padrón institucional de expedientes laborales.',
        'can_create_user': 'Acción Operativa: Permite dar de alta nuevos funcionarios.',
        'can_edit_user': 'Acción Operativa: Permite modificar la ficha de identidad laboral.',
        'can_change_password': 'Acción Crítica: Permite forzar el reseteo administrativo de contraseñas.',
        'can_delete_user': 'Acción Crítica: Permite aplicar bajas del sistema.',
    }

    # 🟢 CALIBRACIÓN ATÓMICA DE LOS 5 ROLES OBLIGATORIOS (Adaptando editor_rh a editor)
    ROLE_MAPPING = {
        'owner': ['has_access_module', 'can_view_analytics', 'can_view_list', 'can_create_user', 'can_edit_user', 'can_change_password', 'can_delete_user'],
        'admin': ['has_access_module', 'can_view_analytics', 'can_view_list', 'can_create_user', 'can_edit_user', 'can_change_password'],
        'editor': ['has_access_module', 'can_view_list', 'can_create_user', 'can_edit_user'],
        'reviewer': ['has_access_module', 'can_view_list'],
        'viewer': ['has_access_module'],
    }

    SIDEBAR_MENU = [
        ["layout-dashboard", "Cuarto de Control", "accounts:control_panel", 1, "has_access_module"],
        ["users", "Padrón de Empleados", "accounts:funcionario_list", 2, "can_view_list"],
        ["user-plus", "Alta de Servidor", "accounts:funcionario_create", 3, "can_create_user"],
        ["bar-chart-3", "Consola Analítica", "accounts:dashboard", 4, "can_view_analytics"],
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
        "button_text": "Estructura Organica",
        'badge_text': 'Estructura',
        'hover_color': 'hover:border-blue-600',
        'text_hover_color': 'group-hover:text-blue-600',
        'url_name': 'organigrama:control_panel', 
        'is_core': True,
    }

    PERMISSIONS = {
        'has_access_module': 'Permite el ingreso general a la Estación de Control y consultar el catálogo básico.',
        'can_view_analytics': 'Permite auditar reportes de densidad laboral, gráficas de personal y KPIs institucionales en el Dashboard.',
        'can_manage_infrastructure': 'Acción Crítica Inmueble: Permite listar, crear, editar, alternar estatus y aplicar bajas lógicas a Sedes y Palacios.',
        'can_mutate_structure': 'Acción Crítica Orgánica: Permite administrar, crear, editar y eliminar de forma lógica Secretarías, Direcciones Generales y Áreas Operativas.',
    }

    # 🟢 CALIBRACIÓN ATÓMICA DE LOS 5 ROLES OBLIGATORIOS (Adaptando manager a admin)
    ROLE_MAPPING = {
        'owner': ['has_access_module', 'can_view_analytics', 'can_manage_infrastructure', 'can_mutate_structure'],
        'admin': ['has_access_module', 'can_view_analytics', 'can_manage_infrastructure'],
        'editor': ['has_access_module', 'can_manage_infrastructure'],
        'reviewer': ['has_access_module', 'can_view_analytics'],
        'viewer': ['has_access_module'],
    }

    SIDEBAR_MENU = [
        ["layout-dashboard", "Cuarto de Control", "organigrama:control_panel", 1, "has_access_module"],
        ["map-pin", "Sedes e Inmuebles", "organigrama:sede_list", 2, "can_manage_infrastructure"],
        ["git-fork", "Dependencias y áreas", "organigrama:estructura_list", 3, "has_access_module"],
        ["bar-chart-3", "Consola Analítica", "organigrama:dashboard", 4, "can_view_analytics"],
    ]