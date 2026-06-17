import logging
from django.db import models
from apps.shared.apps_config import AppIdentifier

try:
    from apps.security.models.organigrama import AppDependencyCapability
except ImportError:
    from apps.security.models import AppDependencyCapability

logger = logging.getLogger('axentra.security')

class AxentraCapabilityOrchestrator:
    """
    💎 ORQUESTADOR MAESTRO DE CAPACIDADES DEPARTAMENTALES (AXENTRA OS CORE)
    
    Centraliza las reglas de negocio distributivas para la federación de dependencias.
    Soporta de forma nativa escenarios híbridos donde un nodo orgánico posee
    facultades duales (ALFA y BETA en simultáneo) para el mismo aplicativo satélite.
    """

    @staticmethod
    def obtener_estatus_capacidad(user, app_slug: str) -> dict:
        """
        Analiza el árbol orgánico del usuario y dictamina su matriz transaccional.
        
        Soporta la coexistencia de capacidades (es_alfa=True y es_beta=True).
        """
        resultado = {
            "tiene_acceso": False,
            "es_alfa": False,
            "es_beta": False,
            "es_hibrido": False,  # ✨ Nueva bandera táctica para identificar el estado "Ambos"
            "dependencia": None,
            "error_codigo": None
        }

        # 🛑 COMPUERTA 0: Control de Autenticación Base
        if not user or not user.is_authenticated:
            resultado["error_codigo"] = "ANONYMOUS_USER"
            return resultado

        # 👑 COMPUERTA A: BYPASS MAESTRO PARA ADMINISTRADORES GLOBAL / IMMUNITY ROL
        perfil = getattr(user, 'axentra_profile', None) or getattr(user, 'funcionario_profile', None)
        is_root = (
            user.is_superuser or 
            getattr(user, 'is_manager', False) or 
            (perfil and getattr(perfil, 'is_root_admin', False))
        )

        if is_root:
            resultado["tiene_acceso"] = True
            resultado["es_alfa"] = True
            resultado["es_beta"] = True  # El Administrador Maestro es inherentemente ambos
            resultado["es_hibrido"] = True
            if perfil:
                area = getattr(perfil, 'area', None) or getattr(perfil, 'area_operativa', None)
                if area and hasattr(area, 'dependencia'):
                    resultado["dependencia"] = area.dependencia
            return resultado

        # 🏢 COMPUERTA B: EXTRACCIÓN SEGURO DEL NODO ORGÁNICO
        if not perfil:
            resultado["error_codigo"] = "MISSING_PROFILE"
            return resultado

        area = getattr(perfil, 'area', None) or getattr(perfil, 'area_operativa', None)
        if not area or not getattr(area, 'dependencia', None):
            resultado["error_codigo"] = "MISSING_ORGANIZATION_NODE"
            return resultado

        dependencia = area.dependencia
        resultado["dependencia"] = dependencia

        # 🛰️ COMPUERTA C: CONSULTA ALINEADA AL SLUG DE APPIDENTIFIER
        try:
            capacidad = AppDependencyCapability.objects.select_related('app').get(
                dependencia=dependencia,
                app__slug=app_slug.strip().lower()
            )
        except AppDependencyCapability.DoesNotExist:
            resultado["error_codigo"] = f"NO_CAPABILITY_REGISTERED_FOR_{app_slug.upper()}"
            return resultado

        # 📊 COMPUERTA D: EVALUACIÓN MULTI-MODAL (SOPORTA AMBOS SIMULTÁNEAMENTE)
        resultado["es_alfa"] = capacidad.flag_alfa
        resultado["es_beta"] = capacidad.flag_beta
        
        # Activamos el flag de estado híbrido si ambos campos están marcados en la base de datos
        if capacidad.flag_alfa and capacidad.flag_beta:
            resultado["es_hibrido"] = True
        
        # El acceso es válido si cuenta con al menos una capacidad activa
        if capacidad.flag_alfa or capacidad.flag_beta:
            resultado["tiene_acceso"] = True
        else:
            resultado["error_codigo"] = "CAPABILITIES_DISABLED"

        return resultado