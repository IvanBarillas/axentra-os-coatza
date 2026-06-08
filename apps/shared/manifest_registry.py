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
        
        Sustituye por completo los diccionarios fijos con rutas hardcodeadas.
        """
        manifests = {}
        
        # Recuperamos todos los slugs válidos del Core OS (security, accounts, organigrama, etc.)
        modulos_declarados = [choice[0] for choice in AppIdentifier.get_choices()]
        
        for app_code in modulos_declarados:
            # Construcción predictiva de rutas bajo Clean Architecture:
            # Ejemplo: 'accounts' -> 'apps.security.permissions.AccountsPermissions' (Si todo está en security)
            # O si se desacopla: 'apps.accounts.permissions.AccountsPermissions'
            # Mantenemos la convención actual: Todo vive dentro del paquete 'apps.security' o relativo
            # Evaluamos dinámicamente si tus archivos viven en la app unificada de seguridad:
            
            # Formateamos el nombre de la clase esperado de fábrica (Ej: 'SecurityPermissions', 'AccountsPermissions')
            class_name = f"{app_code.capitalize()}Permissions"
            module_path = f"apps.security.permissions" # Chasis unificado actual
            
            try:
                # Intentamos importar el módulo de gobernanza en la RAM
                mod = importlib.import_module(module_path)
                manifest_class = getattr(mod, class_name)
                
                # Registramos el nodo descriptor acoplándolo a su slug
                manifests[app_code] = manifest_class
            except (ImportError, AttributeError) as e:
                # Si un sub-módulo no cuenta con archivo o clase descriptor, el Core lo ignora sin colapsar
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
    def get_launcher_cards(cls, allowed_app_identifiers: list, is_root: bool = False) -> list:
        """
        🚀 ESCRITORIO OPERATIVO (LAUNCHER HUB):
        Construye y empaqueta el lote total de tarjetas analíticas para alimentar 
        el escritorio principal del operador, aplicando un filtrado estricto por privilegios.
        """
        cards = []
        all_manifests = cls.get_all_manifests()
        
        for app_code, manifest in all_manifests.items():
            # El Operador Supremo (is_root) ve todo el chasis; los funcionarios comunes pasan por aduana
            if is_root or app_code in allowed_app_identifiers:
                # Validamos que el manifiesto cuente con los metadatos visuales exigidos por el DOM
                if hasattr(manifest, 'LAUNCHER_CARD'):
                    card_data = manifest.LAUNCHER_CARD.copy()
                    card_data['app_code'] = app_code
                    cards.append(card_data)
                    
        return cards