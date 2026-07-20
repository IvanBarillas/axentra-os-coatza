from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from apps.inventory.forms import AssetConditionUpdateForm, AssetCorrectionForm, AssetLoanFromAssetForm
from apps.inventory.models import AssetOperationalStatus
from apps.inventory.selectors import AssetSelectors, DocumentSelectors
from apps.inventory.services import correct_asset, create_asset_loan, update_asset_condition
from apps.security.decorators import axentra_gate_enforcer
from apps.shared.apps_config import AppIdentifier

from .common import apply_directory_choices, render_inventory, run_service, selector_or_404, success
from .access import asset_scope, has_any_permission


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_view_assets")
def asset_list_view(request):
    scope, scope_department_id = asset_scope(request)
    filters = {
        "q": request.GET.get("q", "").strip(),
        "status": request.GET.get("status", "").strip(),
        "operational_status": request.GET.get("operational_status", "").strip(),
        "category_id": request.GET.get("category", "").strip(),
        "department_id": request.GET.get("department", "").strip(),
    }
    return render_inventory(request, page="inventory/pages/asset_list.html", content="inventory/content/asset_list_content.html", context={
        "current_inventory_view": "inventory:asset_list",
        "assets": AssetSelectors.listar_activos(
            **filters,
            scope=scope,
            actor_id=request.user.pk,
            scope_department_id=scope_department_id,
        ),
        "categories": AssetSelectors.categories(),
        "statuses": AssetSelectors.status_choices(),
        "operational_statuses": AssetSelectors.operational_status_choices(),
        "inventory_scope": scope,
        **filters,
    })


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_view_assets")
def asset_detail_view(request, asset_id):
    scope, scope_department_id = asset_scope(request)
    asset = selector_or_404(lambda: AssetSelectors.obtener_expediente(
        asset_id,
        scope=scope,
        actor_id=request.user.pk,
        department_id=scope_department_id,
    ))
    can_manage_loans = has_any_permission(request, "can_manage_loans")
    can_authorize_loans = has_any_permission(request, "can_authorize_loans")
    return render_inventory(request, page="inventory/pages/asset_detail.html", content="inventory/content/asset_detail_content.html", context={
        "current_inventory_view": "inventory:asset_list", "asset": asset,
        "documents": DocumentSelectors.asset_documents(asset.id),
        "photos": DocumentSelectors.asset_photos(asset.id),
        "can_edit_asset": has_any_permission(request, "can_edit_asset"),
        "can_loan_asset": (
            can_authorize_loans
            and not can_manage_loans
            and asset.operational_status in {
                AssetOperationalStatus.AVAILABLE,
                AssetOperationalStatus.ASSIGNED,
            }
        ),
    })


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_authorize_loans")
def asset_loan_create_view(request, asset_id):
    """Permite al director prestar uno de los bienes visibles de su dependencia."""

    scope, scope_department_id = asset_scope(request)
    asset = selector_or_404(lambda: AssetSelectors.obtener(
        asset_id,
        scope=scope,
        actor_id=request.user.pk,
        department_id=scope_department_id,
    ))
    form = apply_directory_choices(AssetLoanFromAssetForm(
        request.POST or None,
        asset_id=asset.id,
        origin_department_id=asset.current_dependencia_id,
        origin_area_id=asset.current_area_id,
        origin_site_id=asset.current_sede_id,
    ))
    if request.method == "POST" and form.is_valid():
        loan = run_service(
            form,
            lambda: create_asset_loan(
                data=form.to_dto(),
                actor_id=request.user.pk,
                request=request,
            ),
        )
        if loan:
            success(request, f"Préstamo {loan.folio} creado en borrador.")
            return redirect(reverse("inventory:loan_detail", kwargs={"loan_id": loan.id}))
    return render_inventory(
        request,
        page="inventory/pages/asset_loan_form.html",
        content="inventory/content/asset_loan_form_content.html",
        context={
            "current_inventory_view": "inventory:asset_list",
            "asset": asset,
            "form": form,
        },
        status=422 if request.method == "POST" else 200,
    )


def _asset_action(request, asset_id, *, form_class, service, title):
    scope, scope_department_id = asset_scope(request)
    asset = selector_or_404(lambda: AssetSelectors.obtener(
        asset_id,
        scope=scope,
        actor_id=request.user.pk,
        department_id=scope_department_id,
    ))
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
