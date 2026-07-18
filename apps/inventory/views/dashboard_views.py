# apps/inventory/views/dashboard_views.py

from django.views.decorators.http import require_http_methods

from apps.inventory.selectors import AssetSelectors
from apps.security.decorators import axentra_gate_enforcer
from apps.shared.apps_config import AppIdentifier

from .common import render_inventory


@require_http_methods(["GET"])
@axentra_gate_enforcer(
    AppIdentifier.INVENTORY,
    required_fine_permission="can_view_dashboard",
)
def inventory_dashboard_view(request):
    metrics = AssetSelectors.dashboard_metrics(
        actor_id=request.user.id,
    )

    return render_inventory(
        request,
        page="inventory/pages/inventory_dashboard.html",
        content="inventory/content/inventory_dashboard_content.html",
        context={
            "current_inventory_view": "inventory:dashboard",
            "metrics": metrics,
            "inventory_scope": metrics["scope"],
        },
    )


__all__ = ["inventory_dashboard_view"]