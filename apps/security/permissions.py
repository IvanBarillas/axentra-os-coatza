# apps/security/permissions.py
from apps.shared.apps_config import AppIdentifier

class SecurityPermissions:
    """
    🏛️ RECON REGISTRY & MANIFIESTO MAESTRO - AXENTRA OS SECURITY
    Gobierna el control perimetral, la inyección de llaves JSON en PostgreSQL,
    los componentes de navegación del Sidebar y las tarjetas del Launcher.
    """
    APP_CODE = AppIdentifier.SECURITY

    # =========================================================================
    # 🛰️ 1. METADATOS MAESTROS PARA EL LANZADOR DINÁMICO (LAUNCHER HUB CORES)
    # =========================================================================
    # Tu vista 'launcher_home_view' leerá este diccionario para dibujar el escritorio
    LAUNCHER_CARD = {
        'title': 'Ciberseguridad & Control Global',
        'description': 'Consola táctica de gobernanza. Gestión atómica de llaves JSON, monitoreo forense de bitácoras e identidad legal de la entidad.',
        'icon': 'shield-check',            # Identificador nativo de Lucide Icons
        'badge_text': 'Core Security',
        'hover_color': 'hover:border-blue-600',
        'text_hover_color': 'group-hover:text-blue-600',
        'url_name': 'security:dashboard',   # Resuelve vía el paquete de URLs unificado
        'is_core': True,
    }

    # =========================================================================
    # 🔑 2. CATÁLOGO ATÓMICO TOTAL DE PRIVILEGIOS MUNICIPALES (JSON FIELD SEEDS)
    # =========================================================================
    # Estas llaves de texto son las que tu seeder 'post_migrate' inyectará en la BD
    PERMISSIONS = {
        # 🔐 Sub-Dominio: Ciberseguridad Central
        'security__has_access': 'Permite el ingreso general a la Consola de Ciberseguridad.',
        'security__can_view_matrix': 'Permite auditar y visualizar las rejillas de privilegios JSON.',
        'security__can_modify_matrix': 'Acción Crítica Máxima: Permite re-grabar y mutar llaves JSON de funcionarios.',
        'security__can_configure_tenant': 'Acción Crítica Core: Permite alterar la identidad visual, logos y RFC legal de la entidad.',
        
        # 👥 Sub-Dominio: Capital Humano (Accounts)
        'accounts__has_access': 'Permite el ingreso perimetral al control operativo de personal.',
        'accounts__can_view_list': 'Permite consultar el padrón institucional de expedientes laborales.',
        'accounts__can_create_user': 'Acción Operativa: Permite dar de alta nuevos funcionarios en las celdas matriciales.',
        'accounts__can_edit_user': 'Acción Operativa: Permite modificar la ficha de identidad laboral del servidor público.',
        'accounts__can_change_password': 'Acción Crítica: Permite forzar el reseteo administrativo de contraseñas.',
        'accounts__can_delete_user': 'Acción Crítica: Permite aplicar bajas del sistema (soft-delete) preservando historial.',
        
        # 🏛️ Sub-Dominio: Estructura Orgánica (Organigrama)
        'organigrama__has_access': 'Permite visualizar el mapa estructural e interactivo del Ayuntamiento.',
        'organigrama__can_view_analytics': 'Permite auditar reportes de densidad laboral y KPIs institucionales.',
        'organigrama__can_manage_infrastructure': 'Acción Crítica Inmueble: Permite administrar, crear y desactivar Sedes y Palacios.',
        'organigrama__can_mutate_structure': 'Acción Crítica Orgánica: Permite dar de alta Secretarías, Direcciones y Oficinas.',
    }

    # =========================================================================
    # 🤝 3. HOMOLOGACIÓN UNIVERSAL DE ROLES DE FÁBRICA (DEFAULT SECURITY)
    # =========================================================================
    # El perfil 'owner' ostenta el total absoluto de llaves para mitigar bloqueos
    ROLE_MAPPING = {
        'owner': [
            'security__has_access', 'security__can_view_matrix', 'security__can_modify_matrix', 'security__can_configure_tenant',
            'accounts__has_access', 'accounts__can_view_list', 'accounts__can_create_user', 'accounts__can_edit_user', 'accounts__can_change_password', 'accounts__can_delete_user',
            'organigrama__has_access', 'organigrama__can_view_analytics', 'organigrama__can_manage_infrastructure', 'organigrama__can_mutate_structure'
        ],
        'admin': [
            'security__has_access', 'security__can_view_matrix', 'security__can_modify_matrix', 'security__can_configure_tenant',
            'accounts__has_access', 'accounts__can_view_list', 'accounts__can_create_user', 'accounts__can_edit_user', 'accounts__can_change_password', 'accounts__can_delete_user',
            'organigrama__has_access', 'organigrama__can_view_analytics', 'organigrama__can_manage_infrastructure', 'organigrama__can_mutate_structure'
        ],
        'editor_rh': [
            'accounts__has_access', 'accounts__can_view_list', 'accounts__can_create_user', 'accounts__can_edit_user',
            'organigrama__has_access'
            # ⛔ Captura expedientes, ve el organigrama básico, pero NO resetea passwords ni altera ciberseguridad.
        ],
        'auditor_interno': [
            'security__has_access', 'security__can_view_matrix',
            'accounts__has_access', 'accounts__can_view_list',
            'organigrama__has_access', 'organigrama__can_view_analytics'
            # 👁️ Perfil de consulta fiscal forense: Inspecciona bitácoras y padrones sin poder inyectar código o mutar filas.
        ]
    }

    # =========================================================================
    # 🎰 4. MATRICES DE BARRAS LATERALES CONTEXTUALES (DYNAMIC SIDEBAR MENUS)
    # =========================================================================
    # Estructura limpia: ["Icono de Lucide", "Nombre Visual", "URL Django Name", Orden, "Permiso Requerido"]
    
    SIDEBAR_SECURITY = [
        ["sliders", "Cabina de Mando", "security:dashboard", 1, "security__has_access"],
        ["grid", "Matriz de Permisos", "security:dynamic_matrix", 2, "security__can_view_matrix"],
        ["settings", "Identidad Global", "security:tenant_config", 3, "security__can_configure_tenant"],
    ]

    SIDEBAR_ACCOUNTS = [
        ["sliders", "Cabina de Mando", "accounts:dashboard", 1, "accounts__has_access"],
        ["users", "Padrón de Empleados", "accounts:funcionario_list_table", 2, "accounts__can_view_list"],
        ["user-plus", "Alta de Servidor", "accounts:funcionario_create", 3, "accounts__can_create_user"],
    ]

    SIDEBAR_ORGANIGRAMA = [
        ["bar-chart-3", "Dashboard del Core", "organigrama:dashboard", 1, "organigrama__can_view_analytics"],
        ["git-fork", "Estructura Orgánica", "organigrama:estructura_list", 2, "organigrama__has_access"],
        ["map-pin", "Sedes e Inmuebles", "organigrama:sede_list", 3, "organigrama__can_manage_infrastructure"],
    ]

    @classmethod
    def obtener_menu_por_modulo(cls, modulo_actual: str) -> list:
        """
        🧠 ROUTING INTERNO SELECTOR:
        Retorna el Sidebar correspondiente al sub-entorno de navegación activo.
        Sustituye de forma atómica condicionales duros en las plantillas HTML.
        """
        mapping = {
            'security': cls.SIDEBAR_SECURITY,
            'accounts': cls.SIDEBAR_ACCOUNTS,
            'organigrama': cls.SIDEBAR_ORGANIGRAMA
        }
        return mapping.get(modulo_actual, [])