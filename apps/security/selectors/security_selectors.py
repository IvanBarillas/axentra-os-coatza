# apps/security/selectors/security_selectors.py
import importlib
import uuid
import logging
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from typing import List, Optional

from apps.security.models.organigrama import AppDependencyCapability, Dependencia
from apps.shared.apps_config import AppIdentifier
from apps.security.models import SecurityAuditLog, UserAppRole, TenantConfig, AppModule
from apps.security.dtos import RoleReadOnlyDTO, TenantConfigReadOnlyDTO
from apps.security.services.permission_loader import get_app_permissions

User = get_user_model()
logger = logging.getLogger(__name__)

ROLE_WEIGHTS = {'owner': 100, 'admin': 80, 'editor': 60, 'reviewer': 40, 'viewer': 20}


class SecurityDashboardSelectors:
    """Métricas y buffers forenses en caliente para la Consola Analítica."""

    @classmethod
    def obtener_metricas_firewall(cls) -> dict:
        return {
            "total_apps": len(AppIdentifier.get_choices()),
            "llaves_activas_db": UserAppRole.objects.filter(is_active=True).count(),
            "cuentas_riesgo": User.objects.filter(is_active=False, roles__is_active=True).distinct().count(),
        }

    @classmethod
    def obtener_buffer_auditoria(cls, limite: int = 50) -> list:
        """Filtra trazas generadas estrictamente el día de hoy para proteger la latencia RAM."""
        hoy = timezone.now().date()
        logs_queryset = (
            SecurityAuditLog.objects.filter(created_at__date=hoy)
            .select_related('operator_user')
            .order_by('-created_at')[:limite]
        )
        
        return [{
            "timestamp": log.created_at,
            "tipo": log.level_status,
            "operador": log.operator_user.email,
            "accion": log.action_name,
            "destino": log.target_scope
        } for log in logs_queryset]


class PermissionSelectors:
    """Control analítico perimetral de credenciales y gobernanza de la Matriz JSON."""

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
        queryset = UserAppRole.objects.select_related('user', 'app').filter(user_id=user_id, is_active=True)
        return [cls._mapear_rol_a_dto(rol) for rol in queryset]

    @classmethod
    def get_secured_matrix_data(cls, app_module: AppModule, user_focus_id: Optional[str] = None, request_user: Optional[User] = None, is_manager_global: bool = False) -> dict:
        """
        🚀 REFACTOR MASTER CORE: Extrae, cruza y computa el escalafón jerárquico 
        y el árbol granular de llaves JSONField para la Consola Maestra de Privilegios.
        """
        # 1. Traer el padrón total (incluyendo suspendidos) para la lista física izquierda
        roles_activos = UserAppRole.objects.filter(app=app_module).select_related('user').order_by('user__first_name')
        
        config_app = get_app_permissions(app_module.slug)
        catalogo_permisos = config_app.get('permissions', {})
        role_mapping = config_app.get('roles', {})
        
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
            
            # 2. Si es el funcionario bajo inspección activa, calculamos sus llaves granulares
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
                
                # 🛡️ Aduana de Ciberseguridad: Cálculo semántico de bloqueos visuales
                bloqueo_visual = False
                motivo_bloqueo = "none"

                if not is_manager_global and request_user:
                    rol_operador_obj = UserAppRole.objects.filter(user=request_user, app=app_module, is_active=True).first()
                    rol_operador_str = rol_operador_obj.role if rol_operador_obj else 'viewer'
                    
                    peso_operador = ROLE_WEIGHTS.get(rol_operador_str, 0)
                    peso_destino = ROLE_WEIGHTS.get(r.role, 0)

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

        # 3. Filtrado quirúrgico del padrón de usuarios disponibles para inyectar (excluye asignados)
        if is_manager_global:
            usuarios_ya_asignados = UserAppRole.objects.filter(app=app_module).values_list('user_id', flat=True)
            usuarios_potenciales = User.objects.filter(is_active=True, is_superuser=False, is_manager=False).exclude(id__in=usuarios_ya_asignados).order_by('first_name')
            mostrar_buscador = True
        else:
            usuarios_potenciales = None
            mostrar_buscador = False

        roles_grilla = [(val, etiqueta) for val, etiqueta in UserAppRole.Roles.choices if val != 'owner' or is_manager_global]

        return {
            'personal_list': personal_list,
            'usuario_enfocado': usuario_enfocado_data,
            'roles_choices': roles_grilla,
            'role_mapping': role_mapping,
            'mostrar_buscador': mostrar_buscador,
            'usuarios_potenciales': usuarios_potenciales
        }


class TenantConfigSelectors:
    """Extractor inmutable del Singleton institucional de marca."""

    @staticmethod
    def obtener_configuracion_activa() -> Optional[TenantConfigReadOnlyDTO]:
        config = TenantConfig.objects.first()
        if not config:
            return None
        return TenantConfigReadOnlyDTO.model_validate(config)
    
    
class CapabilitySelectors:
    """Selector encargado de compilar el mapeo relacional de dependencias y apps con semántica dinámica."""

    @staticmethod
    def obtener_labels_manifiesto(app_slug: str) -> dict:
        """
        🔍 INTROSPECCIÓN DINÁMICA: Busca la clase de permisos de la app en ejecución
        y extrae el diccionario CAPABILITIES personalizado.
        """
        labels_config = {
            'flag_alfa': {'label': "Capacidad Primaria (Alfa)", 'help_text': "Activar rol primario institucional."},
            'flag_beta': {'label': "Capacidad Secundaria (Beta)", 'help_text': "Activar rol secundario de soporte."}
        }
        try:
            # Importa el archivo centralizado de manifiestos
            modulo_permissions = importlib.import_module("apps.security.permissions")
            for attr_name in dir(modulo_permissions):
                if attr_name.endswith("Permissions") and attr_name.lower().startswith(app_slug.replace('_', '')):
                    clase_permisos = getattr(modulo_permissions, attr_name)
                    if hasattr(clase_permisos, 'CAPABILITIES'):
                        labels_config = clase_permisos.CAPABILITIES
                    break
        except Exception:
            pass
        return labels_config

    @classmethod
    def obtener_matriz_capacidades_contexto(cls, app_activa: AppModule) -> dict:
        """Compila los nodos reales vinculados y las dependencias remanentes disponibles."""
        capacidades_reales = AppDependencyCapability.objects.filter(app=app_activa).select_related('dependencia')
        deps_ya_vinculadas = capacidades_reales.values_list('dependencia_id', flat=True)
        
        dependencias_disponibles = (
            Dependencia.objects.filter(is_active=True, is_deleted=False)
            .exclude(id__in=deps_ya_vinculadas)
            .order_by('nombre')
        )
        
        return {
            'matriz': capacidades_reales,
            'dependencias_disponibles': dependencias_disponibles,
            'labels': cls.obtener_labels_manifiesto(app_activa.slug)
        }