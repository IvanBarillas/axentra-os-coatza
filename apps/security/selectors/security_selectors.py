# apps/security/selectors/security_selectors.py
import importlib
import uuid
import logging
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from typing import List, Optional
from django.db.models import Q

from apps.security.models.organigrama import AppDependencyCapability, Dependencia
from apps.shared.apps_config import AppIdentifier
from apps.security.models import SecurityAuditLog, UserAppRole, TenantConfig, AppModule
from apps.security.dtos import RoleReadOnlyDTO, TenantConfigReadOnlyDTO
from apps.security.services.permission_loader import get_app_permissions

User = get_user_model()
logger = logging.getLogger(__name__)

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
    def obtener_buffer_auditoria(cls, limite: int = 50, filtros: dict = None) -> list:
        """
        Filtra trazas con soporte cronológico extendido.
        Preserva el ciclo diario por defecto para cuidar la memoria RAM.
        """
        hoy = timezone.now().date()
        
        # 🟢 CALIBRACIÓN CRONOLÓGICA INTELIGENTE
        if filtros and (filtros.get('fecha_inicio') or filtros.get('fecha_fin')):
            # Si el usuario mandó rango, inicializamos un Query vacío
            query = Q()
            if filtros.get('fecha_inicio'):
                query &= Q(created_at__date__gte=filtros['fecha_inicio'])
            if filtros.get('fecha_fin'):
                query &= Q(created_at__date__lte=filtros['fecha_fin'])
        else:
            # 🛡️ CANDADO POR DEFECTO: Si no hay fechas en el GET, se bloquea a "solo hoy"
            query = Q(created_at__date=hoy)
        
        # Inyección de los demás filtros tradicionales
        if filtros:
            if filtros.get('app_namespace'):
                query &= Q(app_namespace=filtros['app_namespace'])
            if filtros.get('action_type'):
                query &= Q(action_type=filtros['action_type'])
            if filtros.get('level_status'):
                query &= Q(level_status=filtros['level_status'])
            if filtros.get('search_target'):
                query &= Q(search_target__icontains=filtros['search_target'])
            if filtros.get('operador'):
                query &= Q(operator_user__email__icontains=filtros['operador'])

        logs_queryset = (
            SecurityAuditLog.objects.filter(query)
            .select_related('operator_user')
            .order_by('-created_at')[:limite]
        )
        
        return [{
            "timestamp": log.created_at,
            "tipo": log.level_status,
            "app": log.app_namespace.upper(),
            "verbo": log.action_type,
            "operador": log.operator_user.email if log.operator_user else "SISTEMA",
            "accion": log.action_name,
            "target": log.search_target or "--",
            "destino": log.target_scope
        } for log in logs_queryset]

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