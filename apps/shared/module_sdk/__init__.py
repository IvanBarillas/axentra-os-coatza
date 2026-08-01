"""API pública del SDK modular de Axentra OS."""

from .contracts import (
    ExternalAssetActivity,
    ExternalAssetActivityCollection,
    ModuleHealth,
    ModuleKind,
    ModuleManifest,
    ModuleRuntimeStatus,
)
from .registry import module_registry, register_module
from .catalog import ModuleCatalogEntry, available_module_catalog

__all__ = [
    "ExternalAssetActivity",
    "ExternalAssetActivityCollection",
    "ModuleHealth",
    "ModuleKind",
    "ModuleManifest",
    "ModuleRuntimeStatus",
    "ModuleCatalogEntry",
    "available_module_catalog",
    "module_registry",
    "register_module",
]
