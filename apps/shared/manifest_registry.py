# apps/shared/manifest_registry.py
import importlib
import logging
from apps.shared.apps_config import AppIdentifier

logger = logging.getLogger(__name__)

class AxentraOSRegistry:
    
    @classmethod
    def get_all_manifests(cls) -> dict:
        """
        🛰️ ESCÁNER HÍBRIDO AUTO-ROTATIVO:
        Busca manifiestos de forma nativa en la ruta de cada módulo. 
        Si no existen en su propia carpeta, aplica un fallback automático
        hacia el archivo unificado de la app de seguridad central.
        """
        manifests = {}
        modulos_declarados = [choice[0] for choice in AppIdentifier.get_choices()]
        
        for app_code in modulos_declarados:
            class_parts = [part.capitalize() for part in app_code.split('_')]
            class_name = f"{''.join(class_parts)}Permissions"
            
            # Intento 1: Buscar de forma limpia en su propia app satélite dedicada
            module_path_satelite = f"apps.{app_code}.permissions"
            
            try:
                mod = importlib.import_module(module_path_satelite)
                manifest_class = getattr(mod, class_name)
                manifests[app_code] = manifest_class
                continue # Encontrado en su propio búnker, saltamos al siguiente
            except (ImportError, AttributeError):
                # Si no existe la carpeta o la clase ahí, no pasa nada, procedemos al Fallback
                pass
            
            # Intento 2: Fallback hacia el archivo central unificado de Security
            module_path_core = "apps.security.permissions"
            try:
                mod = importlib.import_module(module_path_core)
                if hasattr(mod, class_name):
                    manifests[app_code] = getattr(mod, class_name)
                else:
                    logger.debug(f"ℹ️ [Registry] Clase [{class_name}] no localizada en ninguna capa.")
            except ImportError as e:
                logger.debug(f"⚠️ [Registry Critical] Archivo base de seguridad ausente: {e}")
                
        return manifests

    @classmethod
    def get_manifest_by_slug(cls, app_code: str):
        return cls.get_all_manifests().get(app_code)

