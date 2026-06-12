# apps/security/utils/forensic_auditor.py
import logging
import traceback
from apps.security.models.audit import SecurityAuditLog

logger = logging.getLogger(__name__)

class ForensicAuditor:
    
    @staticmethod
    def registrar_evento(request, action_name, target_scope, app_name=None, level=SecurityAuditLog.Levels.INFO, target_user=None, search_target=None, payload=None):
        """
        🚀 GUARDIÁN FORENSE UNIVERSAL: Extrae automáticamente IP, Navegador y Metadatos.
        Indexa componentes independientes para búsquedas quirúrgicas ultra-veloces.
        """
        try:
            # 1. Extracción automatizada de la IP real (Soporta Proxies/Nginx en Producción)
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0].strip()
            else:
                ip = request.META.get('REMOTE_ADDR', '127.0.0.1')

            # 2. Extracción de la firma del Dispositivo / Navegador
            user_agent = request.META.get('HTTP_USER_AGENT', 'Desconocido/API')

            # 3. Detección automática de la App de Origen mediante Namespace de Rutas
            if not app_name and request.resolver_match:
                app_name = request.resolver_match.app_name

            # 4. Sanitización estricta del criterio de búsqueda dinámica
            criterio_busqueda = str(search_target).strip() if search_target else None

            # 5. Persistencia física indexada en Postgres
            log_instancia = SecurityAuditLog.objects.create(
                app_namespace=app_name.lower() if app_name else "core",
                operator_user=request.user,
                target_user=target_user,
                level_status=level,
                action_name=action_name,
                search_target=criterio_busqueda,  # ◄── Aquí caerá tu Serie, Clave Catastral, etc.
                target_scope=target_scope,
                ip_address=ip,
                user_agent=user_agent,
                payload_json=payload or {}
            )
            
            logger.info(f"🛰️ [AUDIT EXECUTED]: {log_instancia.action_name} | IP: {log_instancia.ip_address} | App: {log_instancia.app_namespace}")
            return log_instancia

        except Exception as e:
            logger.error(f"⚠️ [CRITICAL FORENSIC FAIL]: Fallo al escribir en el Buffer Circular: {str(e)}\n{traceback.format_exc()}")
            return None