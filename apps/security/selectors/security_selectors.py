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
    """Métricas y buffers forenses en caliente."""

    @classmethod
    def obtener_metricas_firewall(cls) -> dict:
        return {
            "total_apps": len(AppIdentifier.get_choices()),
            "llaves_activas_db": UserAppRole.objects.filter(is_active=True).count(),
            "cuentas_riesgo": User.objects.filter(is_active=False, app_roles__is_active=True).distinct().count(),
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


class SecuritySelectors:
    """Control analítico perimetral de credenciales."""

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


class TenantConfigSelectors:
    """Extractor inmutable del Singleton institucional de marca."""

    @staticmethod
    def obtener_configuracion_activa() -> Optional[TenantConfigReadOnlyDTO]:
        config = TenantConfig.objects.first()
        if not config:
            return None
        return TenantConfigReadOnlyDTO.model_validate(config)