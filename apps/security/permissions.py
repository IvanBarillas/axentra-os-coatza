# apps/security/permissions.py
from apps.shared.apps_config import AppIdentifier

class SecurityPermissions:
    """
    MANIFIESTO CORE DE PRIVILEGIOS Y COMPONENTES DE NAVEGACIÓN - SECURITY
    Gobierna el control perimetral y el lanzamiento dinámico de Ciberseguridad.
    """
    APP_CODE = AppIdentifier.SECURITY

    # 🚀 METADATA CENTRALIZADA PARA EL LANZADOR DINÁMICO (CALIBRADO CORE OS)
    LAUNCHER_CARD = {
        'title': 'Ciberseguridad Central',
        'description': 'Consola central de gobernanza. Gestión de perfiles institucionales, auditoría perimetral e hidratación de matrices de privilegios.',
        'icon': 'shield-check', # Nombre del icono de Lucide
        'badge_text': 'Core Security',
        'hover_color': 'hover:border-slate-400',
        'text_hover_color': 'group-hover:text-slate-700',
        'url_name': 'security:dashboard', # Entrada directa que mapearemos en sus urls
        'is_core': True,
    }

    # 🔑 Catálogo atómico y jerárquico por Dominios de Responsabilidad
    PERMISSIONS = {
        'has_access_module': 'Permite el ingreso general a la suite de ciberseguridad.',
        'can_view_profiles': 'Permite consultar la lista general de usuarios y matrices de privilegios.',
        'can_modify_matrix': 'Acción Crítica: Permite alterar los permisos hidratados en el JSON de cualquier usuario.',
        'can_view_audit_logs': 'Acción Operativa: Permite auditar la bitácora e historial forense de accesos.',
    }

    # 🤝 Homologación de perfiles locales por defecto
    ROLE_MAPPING = {
        'owner': ['has_access_module', 'can_view_profiles', 'can_modify_matrix', 'can_view_audit_logs'],
        'admin': ['has_access_module', 'can_view_profiles', 'can_modify_matrix', 'can_view_audit_logs'],
        'viewer': ['has_access_module', 'can_view_profiles']
    }

    # 👥 Menú contextual exclusivo de la barra lateral al estar dentro de Seguridad
    # Estructura: ["Icono de Lucide", "Nombre Visual", "Ruta de Django (name)", Orden, "Permiso Requerido"]
    SIDEBAR_MENU = [
        ["sliders", "Cabina de Mando", "security:dashboard", 1, "has_access_module"],
        ["users", "Control de Accesos", "security:profiles_list", 2, "can_view_profiles"],
        ["activity", "Logs de Auditoría", "security:audit_logs", 3, "can_view_audit_logs"],
    ]