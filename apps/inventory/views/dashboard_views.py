# apps/inventory/views/dashboard_views.py

from apps.inventory.selectors import AssetSelectors, LoanSelectors
from apps.security.decorators import axentra_gate_enforcer
from apps.shared.apps_config import AppIdentifier

from .access import (
    asset_scope,
    has_any_permission,
    loan_scope,
)
from .common import render_inventory

@axentra_gate_enforcer(AppIdentifier.INVENTORY)
def inventory_dashboard_view(request):
    """
    Página de entrada universal de Inventory.

    El decorador exige automáticamente `has_access_module`, por lo que no
    es necesario declarar un permiso fino adicional.

    La información mostrada se limita posteriormente según el alcance
    funcional del usuario:

    - GLOBAL: Patrimonio, administradores y auditoría autorizada.
    - DEPARTMENT: titulares o directores de dependencia.
    - OWN: resguardatarios y usuarios de alcance personal.
    """

    asset_visibility, asset_department_id = asset_scope(request)
    loan_visibility, loan_department_id = loan_scope(request)

    can_view_loans = has_any_permission(
        request,
        "can_request_loans",
        "can_manage_loans",
        "can_authorize_loans",
    )

    return render_inventory(
        request,
        page="inventory/pages/inventory_dashboard.html",
        content=(
            "inventory/content/"
            "inventory_dashboard_content.html"
        ),
        context={
            "current_inventory_view": "inventory:dashboard",

            "metrics": AssetSelectors.dashboard_metrics(
                scope=asset_visibility,
                actor_id=request.user.pk,
                department_id=asset_department_id,
            ),

            "inventory_scope": asset_visibility,

            "loan_metrics": LoanSelectors.dashboard_metrics(
                scope=loan_visibility,
                actor_id=request.user.pk,
                department_id=loan_department_id,
            ),

            "is_global_inventory": (
                loan_visibility == "GLOBAL"
            ),

            "can_view_loans": can_view_loans,
        },
    )
    
