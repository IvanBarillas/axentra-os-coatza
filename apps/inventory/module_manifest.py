"""Manifiesto SDK del módulo Inventory."""

from apps.shared.module_sdk.contracts import ModuleKind, ModuleManifest


MODULE_MANIFEST = ModuleManifest(
    code="inventory",
    name="Inventario Patrimonial",
    description=(
        "Administración de bienes patrimoniales, solicitudes de alta, "
        "resguardos, movimientos, préstamos, bajas, auditoría física, "
        "documentos, depreciación y conciliación contable."
    ),
    entry_url="inventory:dashboard",
    urlconf="apps.inventory.urls.inventory_urls",
    url_prefix="app/inventory/",
    version="1.0.0",
    icon="package-search",
    kind=ModuleKind.SATELLITE,
    dependencies=(
        "security",
        "accounts",
        "organigrama",
    ),
    optional_integrations=(
        "helpdesk",
    ),
    default_enabled=False,
    can_disable=True,
)


__all__ = ["MODULE_MANIFEST"]