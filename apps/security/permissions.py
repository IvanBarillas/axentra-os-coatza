# apps/account/permission.py
from apps.shared.apps_config import AppIdentifier

# =========================================================================
# 🛡️ CLASE 1: DOMINIO DE CIBERSEGURIDAD CENTRAL (SECURITY)
# =========================================================================
class SecurityPermissions:
    APP_CODE = AppIdentifier.SECURITY

    PERMISSIONS = {
        'has_access_module': 'Permite el ingreso general a la Estación de Control de Ciberseguridad.',
        'can_view_analytics': 'Permite auditar el tráfico forense de bitácoras y telemetría en el Dashboard de Seguridad.',
        'can_view_matrix': 'Permite auditar y visualizar las rejillas de privilegios JSON.',
        'can_modify_matrix': 'Acción Crítica Máxima: Permite re-grabar y mutar llaves JSON de funcionarios.',
        'can_configure_tenant': 'Acción Crítica Core: Permite alterar la identidad visual, logos y RFC legal de la entidad.',
    }

    ROLE_MAPPING = {
        'owner': ['has_access_module', 'can_view_analytics', 'can_view_matrix', 'can_modify_matrix', 'can_configure_tenant'],
        'admin': ['has_access_module', 'can_view_analytics', 'can_view_matrix', 'can_modify_matrix'],
        'cyber_auditor': ['has_access_module', 'can_view_analytics', 'can_view_matrix'],
        'editor': ['has_access_module', 'can_view_analytics', 'can_view_matrix'],
        'reviewer': ['has_access_module', 'can_view_matrix'],
        'viewer': ['has_access_module'],
    }

    ROLE_WEIGHTS = {'owner': 100, 'admin': 80, 'cyber_auditor': 70, 'editor': 60, 'reviewer': 40, 'viewer': 20}

    SIDEBAR_MENU = [
        ["layout-dashboard", "Panel Administrativo", "security:control_panel", 1, "has_access_module"],
        ["activity", "Auditoría Forense", "security:global_matrix_forensic", 3, "can_view_matrix"],
        ["bar-chart-3", "Dashboard Analítico", "security:dashboard", 4, "can_view_analytics"],
        ["settings", "Identidad Global", "security:tenant_config", 5, "can_configure_tenant"],
    ]
    
    CAPABILITIES = {
        'flag_alfa': {
            'label': "🛠️ [Security] ¿Es Dependencia Proveedora de Seguridad?",
            'help_text': "EFECTO EN SISTEMA: Al activar esta casilla, el personal adscrito a esta dirección será elegible para aparecer en el combo box de 'Alta de Perfil Técnico' (Comisionar Ingeniero). Úselo exclusivamente para la Dirección de Tecnologías, Innovación o Soporte de Sistemas."
        },
        'flag_beta': {
            'label': "📋 [Security] ¿Es Dependencia Consumidora Estricta (Solo Reportes)?",
            'help_text': "EFECTO EN SISTEMA: Indica que esta área solo puede levantar reportes y visualizar sus propios folios. El sistema aislará sus combo boxes para que al crear un ticket, solo puedan seleccionar las Sedes y Áreas Físicas que pertenezcan formalmente a su propia dirección."
        }
    }


