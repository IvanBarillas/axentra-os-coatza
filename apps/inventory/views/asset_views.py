from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from apps.inventory.forms import AssetConditionUpdateForm, AssetCorrectionForm
from apps.inventory.selectors import AssetSelectors, DocumentSelectors
from apps.inventory.services import correct_asset, update_asset_condition
from apps.security.decorators import axentra_gate_enforcer
from apps.shared.apps_config import AppIdentifier

from .common import render_inventory, run_service, selector_or_404, success


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_view_assets")
def asset_list_view(request):
    filters = {
        "q": request.GET.get("q", "").strip(),
        "status": request.GET.get("status", "").strip(),
        "operational_status": request.GET.get("operational_status", "").strip(),
        "category_id": request.GET.get("category", "").strip(),
        "department_id": request.GET.get("department", "").strip(),
    }
    return render_inventory(request, page="inventory/pages/asset_list.html", content="inventory/content/asset_list_content.html", context={
        "current_inventory_view": "inventory:asset_list",
        "assets": AssetSelectors.listar_activos(**filters),
        "categories": AssetSelectors.categories(),
        "statuses": AssetSelectors.status_choices(),
        "operational_statuses": AssetSelectors.operational_status_choices(),
        **filters,
    })


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_view_assets")
def asset_detail_view(request, asset_id):
    asset = selector_or_404(lambda: AssetSelectors.obtener_expediente(asset_id))
    return render_inventory(request, page="inventory/pages/asset_detail.html", content="inventory/content/asset_detail_content.html", context={
        "current_inventory_view": "inventory:asset_list", "asset": asset,
        "documents": DocumentSelectors.asset_documents(asset.id),
        "photos": DocumentSelectors.asset_photos(asset.id),
    })


def _asset_action(request, asset_id, *, form_class, service, title):
    asset = selector_or_404(lambda: AssetSelectors.obtener(asset_id))
    form = form_class(request.POST or None)
    if request.method == "POST" and form.is_valid():
        result = run_service(form, lambda: service(asset_id=asset.id, data=form.to_dto(), actor=request.user, request_context=None))
        if result:
            success(request, title)
            return redirect(reverse("inventory:asset_detail", kwargs={"asset_id": asset.id}))
    return render_inventory(request, page="inventory/pages/asset_action_form.html", content="inventory/content/asset_action_form_content.html", context={
        "current_inventory_view": "inventory:asset_list", "asset": asset, "form": form, "form_title": title,
    }, status=422 if request.method == "POST" else 200)


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_edit_asset")
def asset_correct_view(request, asset_id):
    return _asset_action(request, asset_id, form_class=AssetCorrectionForm, service=correct_asset, title="Activo corregido correctamente.")


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_edit_asset")
def asset_condition_view(request, asset_id):
    return _asset_action(request, asset_id, form_class=AssetConditionUpdateForm, service=update_asset_condition, title="Condición del activo actualizada.")
