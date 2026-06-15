# apps/shared/manifest_registry.py
import importlib
import logging
from apps.shared.apps_config import AppIdentifier

logger = logging.getLogger(__name__)

class AxentraOSRegistry:
    """
    🧠 RECON HUB & REFLECTION ENGINE - AXENTRA OS
    Motor ciego de descubrimiento e introspección de metadatos.
    Escanea la topología del disco duro buscando los manifiestos de permisos
    independientes de cada módulo para alimentar de forma dinámica al Launcher, 
    las barras laterales y los seeders del Core OS.
    """
    
    @classmethod
    def get_all_manifests(cls) -> dict:
        """
        🛰️ ESCÁNER AUTO-ROTATIVO DE MANIFIESTOS:
        Itera sobre el catálogo maestro de 'AppIdentifier.get_choices()' y mapea 
        en caliente las clases de permisos declaradas en el ecosistema.
        """
        manifests = {}
        
        # Recuperamos todos los slugs válidos del Core OS (security, accounts, organigrama, helpdesk, etc.)
        modulos_declarados = [choice[0] for choice in AppIdentifier.get_choices()]
        
        for app_code in modulos_declarados:
            # 🪐 REFACTORIZACIÓN 1: Formateo CamelCase inmune a guiones bajos (ej: dynamic_forms -> DynamicFormsPermissions)
            class_parts = [part.capitalize() for part in app_code.split('_')]
            class_name = f"{''.join(class_parts)}Permissions"
            
            # 🪐 REFACTORIZACIÓN 2: Desacoplamiento dinámico de rutas del disco duro
            # El chasis ahora busca de forma inteligente el permissions.py exclusivo de cada app satélite
            module_path = f"apps.{app_code}.permissions"
            
            try:
                mod = importlib.import_module(module_path)
                manifest_class = getattr(mod, class_name)
                manifests[app_code] = manifest_class
            except (ImportError, AttributeError) as e:
                # Cambiado a logger.warning o print temporal para que lo veas claro en tu terminal al migrar/correr
                logger.debug(f"ℹ️ [Registry Discovery] Nodo satélite [{app_code}] omitido o sin manifiesto estructurado: {e}")
                continue
                
        return manifests

    @classmethod
    def get_manifest_by_slug(cls, app_code: str):
        """
        🔍 DESPACHADOR BAJO DEMANDA:
        Retorna la clase de permisos de un módulo específico para el uso de decoradores y vistas.
        """
        return cls.get_all_manifests().get(app_code)

    @classmethod
    def get_launcher_cards(cls, allowed_app_identifiers: list, is_root: bool = False) -> dict:
        """
        🚀 ESCRITORIO OPERATIVO SECTORIZADO (LAUNCHER HUB):
        """
        cards_bucket = {
            'core_apps': [],       # 🏛️ Bloque Superior (Gobernanza Core)
            'satellite_apps': []   # 🛰️ Bloque Inferior (Módulos de Gestión)
        }
        
        all_manifests = cls.get_all_manifests()
        
        for app_code, manifest in all_manifests.items():
            if is_root or app_code in allowed_app_identifiers:
                if hasattr(manifest, 'LAUNCHER_CARD'):
                    card_data = manifest.LAUNCHER_CARD.copy()
                    card_data['app_code'] = app_code
                    
                    if card_data.get('is_core', False):
                        cards_bucket['core_apps'].append(card_data)
                    else:
                        cards_bucket['satellite_apps'].append(card_data)
                    
        return cards_bucket

  