# apps/security/utils/forensic_auditor.py
import logging
import traceback
from apps.security.models.audit import SecurityAuditLog

logger = logging.getLogger(__name__)

class ForensicAuditor:
    
    @staticmethod
    def registrar_evento(request, action_type, module_component, action_name, target_scope, app_name=None, level=SecurityAuditLog.Levels.INFO, target_user=None, search_target=None, payload=None):
        """
        🚀 GUARDIÁN FORENSE EVOLUCIONADO: Normaliza la telemetría separando 
        el Verbo (action_type) del Sujeto/Componente (module_component).
        """
        try:
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            ip = x_forwarded_for.split(',')[0].strip() if x_forwarded_for else request.META.get('REMOTE_ADDR', '127.0.0.1')
            user_agent = request.META.get('HTTP_USER_AGENT', 'Desconocido/API')

            if not app_name and request.resolver_match:
                app_name = request.resolver_match.app_name

            # Creación física indexada en Postgres
            return SecurityAuditLog.objects.create(
                app_namespace=app_name.lower() if app_name else "core",
                action_type=action_type,                  # ◄── 'CREATE', 'UPDATE', etc.
                module_component=str(module_component).upper().strip(),  # ◄── 'ALTA_USUARIOS', 'MATRIZ'
                level_status=level,
                action_name=action_name,
                search_target=str(search_target).strip() if search_target else None,
                target_scope=target_scope,
                operator_user=request.user,
                target_user=target_user,
                ip_address=ip,
                user_agent=user_agent,
                payload_json=payload or {}
            )
        except Exception as e:
            logger.error(f"⚠️ [CRITICAL FORENSIC FAIL]: {str(e)}")
            return None