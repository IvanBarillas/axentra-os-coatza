from apps.inventory.selectors import AssetSelectors, LoanSelectors
from apps.security.decorators import axentra_gate_enforcer
from apps.shared.apps_config import AppIdentifier

from .common import render_inventory
from .access import asset_scope, has_any_permission, loan_scope


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_view_dashboard")
def inventory_dashboard_view(request):
    scope, scope_department_id = asset_scope(request)
    registry_scope, registry_department_id = loan_scope(request)
    return render_inventory(
        request,
        page="inventory/pages/inventory_dashboard.html",
        content="inventory/content/inventory_dashboard_content.html",
        context={
            "current_inventory_view": "inventory:dashboard",
            "metrics": AssetSelectors.dashboard_metrics(
                scope=scope,
                actor_id=request.user.pk,
                department_id=scope_department_id,
            ),
            "inventory_scope": scope,
            "loan_metrics": LoanSelectors.dashboard_metrics(
                scope=registry_scope,
                actor_id=request.user.pk,
                department_id=registry_department_id,
            ),
            "is_global_inventory": registry_scope == "GLOBAL",
            "can_view_loans": has_any_permission(
                request,
                "can_request_loans",
                "can_manage_loans",
                "can_authorize_loans",
            ),
        },
    )
