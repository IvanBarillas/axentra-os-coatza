# apps/shared/manifest_registry.py
import importlib
from apps.shared.apps_config import AppIdentifier

class AxentraOSRegistry:
    """
    Motor ciego de reflexión que lee los manifiestos de las apps instaladas
    para alimentar al Launcher y las barras laterales del sistema.
    """
    
    @classmethod
    def get_all_manifests(cls):
        """
        Escanea las aplicaciones activas y recupera sus clases de manifiesto.
        """
        manifests = {}
        # Escaneamos únicamente las apps declaradas en producción por el momento
        apps_to_scan = {
            AppIdentifier.SECURITY: "apps.security.permissions.SecurityPermissions",
        }
        
        for app_code, import_path in apps_to_scan.items():
            try:
                module_path, class_name = import_path.rsplit('.', 1)
                mod = importlib.import_module(module_path)
                manifest_class = getattr(mod, class_name)
                manifests[app_code] = manifest_class
            except (ImportError, AttributeError):
                continue
        return manifests

    @classmethod
    def get_launcher_cards(cls, allowed_app_identifiers: list, is_root: bool = False):
        """
        Construye el diccionario de tarjetas para el index.html basado en permisos.
        """
        cards = []
        all_manifests = cls.get_all_manifests()
        
        for app_code, manifest in all_manifests.items():
            if is_root or app_code in allowed_app_identifiers:
                card_data = manifest.LAUNCHER_CARD.copy()
                card_data['app_code'] = app_code
                cards.append(card_data)
        return cards