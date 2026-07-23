from dataclasses import dataclass, field

from django.conf import settings

from .contracts import ModuleKind


@dataclass(frozen=True, slots=True)
class ModuleCatalogEntry:
    """Producto conocido por el Core, esté o no instalado en este proyecto."""

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


DEFAULT_MODULE_CATALOG = (
    ModuleCatalogEntry(
        code="inventory",
        name="Inventario Patrimonial",
        description=(
            "Bienes, resguardos, movimientos, préstamos, bajas, auditoría "
            "física y conciliación contable."
        ),
        distribution="axentra-inventory",
        icon="package-search",
        dependencies=("security", "accounts", "organigrama"),
        install_steps=(
            "Obtenga la distribución institucional autorizada de Inventory.",
            "Añada su AppConfig a INSTALLED_APPS.",
            "Ejecute python manage.py migrate.",
            "Ejecute python manage.py check_axentra_modules --persist.",
            "Ejecute python manage.py bootstrap_axentra_owner.",
            "Active el módulo desde esta Estación Central.",
        ),
    ),
    ModuleCatalogEntry(
        code="helpdesk",
        name="Mesa de Ayuda",
        description=(
            "Tickets, atención técnica, acuerdos de servicio e integraciones "
            "opcionales con activos."
        ),
        distribution="axentra-helpdesk",
        icon="headset",
        dependencies=("security", "accounts", "organigrama"),
        install_steps=(
            "Obtenga la distribución institucional autorizada de Helpdesk.",
            "Añada su AppConfig a INSTALLED_APPS.",
            "Ejecute python manage.py migrate.",
            "Ejecute python manage.py check_axentra_modules --persist.",
            "Ejecute python manage.py bootstrap_axentra_owner.",
            "Active el módulo desde esta Estación Central.",
        ),
    ),
)


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
    """
    Devuelve el catálogo extensible de productos.

    AXENTRA_MODULE_CATALOG puede añadir o reemplazar entradas sin modificar
    este archivo. Se acepta una secuencia de diccionarios o de entradas.
    """

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
