from apps.inventory.selectors import AssetSelectors
from apps.security.decorators import axentra_gate_enforcer
from apps.shared.apps_config import AppIdentifier

from .common import render_inventory


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_view_dashboard")
def inventory_dashboard_view(request):
    return render_inventory(
        request,
        page="inventory/pages/inventory_dashboard.html",
        content="inventory/content/inventory_dashboard_content.html",
        context={
            "current_inventory_view": "inventory:dashboard",
            "metrics": AssetSelectors.dashboard_metrics(),
        },
    )