# =========================================================================
# 👥 CLASE 2: DOMINIO DE CAPITAL HUMANO (ACCOUNTS)
# =========================================================================
class AccountsPermissions:
    APP_CODE = AppIdentifier.ACCOUNTS

    PERMISSIONS = {
        'has_access_module': 'Permite el ingreso general a la Estación de Control de Personal.',
        'can_view_analytics': 'Permite auditar reportes de densidad laboral, gráficas de personal y KPIs de nómina.',
        'can_view_list': 'Permite consultar el padrón institucional de expedientes laborales.',
        'can_create_user': 'Acción Operativa: Permite dar de alta nuevos funcionarios.',
        'can_edit_user': 'Acción Operativa: Permite modificar la ficha de identidad laboral.',
        'can_change_password': 'Acción Crítica: Permite forzar el reseteo administrativo de contraseñas.',
        'can_delete_user': 'Acción Crítica: Permite aplicar bajas del sistema.',
    }

    ROLE_MAPPING = {
        'owner': ['has_access_module', 'can_view_analytics', 'can_view_list', 'can_create_user', 'can_edit_user', 'can_change_password', 'can_delete_user'],
        'director_rh': ['has_access_module', 'can_view_analytics', 'can_view_list', 'can_create_user', 'can_edit_user', 'can_change_password'],
        'oficial_rh': ['has_access_module', 'can_view_list', 'can_create_user', 'can_edit_user'],
        'editor': ['has_access_module', 'can_view_list', 'can_create_user', 'can_edit_user'],
        'reviewer': ['has_access_module', 'can_view_list'],
        'viewer': ['has_access_module'],
    }

    ROLE_WEIGHTS = {'owner': 100, 'director_rh': 85, 'oficial_rh': 65, 'editor': 60, 'reviewer': 45, 'viewer': 20}

    SIDEBAR_MENU = [
        ["users", "Listado de Empleados", "accounts:funcionario_list", 1, "can_view_list"],
        ["bar-chart-3", "Dashboard Analítico", "accounts:analytics", 6, "can_view_analytics"],
    ]

    FUNCIONARIO_DETAIL_MENU = [
        {"icon": "fingerprint", "title": "Ficha de Identidad", "url_name": "accounts:funcionario_sub_identidad", "order": 1, "permission": "can_edit_user", "provider": "accounts", "stub": False},
        {"icon": "laptop-2", "title": "Hardware Asignado", "url_name": "accounts:funcionario_sub_hardware", "order": 2, "permission": "can_edit_user", "provider": "assets", "stub": True},
        {"icon": "smartphone", "title": "Línea y Telefonía", "url_name": "accounts:funcionario_sub_telefonia", "order": 3, "permission": "can_edit_user", "provider": "telefonia", "stub": True},
    ]


