"""Composición de aplicaciones satélite instaladas por Coatza."""

COATZA_APPS = (
    "apps.inventory.apps.InventoryConfig",
)


def compose_installed_apps(core_apps):
    """Agrega satélites de Coatza sin modificar ni duplicar apps del Core."""
    installed = list(core_apps)
    for app in COATZA_APPS:
        if app not in installed:
            installed.append(app)
    return installed
