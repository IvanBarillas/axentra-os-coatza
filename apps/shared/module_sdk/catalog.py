from dataclasses import dataclass, field

from django.conf import settings

from .contracts import ModuleKind


@dataclass(frozen=True, slots=True)
class ModuleCatalogEntry:
    """Producto configurable conocido por una distribución, esté o no instalado."""

    code: str
    name: str
    description: str
    distribution: str
    icon: str = "blocks"
    kind: ModuleKind = ModuleKind.SATELLITE
    dependencies: tuple[str, ...] = field(default_factory=tuple)
    install_steps: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self):
        code = str(self.code).strip().lower()
        if not code or not code.replace("_", "").replace("-", "").isalnum():
            raise ValueError("El producto requiere un código técnico válido.")
        object.__setattr__(self, "code", code)
        object.__setattr__(
            self,
            "dependencies",
            tuple(str(item).strip().lower() for item in self.dependencies),
        )
        object.__setattr__(self, "install_steps", tuple(self.install_steps))


# El Core no conoce productos de dominio. Cada distribución puede declarar
# su catálogo mediante AXENTRA_MODULE_CATALOG sin modificar el SDK.
DEFAULT_MODULE_CATALOG = ()


def _entry_from_mapping(data):
    kind = data.get("kind", ModuleKind.SATELLITE)
    if not isinstance(kind, ModuleKind):
        kind = ModuleKind(str(kind).strip().upper())
    return ModuleCatalogEntry(
        code=data["code"],
        name=data["name"],
        description=data.get("description", ""),
        distribution=data.get("distribution", ""),
        icon=data.get("icon", "blocks"),
        kind=kind,
        dependencies=tuple(data.get("dependencies", ())),
        install_steps=tuple(data.get("install_steps", ())),
    )


def available_module_catalog():
    """Devuelve exclusivamente los productos declarados por la distribución."""

    entries = {entry.code: entry for entry in DEFAULT_MODULE_CATALOG}
    configured = getattr(settings, "AXENTRA_MODULE_CATALOG", ())
    for item in configured:
        entry = (
            item
            if isinstance(item, ModuleCatalogEntry)
            else _entry_from_mapping(item)
        )
        entries[entry.code] = entry
    return tuple(entries.values())


__all__ = [
    "DEFAULT_MODULE_CATALOG",
    "ModuleCatalogEntry",
    "available_module_catalog",
]
