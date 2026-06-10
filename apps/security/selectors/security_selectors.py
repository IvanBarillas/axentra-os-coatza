# apps/security/selectors/security_selectors.py
import uuid
from django.utils import timezone
from django.contrib.auth import get_user_model
from typing import List, Optional

from apps.shared.apps_config import AppIdentifier
from apps.security.models import SecurityAuditLog, UserAppRole, TenantConfig
from apps.security.dtos import RoleReadOnlyDTO, TenantConfigReadOnlyDTO

User = get_user_model()

class SecurityDashboardSelectors:
    """Métricas y buffers forenses en caliente para la Consola Analítica."""

    @classmethod
    def obtener_metricas_firewall(cls) -> dict:
        return {
            "total_apps": len(AppIdentifier.get_choices()),
            "llaves_activas_db": UserAppRole.objects.filter(is_active=True).count(),
            # 🟢 CORRECCIÓN ATÓMICA ORM: Cambiado 'app_roles' por el related_name premium 'roles'
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
    def get_secured_matrix_data(cls, app_module, user_focus_id=None, request_user=None) -> dict:
        """
        🟢 SINCRO INTEGRAL: Despacha el pool completo de llaves JSON configuradas 
        para un aplicativo, hidratando los checkboxes del módulo de ciberseguridad.
        """
        # Extraemos las membresías activas asignadas a este módulo
        roles_qs = UserAppRole.objects.select_related('user', 'app').filter(app=app_module, is_active=True)
        
        usuarios_autorizados = [cls._mapear_rol_a_dto(rol) for rol in roles_qs]
        
        # Cargamos el catálogo de funcionarios para el buscador de incorporación selectiva
        funcionarios_disponibles = User.objects.filter(is_active=True, is_superuser=False).order_by('email')

        return {
            "usuarios_autorizados": usuarios_autorizados,
            "funcionarios_disponibles": funcionarios_disponibles,
            "user_focus_id": user_focus_id
        }


class TenantConfigSelectors:
    """Extractor inmutable del Singleton institucional de marca."""

    @staticmethod
    def obtener_configuracion_activa() -> Optional[TenantConfigReadOnlyDTO]:
        config = TenantConfig.objects.first()
        if not config:
            return None
        # Usamos model_validate de Pydantic de forma segura
        return TenantConfigReadOnlyDTO.model_validate(config)