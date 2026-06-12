# apps/security/services/security_services.py
import logging
import sys
import traceback
from typing import List, Dict, Any, Optional, Tuple
from django.db import transaction
from django.contrib.auth import get_user_model
from apps.security.models import UserAppRole, AppModule
from apps.security.models.audit import SecurityAuditLog
from apps.security.utils.forensic_auditor import ForensicAuditor
from apps.security.utils.hierarchy_enforcer import HierarchyEnforcer
from apps.security.services.permission_loader import get_app_permissions

User = get_user_model()
logger = logging.getLogger(__name__)


class PermissionService:
    """Lógica transaccional centralizada para la inyección, mutación y auditoría de privilegios."""

    @staticmethod
    def authorize_new_user_entry(request, app_module: AppModule, user_id: str, rol_a_inyectar: str = 'viewer') -> bool:
        """
        Incorpora un funcionario al padrón de una aplicación bajo la filosofía Zero Trust.
        🛰️ AUDITORÍA NORMALIZADA: Registra el evento bajo el tipo CREATE en el componente MATRIZ_PERMISOS.
        """
        try:
            target_user = User.objects.get(id=user_id)
            if target_user.is_manager or target_user.is_superuser:
                return False
                
            rol_limpio = str(rol_a_inyectar).lower().strip()

            with transaction.atomic():
                rol_existente = UserAppRole.objects.filter(user=target_user, app=app_module).first()
                if rol_existente and rol_existente.is_active:
                    return False

                if rol_limpio == "owner":
                    config_app = get_app_permissions(app_module.slug)
                    llaves_finales = list(config_app.get('permissions', {}).keys())
                else:
                    llaves_finales = ['has_access_module']

                UserAppRole.objects.update_or_create(
                    user=target_user,
                    app=app_module,
                    defaults={
                        'role': rol_limpio,
                        'permissions_list': llaves_finales,
                        'is_active': True
                    }
                )

            # 🪐 BITÁCORA FORENSE ATÓMICA DE INYECCIÓN
            ForensicAuditor.registrar_evento(
                request=request,
                action_type=SecurityAuditLog.ActionTypes.CREATE,
                module_component="MATRIZ_PERMISOS",
                action_name="INYECCION_PERIMETRAL_FUNCIONARIO",
                target_scope=f"Siembra inicial del funcionario {target_user.email} en {app_module.name} con rol [{rol_limpio.upper()}].",
                level=SecurityAuditLog.Levels.SUCCESS,
                target_user=target_user,
                search_target=target_user.id,
                payload={'initial_role': rol_limpio, 'app_slug': app_module.slug}
            )

            logger.info(f"🟢 CIBERSEGURIDAD: Funcionario {target_user.email} sembrado en [{app_module.slug.upper()}].")
            return True
        except Exception as e:
            logger.error(f"❌ FALLO (authorize_new_user_entry): {str(e)}")
            return False

    @staticmethod
    def save_matrix_permissions(request, target_user: Any, app_module: AppModule, nuevo_rol: str, llaves_encendidas: List[str], is_manager_bypass: bool = False) -> Tuple[bool, str]:
        """
        🚀 REFACTOR MASTER CENTRALIZADO BLINDADO: Sanea, valida jerarquía, calcula deltas y guarda.
        🛡️ ENFOQUE ZERO-TRUST ESTRICTO: Solo 'owner' hereda todos los permisos. ADMIN nace en ceros.
        🛰️ COMPILACIÓN FORENSE AUTÓNOMA: El servicio calcula el delta de forma nativa para blindar el payload_json.
        """
        try:
            rol_limpio = str(nuevo_rol).lower().strip()
            
            # 🪐 SNAPSHOT ANTES: Capturamos el estado actual real de la BD antes de alterarlo
            rol_actual_obj = UserAppRole.objects.filter(user=target_user, app=app_module).first()
            rol_anterior = rol_actual_obj.role if rol_actual_obj else 'ninguno'
            permisos_anteriores = list(rol_actual_obj.permissions_list or []) if rol_actual_obj else []

            # 🛡️ VALIDACIÓN DE ESCALAFÓN DE JERARQUÍA
            config_app = get_app_permissions(app_module.slug)
            weights_map = config_app.get('weights', {})
            permissions_pool = config_app.get('permissions', {})

            tiene_autoridad = HierarchyEnforcer.validar_autoridad_operador(
                request=request, target_user=target_user, app_module=app_module,
                nuevo_rol_slug=rol_limpio, weights_map=weights_map
            )
            if not tiene_autoridad:
                return False, "🚫 Violación de Escalafón: Tus privilegios locales no tienen el peso jerárquico requerido."

            # Saneamiento y filtrado de llaves inyectadas desde el POST contra el manifiesto
            lista_final_json = list(set([str(llave).strip() for llave in llaves_encendidas if llave]))
            if permissions_pool:
                lista_final_json = [l for l in lista_final_json if l in permissions_pool.keys()]

            # Regla de control Zero-Trust: Solo Owner clona la piscina completa
            if rol_limpio == 'owner' and permissions_pool:
                lista_final_json = list(permissions_pool.keys())
            
            # El token mínimo de entrada se amarra por diseño defensivo
            if 'has_access_module' not in lista_final_json:
                lista_final_json.append('has_access_module')

            # 🪐 ANÁLISIS FORENSE DELTA: Calculamos tokens ganados y perdidos de manera autónoma
            payload_delta = {
                'antes': {'role': rol_anterior, 'permissions': permisos_anteriores},
                'despues': {'role': rol_limpio, 'permissions': lista_final_json},
                'delta_cambios': {
                    'tokens_ganados': [p for p in lista_final_json if p not in permisos_anteriores],
                    'tokens_perdidos': [p for p in permisos_anteriores if p not in lista_final_json],
                    'rol_mutado': rol_anterior != rol_limpio
                }
            }

            # Persistencia física atómica en PostgreSQL
            with transaction.atomic():
                UserAppRole.objects.update_or_create(
                    user=target_user, app=app_module,
                    defaults={'role': rol_limpio, 'permissions_list': lista_final_json, 'is_active': True}
                )

            # 🪐 INYECTOR FORENSE CENTRALIZADO CON EL PAYLOAD COMPLETO
            action_code = "MUTACION_MATRIZ_BYPASS" if is_manager_bypass else "MUTACION_MATRIZ_ESTANDAR"
            level_status = SecurityAuditLog.Levels.SUCCESS if is_manager_bypass else SecurityAuditLog.Levels.INFO
            
            ForensicAuditor.registrar_evento(
                request=request,
                action_type=SecurityAuditLog.ActionTypes.ASSIGN,     # 🔤 Verbo Normalizado
                module_component="MATRIZ_PERMISOS",                  # 🗺️ Componente Local
                action_name=action_code,
                target_scope=f"Reconfiguración granular sobre la grilla de {target_user.email} en el módulo de {app_module.name}",
                level=level_status,
                target_user=target_user,
                search_target=target_user.id,
                payload=payload_delta                                # ◄── Guardado impecable en Postgres
            )

            msg = f"🔒 [NIVEL MAESTRO]: Reconfiguración por decreto completada." if is_manager_bypass else f"🔒 Matriz actualizada con éxito."
            return True, msg

        except Exception as e:
            logger.error(f"❌ FALLO TRANSACCIONAL (save_matrix_permissions): {str(e)}\n{traceback.format_exc()}")
            return False, f"Fallo interno de consistencia: {str(e)}"