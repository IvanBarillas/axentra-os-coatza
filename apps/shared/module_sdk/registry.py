import importlib
import logging
from collections import OrderedDict
from threading import RLock

from django.apps import apps

from .contracts import ModuleKind, ModuleManifest

logger = logging.getLogger(__name__)


BUILTIN_MODULES = (
    ModuleManifest(
        code="security", name="Ciberseguridad", description="Permisos, auditoría y control de acceso.",
        entry_url="security:control_panel", icon="shield-check", kind=ModuleKind.CORE,
        default_enabled=True, can_disable=False,
    ),
    ModuleManifest(
        code="configuration", name="Configuración institucional", description="Identidad y parámetros de la institución.",
        entry_url="security:tenant_config", icon="settings", kind=ModuleKind.CORE,
        dependencies=("security",), default_enabled=True, can_disable=False,
    ),
    ModuleManifest(
        code="accounts", name="Usuarios", description="Directorio y cuentas del personal.",
        entry_url="accounts:funcionario_list", icon="users", kind=ModuleKind.CORE,
        dependencies=("security",), default_enabled=True, can_disable=False,
    ),
    ModuleManifest(
        code="organigrama", name="Organización", description="Sedes, dependencias y áreas operativas.",
        entry_url="organigrama:estructura_list", icon="git-fork", kind=ModuleKind.CORE,
        dependencies=("security", "accounts"), default_enabled=True, can_disable=False,
    ),
)


class ModuleRegistry:
    def __init__(self):
        self._items = OrderedDict()
        self._lock = RLock()
        self._discovered = False
        for manifest in BUILTIN_MODULES:
            self.register(manifest)

    def register(self, manifest, *, replace=False):
        if not isinstance(manifest, ModuleManifest):
            raise TypeError("El manifiesto debe ser ModuleManifest.")
        with self._lock:
            if manifest.code in self._items and not replace:
                if self._items[manifest.code] == manifest:
                    return manifest
                raise ValueError(f"El módulo [{manifest.code}] ya está registrado.")
            self._items[manifest.code] = manifest
        return manifest

    def discover(self, *, force=False):
        with self._lock:
            if self._discovered and not force:
                return self.all()
            for app_config in apps.get_app_configs():
                module_path = f"{app_config.name}.module_manifest"
                try:
                    module = importlib.import_module(module_path)
                except ModuleNotFoundError as exc:
                    if exc.name != module_path:
                        logger.exception("Error importando %s", module_path)
                    continue
                manifest = getattr(module, "MODULE_MANIFEST", None)
                if manifest:
                    self.register(manifest, replace=True)
            # Compatibilidad temporal: manifiestos antiguos basados únicamente
            # en permissions.py siguen visibles hasta adoptar module_manifest.py.
            from apps.shared.apps_config import AppIdentifier
            from apps.shared.manifest_registry import AxentraOSRegistry
            labels = dict(AppIdentifier.get_choices())
            legacy_entries = {
                "security": "security:control_panel",
                "configuration": "security:tenant_config",
                "accounts": "accounts:funcionario_list",
                "organigrama": "organigrama:estructura_list",
                "inventory": "inventory:dashboard",
            }
            legacy_urls = {
                "inventory": (
                    "apps.inventory.urls.inventory_urls",
                    "app/inventory/",
                ),
            }
            for code in AxentraOSRegistry.get_all_manifests():
                if code in self._items:
                    continue
                urlconf, url_prefix = legacy_urls.get(code, ("", ""))
                self.register(ModuleManifest(
                    code=code,
                    name=labels.get(code, code.replace("_", " ").title()),
                    description=f"Módulo operativo {labels.get(code, code)}.",
                    entry_url=legacy_entries.get(code, f"{code}:dashboard"),
                    urlconf=urlconf,
                    url_prefix=url_prefix,
                    icon="blocks",
                    default_enabled=True,
                ))
            self._discovered = True
            return self.all()

    def get(self, code):
        self.discover()
        return self._items.get(str(code).strip().lower())

    def all(self):
        return tuple(self._items.values())

    def codes(self):
        self.discover()
        return tuple(self._items.keys())


module_registry = ModuleRegistry()


def register_module(manifest, *, replace=False):
    return module_registry.register(manifest, replace=replace)


__all__ = ["ModuleRegistry", "module_registry", "register_module"]