# =========================================================================
# 🏛️ CLASE 3: DOMINIO DE ESTRUCTURA ORGÁNICA (ORGANIGRAMA)
# =========================================================================
class OrganigramaPermissions:
    APP_CODE = AppIdentifier.ORGANIGRAMA

    PERMISSIONS = {
        'has_access_module': 'Permite el ingreso general a la Estación de Control y consultar el catálogo básico.',
        'can_view_analytics': 'Permite auditar reportes de densidad laboral, gráficas de personal y KPIs institucionales en el Dashboard.',
        'can_manage_infrastructure': 'Acción Crítica Inmueble: Permite listar, crear, editar, alternar estatus y aplicar bajas lógicas a Sedes y Palacios.',
        'can_mutate_structure': 'Acción Crítica Orgánica: Permite administrar, crear, editar y eliminar de forma lógica Secretarías, Direcciones Generales y Áreas Operativas.',
    }

    ROLE_MAPPING = {
        'owner': ['has_access_module', 'can_view_analytics', 'can_manage_infrastructure', 'can_mutate_structure'],
        'admin': ['has_access_module', 'can_view_analytics', 'can_manage_infrastructure'],
        'planeador_urbano': ['has_access_module', 'can_manage_infrastructure'],
        'editor': ['has_access_module', 'can_manage_infrastructure'],
        'reviewer': ['has_access_module', 'can_view_analytics'],
        'viewer': ['has_access_module'],
    }

    ROLE_WEIGHTS = {'owner': 100, 'admin': 80, 'planeador_urbano': 65, 'editor': 60, 'reviewer': 40, 'viewer': 20}

    SIDEBAR_MENU = [
        ["layout-dashboard", "Panel Administrativo", "organigrama:control_panel", 1, "has_access_module"],
        ["map-pin", "Sedes e Inmuebles", "organigrama:sede_list", 2, "can_manage_infrastructure"],
        ["git-fork", "Dependencias y áreas", "organigrama:estructura_list", 3, "has_access_module"],
        ["bar-chart-3", "Dashboard Analítico", "organigrama:dashboard", 4, "can_view_analytics"],
    ]
    
    SEDE_DETAIL_MENU = [
        {
            "icon": "fingerprint", "title": "Ficha de Sede", "url_name": "organigrama:sede_sub_identidad",
            "order": 1, "permission": "can_manage_infrastructure", "provider": "organigrama", "stub": False,
        },
        {
            "icon": "building-2", "title": "Dependencias Presentes", "url_name": "organigrama:sede_sub_dependencias",
            "order": 2, "permission": "can_manage_infrastructure", "provider": "organigrama", "stub": False,
        },
        {
            "icon": "layout-grid", "title": "Áreas Operativas", "url_name": "organigrama:sede_sub_areas",
            "order": 3, "permission": "can_manage_infrastructure", "provider": "organigrama", "stub": False,
        },
        {
            "icon": "users", "title": "Funcionarios en Sede", "url_name": "organigrama:sede_sub_funcionarios",
            "order": 4, "permission": "can_manage_infrastructure", "provider": "accounts", "stub": False,
        },
        {
            "icon": "package", "title": "Activos Instalados", "url_name": "#",
            "order": 5, "permission": "can_manage_infrastructure", "provider": "assets", "stub": True,
        },
        {
            "icon": "ticket", "title": "Tickets de Sede", "url_name": "#",
            "order": 6, "permission": "can_manage_infrastructure", "provider": "helpdesk", "stub": True,
        },   
    ]
    
    DEPENDENCIA_DETAIL_MENU = [
            {
                "icon": "fingerprint",
                "title": "Ficha de Dependencia",
                "url_name": "organigrama:dependencia_sub_identidad",
                "permission": "can_manage_infrastructure",
                "order": 10,
                "provider": "organigrama",
                "stub": False,
            },
            {
                "icon": "layout-grid",
                "title": "Áreas Operativas",
                "url_name": "organigrama:dependencia_sub_areas",
                "permission": "can_manage_infrastructure",
                "order": 20,
                "provider": "organigrama",
                "stub": False,
            },
            {
                "icon": "map-pin",
                "title": "Sedes donde Opera",
                "url_name": "organigrama:dependencia_sub_sedes",
                "permission": "can_manage_infrastructure",
                "order": 30,
                "provider": "organigrama",
                "stub": False,
            },
            {
                "icon": "users",
                "title": "Funcionarios Adscritos",
                "url_name": "organigrama:dependencia_sub_funcionarios",
                "permission": "can_manage_infrastructure",
                "order": 40,
                "provider": "organigrama",
                "stub": False,
            },
            {
                "icon": "package",
                "title": "Activos Asignados",
                "url_name": "#",
                "permission": "can_manage_infrastructure",
                "order": 80,
                "provider": "assets",
                "stub": True,
            },
            {
                "icon": "ticket",
                "title": "Tickets de Dependencia",
                "url_name": "#",
                "permission": "can_manage_infrastructure",
                "order": 90,
                "provider": "helpdesk",
                "stub": True,
            },
        ]
    
    AREA_DETAIL_MENU = [
        {
            "icon": "fingerprint",
            "title": "Ficha de Área",
            "url_name": "organigrama:area_sub_identidad",
            "permission": "can_manage_infrastructure",
            "order": 10,
            "provider": "organigrama",
            "stub": False,
        },
        {
            "icon": "users",
            "title": "Funcionarios Adscritos",
            "url_name": "organigrama:area_sub_funcionarios",
            "permission": "can_manage_infrastructure",
            "order": 20,
            "provider": "organigrama",
            "stub": False,
        },
        {
            "icon": "package",
            "title": "Activos del Área",
            "url_name": "#",
            "permission": "can_manage_infrastructure",
            "order": 80,
            "provider": "assets",
            "stub": True,
        },
        {
            "icon": "ticket",
            "title": "Tickets del Área",
            "url_name": "#",
            "permission": "can_manage_infrastructure",
            "order": 90,
            "provider": "helpdesk",
            "stub": True,
        },
    ]
    
    AREA_DETAIL_MENU = [
        {
            "icon": "fingerprint",
            "title": "Ficha de Área",
            "url_name": "organigrama:area_sub_identidad",
            "permission": "can_manage_infrastructure",
            "order": 10,
            "provider": "organigrama",
            "stub": False,
        },
        {
            "icon": "users",
            "title": "Funcionarios Adscritos",
            "url_name": "organigrama:area_sub_funcionarios",
            "permission": "can_manage_infrastructure",
            "order": 20,
            "provider": "organigrama",
            "stub": False,
        },
        {
            "icon": "package",
            "title": "Activos del Área",
            "url_name": "#",
            "permission": "can_manage_infrastructure",
            "order": 80,
            "provider": "assets",
            "stub": True,
        },
        {
            "icon": "ticket",
            "title": "Tickets del Área",
            "url_name": "#",
            "permission": "can_manage_infrastructure",
            "order": 90,
            "provider": "helpdesk",
            "stub": True,
        },
    ]
    
