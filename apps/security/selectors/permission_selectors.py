# apps/security/selectors/permission_selectors.py
import importlib
import logging
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from apps.security.models import AppModule, UserAppRole

User = get_user_model()
logger = logging.getLogger(__name__)

class PermissionSelectors:

    @staticmethod
    def get_app_metadata_or_404(app_slug: str) -> AppModule:
        return get_object_or_404(AppModule, slug=app_slug, is_active=True)

    @staticmethod
    def get_app_config_modules(app_slug: str):
        """Introspección dinámica: Lee los diccionarios PERMISSIONS y ROLE_MAPPING aislados."""
        fallback_permissions = {'has_access_module': 'Permite el acceso general al módulo.'}
        fallback_mapping = {'viewer': ['has_access_module']}

        try:
            modulo_permisos = importlib.import_module(f"apps.{app_slug}.permissions")
            clase_permisos = None
            for attr_name in dir(modulo_permisos):
                if attr_name.endswith("Permissions"):
                    clase_permisos = getattr(modulo_permisos, attr_name)
                    break
            
            if clase_permisos:
                permissions = getattr(clase_permisos, "PERMISSIONS", fallback_permissions)
                role_mapping = getattr(clase_permisos, "ROLE_MAPPING", fallback_mapping)
            else:
                permissions = fallback_permissions
                role_mapping = fallback_mapping
        except ModuleNotFoundError:
            permissions = fallback_permissions
            role_mapping = fallback_mapping
        except Exception as e:
            logger.error(f"Error crítico de introspección en la app '{app_slug}': {str(e)}")
            permissions = fallback_permissions
            role_mapping = fallback_mapping

        return permissions, role_mapping

    @staticmethod
    def get_secured_matrix_data(app_module: AppModule, user_focus_id=None, request_user=None) -> dict:
        """Gobernanza de Ciberseguridad: cruza el manifiesto local contra el JSONField de la BD."""
        permissions_dict, role_mapping = PermissionSelectors.get_app_config_modules(app_module.slug)
        llaves_disponibles = list(permissions_dict.keys())
        operador_is_manager = getattr(request_user, 'is_manager', False) if request_user else False

        roles_en_app_qs = UserAppRole.objects.filter(
            app=app_module, is_active=True
        ).exclude(user__is_manager=True).select_related('user')
        
        usuarios_con_acceso_ids = [r.user_id for r in roles_en_app_qs]

        personal_data = []
        for r_obj in roles_en_app_qs:
            if not r_obj.permissions_list or "has_access_module" not in r_obj.permissions_list:
                continue

            usuario = r_obj.user
            rol_str = r_obj.role
            llaves_por_defecto = role_mapping.get(rol_str, ["has_access_module"])
            llaves_reales_db = r_obj.permissions_list or []

            permisos_mapeados = []
            for llave in llaves_disponibles:
                permisos_mapeados.append({
                    'llave': llave,
                    'descripcion': permissions_dict.get(llave, ''),
                    'concedido_by_role': llave in llaves_por_defecto,
                    'concedido_total': llave in llaves_reales_db
                })

            personal_data.append({
                'usuario': usuario,
                'rol_actual': rol_str,
                'permisos': permisos_mapeados,
                'es_el_seleccionado': str(usuario.id) == str(user_focus_id)
            })

        usuarios_potenciales = User.objects.filter(
            is_active=True, is_manager=False, is_superuser=False
        ).exclude(id__in=usuarios_con_acceso_ids).order_by('first_name') if operador_is_manager else User.objects.none()

        return {
            'llaves_cabecera': llaves_disponibles,
            'personal_list': personal_data,
            'usuarios_potenciales': usuarios_potenciales,
            'roles_choices': [(rol, rol.upper()) for rol in role_mapping.keys()],
            'role_mapping_json': role_mapping,
            'mostrar_buscador': operador_is_manager  
        }