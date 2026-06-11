# apps/security/selectors/permission_selectors.py
import importlib
import logging
import traceback  # ◄── Bloque Forense de Extracción de Errores Críticos
from typing import List, Optional
import uuid
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from apps.security.dtos.security_dtos import RoleReadOnlyDTO
from apps.security.models import AppModule, UserAppRole
from apps.security.services.permission_loader import get_app_permissions
from django.db import models as db_models

from apps.shared.apps_config import AppIdentifier

User = get_user_model()
logger = logging.getLogger(__name__)

class PermissionSelectors:
    """Control analítico perimetral de credenciales y gobernanza de la Matriz JSON."""
    
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
            logger.error(f"❌ Error crítico de introspección en la app '{app_slug}': {str(e)}\n{traceback.format_exc()}")
            permissions = fallback_permissions
            role_mapping = fallback_mapping

        return permissions, role_mapping

    @staticmethod
    def _mapear_rol_a_dto(obj: UserAppRole) -> RoleReadOnlyDTO:
        return RoleReadOnlyDTO(
            id=obj.id, user_id=obj.user.id, user_email=obj.user.email,
            app_id=obj.app.id, app_name=obj.app.name, app_slug=obj.app.slug,
            role=obj.role, role_display=obj.get_role_display(),
            permissions_list=obj.permissions_list, is_active=obj.is_active
        )

    @classmethod
    def obtener_roles_por_usuario(cls, user_id: uuid.UUID) -> List[RoleReadOnlyDTO]:
        try:
            queryset = UserAppRole.objects.select_related('user', 'app').filter(user_id=user_id, is_active=True)
            return [cls._mapear_rol_a_dto(rol) for rol in queryset]
        except Exception as e:
            logger.error(f"❌ Error en obtener_roles_por_usuario: {str(e)}\n{traceback.format_exc()}")
            return []

    @classmethod
    def get_secured_matrix_data(cls, app_module: AppModule, user_focus_id: Optional[str] = None, request_user: Optional[User] = None, is_manager_global: bool = False) -> dict:
        """
        🚀 REFACTOR MASTER CORE: Extrae, cruza y computa el escalafón jerárquico 
        y el árbol granular de llaves JSONField para la Consola Maestra de Privilegios.
        """
        try:
            roles_activos = UserAppRole.objects.filter(app=app_module).select_related('user').order_by('user__first_name')
            
            config_app = get_app_permissions(app_module.slug)
            catalogo_permisos = config_app.get('permissions', {})
            role_mapping = config_app.get('roles', {})
            weights_map = config_app.get('weights', {})
            
            personal_list = []
            usuario_enfocado_data = None
            
            for r in roles_activos:
                es_el_seleccionado = str(r.user.id) == str(user_focus_id)
                personal_list.append({
                    'usuario': r.user,
                    'rol_actual': r.role.upper(),
                    'es_el_seleccionado': es_el_seleccionado,
                    'is_suspended': not r.is_active
                })
                
                if es_el_seleccionado:
                    permisos_raw = r.permissions_list or []
                    permisos_usuario_lista = [p for p in permisos_raw if p in catalogo_permisos]
                    
                    permisos_permitidos_por_rol = role_mapping.get(r.role, [])
                    payload_llaves = []
                    for code, desc in catalogo_permisos.items():
                        if code not in permisos_permitidos_por_rol:
                            continue
                        obligatorio_by_role = (code == 'has_access_module') or (r.role == 'owner')
                        payload_llaves.append({
                            'llave': code,
                            'descripcion': desc,
                            'concedido_total': (code in permisos_usuario_lista) or obligatorio_by_role,
                            'obligatorio_by_role': obligatorio_by_role
                        })
                    
                    bloqueo_visual = False
                    motivo_bloqueo = "none"

                    if not is_manager_global and request_user:
                        rol_operador_obj = UserAppRole.objects.filter(user=request_user, app=app_module, is_active=True).first()
                        rol_operador_str = rol_operador_obj.role if rol_operador_obj else 'viewer'
                        
                        peso_operador = weights_map.get(str(rol_operador_str).lower().strip(), 0)
                        peso_destino = weights_map.get(str(r.role).lower().strip(), 0)

                        if str(r.user.id) == str(request_user.id):
                            bloqueo_visual = True
                            motivo_bloqueo = "auto_lock"
                        elif r.role == 'owner':
                            bloqueo_visual = True
                            motivo_bloqueo = "owner_lock"
                        elif peso_destino >= peso_operador:
                            bloqueo_visual = True
                            motivo_bloqueo = "weight_lock"

                    usuario_enfocado_data = {
                        'usuario': r.user,
                        'rol_actual': r.role,
                        'permisos': payload_llaves,
                        'bloqueo_visual': bloqueo_visual or (not r.is_active),
                        'motivo_bloqueo': "suspended_lock" if not r.is_active else motivo_bloqueo
                    }

            if is_manager_global:
                usuarios_ya_asignados = UserAppRole.objects.filter(app=app_module).values_list('user_id', flat=True)
                usuarios_potenciales = User.objects.filter(is_active=True, is_superuser=False, is_manager=False).exclude(id__in=usuarios_ya_asignados).order_by('first_name')
                mostrar_buscador = True
            else:
                usuarios_potenciales = None
                mostrar_buscador = False

            roles_grilla = [(rol_key, rol_key.upper()) for rol_key in role_mapping.keys() if rol_key != 'owner' or is_manager_global]

            return {
                'personal_list': personal_list,
                'usuario_enfocado': usuario_enfocado_data,
                'roles_choices': roles_grilla,
                'role_mapping': role_mapping,
                'mostrar_buscador': mostrar_buscador,
                'usuarios_potenciales': usuarios_potenciales
            }
        except Exception as e:
            logger.error(f"❌ Error crítico en get_secured_matrix_data: {str(e)}\n{traceback.format_exc()}")
            return {'personal_list': [], 'usuario_enfocado': None, 'roles_choices': [], 'role_mapping': {}, 'mostrar_buscador': False, 'usuarios_potenciales': None}
        
    @classmethod
    def listar_matriz_forense_global(cls, filtros) -> list:
        """🪙 RAM FORENSIC ENGINE: Extrae la plantilla operativa masiva."""
        try:
            usuarios_queryset = (
                User.objects.filter(is_superuser=False)
                .select_related(
                    'axentra_profile', 
                    'axentra_profile__area', 
                    'axentra_profile__area__dependencia', 
                    'axentra_profile__area__sede_fisica'
                )
                .order_by('-date_joined')
            )
            
            if filtros.get('q'):
                q_filter = filtros.get('q')
                usuarios_queryset = usuarios_queryset.filter(
                    db_models.Q(email__icontains=q_filter) | 
                    db_models.Q(first_name__icontains=q_filter) | 
                    db_models.Q(last_name__icontains=q_filter)
                )
                
            sede_id = filtros.get('sede_id')
            dependencia_id = filtros.get('dependencia_id')
            area_id = filtros.get('area_id')
            
            if sede_id:
                usuarios_queryset = usuarios_queryset.filter(axentra_profile__area__sede_fisica_id=sede_id)
            if dependencia_id:
                usuarios_queryset = usuarios_queryset.filter(axentra_profile__area__dependencia_id=dependencia_id)
            if area_id:
                usuarios_queryset = usuarios_queryset.filter(axentra_profile__area__id=area_id)

            todos_los_roles = UserAppRole.objects.filter(is_active=True).select_related('app')
            matriz_seguridad_ram = {}
            for rol in todos_los_roles:
                if rol.user_id not in matriz_seguridad_ram:
                    matriz_seguridad_ram[rol.user_id] = {}
                matriz_seguridad_ram[rol.user_id][rol.app.slug] = {
                    'role': rol.role,
                    'permisos': rol.permissions_list or []
                }

            plantilla_final_funcionarios = []
            particulas_ignorar = {'de', 'la', 'el', 'y', 'los', 'las', 'en', 'para'}

            for user in usuarios_queryset:
                roles_usuario = matriz_seguridad_ram.get(user.id, {})
                accesos_modulos = {}
                owners_modulos = {}  
                
                for slug, _ in AppIdentifier.get_choices():
                    if getattr(user, 'is_manager', False):
                        accesos_modulos[slug] = True
                        owners_modulos[slug] = False
                    else:
                        datos_rol = roles_usuario.get(slug, {})
                        permisos_list = datos_rol.get('permisos', [])
                        rol_str = datos_rol.get('role', '')
                        
                        accesos_modulos[slug] = (rol_str == "owner") or ("has_access_module" in permisos_list)
                        owners_modulos[slug] = (rol_str == "owner")
                
                profile = getattr(user, 'axentra_profile', None)
                area = getattr(profile, 'area', None) if profile else None
                dependencia = getattr(area, 'dependencia', None) if area else None
                
                if dependencia and dependencia.slug:
                    palabras = dependencia.slug.split('-')
                    letras_clave = [p[0].upper() for p in palabras if p and p not in particulas_ignorar]
                    dep_siglas = "".join(letras_clave) if len(letras_clave) > 1 else dependencia.slug[:4].upper()
                else:
                    dep_siglas = 'MUNI'

                plantilla_final_funcionarios.append({
                    'full_name': user.get_full_name() or user.username,
                    'email': user.email,
                    'profile_id': profile.id if profile else None,
                    'is_email_verified': getattr(user, 'is_email_verified', False),
                    'is_manager': getattr(user, 'is_manager', False),
                    'sede_nombre': area.sede_fisica.nombre if area and getattr(area, 'sede_fisica', None) else '',
                    'dependencia_siglas': dep_siglas,
                    'area_nombre': area.nombre if area else '',
                    'accesos_modulos': accesos_modulos,
                    'owners_modulos': owners_modulos
                })

            return plantilla_final_funcionarios
        except Exception as e:
            logger.error(f"❌ Error masivo en listar_matriz_forense_global: {str(e)}\n{traceback.format_exc()}")
            return []