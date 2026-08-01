from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.inventory.forms import AssetConditionUpdateForm, AssetCorrectionForm, AssetLoanFromAssetForm, AssetPhotoUploadForm
from apps.inventory.integrations import get_external_asset_activity
from apps.inventory.models import AssetLoanStatus, AssetOperationalStatus
from apps.inventory.selectors import AssetSelectors, CoreDirectorySelectors, DocumentSelectors, InventoryScope
from apps.inventory.services import correct_asset, create_asset_loan, update_asset_condition, upload_asset_photo
from apps.security.decorators import axentra_gate_enforcer
from apps.shared.apps_config import AppIdentifier

from .common import apply_directory_choices, render_inventory, run_service, selector_or_404, success
from .access import asset_scope, has_any_permission


def _visible_asset(request, asset_id):
    scope, scope_department_id = asset_scope(request)
    return selector_or_404(lambda: AssetSelectors.obtener_expediente(
        asset_id,
        scope=scope,
        actor_id=request.user.pk,
        department_id=scope_department_id,
    ))


def _asset_report_context(request, asset_id):
    asset = _visible_asset(request, asset_id)
    return {
        "asset": asset,
        "generated_at": timezone.localtime(),
        "documents": DocumentSelectors.asset_documents(asset.id),
        "photos": DocumentSelectors.asset_photos(asset.id),
    }


def _asset_context(request, asset, current_view):
    open_statuses = {
        AssetLoanStatus.REQUESTED,
        AssetLoanStatus.DEPARTMENT_APPROVED,
        AssetLoanStatus.AUTHORIZED,
        AssetLoanStatus.DELIVERED,
        AssetLoanStatus.OVERDUE,
        AssetLoanStatus.RETURN_PENDING,
    }
    active_loan = next(
        (loan for loan in asset.loans.all() if loan.status in open_statuses),
        None,
    )
    external_activity = get_external_asset_activity(
        asset.id,
        actor_id=request.user.pk,
    )
    return {
        "asset": asset,
        "asset_context_sidebar": True,
        "current_inventory_view": current_view,
        "active_loan": active_loan,
        "external_activity": external_activity,
        "blocking_external_activity": (
            external_activity.blocking_items[0]
            if external_activity.blocking_items else None
        ),
    }


def _render_asset_section(request, asset, *, current_view, section, extra=None, status=200):
    context = _asset_context(request, asset, current_view)
    context.update({"asset_section": section, **(extra or {})})
    return render_inventory(
        request,
        page="inventory/pages/asset_section.html",
        content="inventory/content/asset_section_content.html",
        context=context,
        status=status,
    )


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_view_assets")
def asset_list_view(request):
    scope, scope_department_id = asset_scope(request)
    filters = {
        "q": request.GET.get("q", "").strip(),
        "status": request.GET.get("status", "").strip(),
        "operational_status": request.GET.get("operational_status", "").strip(),
        "category_id": request.GET.get("category", "").strip(),
        "site_id": request.GET.get("site", "").strip(),
        "department_id": request.GET.get("department", "").strip(),
        "area_id": request.GET.get("area", "").strip(),
        "custodian_id": request.GET.get("custodian", "").strip(),
        "capitalizable": request.GET.get("capitalizable", "").strip(),
        "loan_status": request.GET.get("loan_status", "").strip(),
    }
    queryset = AssetSelectors.listar_activos(
        **filters,
        scope=scope,
        actor_id=request.user.pk,
        scope_department_id=scope_department_id,
    )
    page_obj = Paginator(queryset, 30).get_page(request.GET.get("page"))
    is_global_scope = scope == InventoryScope.GLOBAL
    directory = CoreDirectorySelectors.form_choices(
        site_id=filters["site_id"] or None,
        department_id=filters["department_id"] or None,
    ) if is_global_scope else {
        "site_choices": [], "department_choices": [],
        "area_choices": [], "user_choices": [],
    }
    return render_inventory(request, page="inventory/pages/asset_list.html", content="inventory/content/asset_list_content.html", context={
        "current_inventory_view": "inventory:asset_list",
        "assets": page_obj.object_list,
        "page_obj": page_obj,
        "categories": AssetSelectors.categories(),
        "statuses": AssetSelectors.status_choices(),
        "operational_statuses": AssetSelectors.operational_status_choices(),
        "inventory_scope": scope,
        "is_global_inventory_scope": is_global_scope,
        **directory,
        **filters,
    })


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_view_assets")
def asset_directory_options_view(request):
    """Opciones institucionales dependientes para los filtros de Patrimonio."""
    scope, _ = asset_scope(request)
    if scope != InventoryScope.GLOBAL:
        raise PermissionDenied("Los filtros globales son exclusivos de Patrimonio.")
    site_id = request.GET.get("site_id", "").strip() or None
    department_id = request.GET.get("department_id", "").strip() or None
    choices = CoreDirectorySelectors.form_choices(
        site_id=site_id,
        department_id=department_id,
    )
    return JsonResponse({
        key: [{"value": value, "label": label} for value, label in values]
        for key, values in choices.items()
    })


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_view_assets")
def asset_detail_view(request, asset_id):
    asset = _visible_asset(request, asset_id)
    can_manage_loans = has_any_permission(request, "can_manage_loans")
    can_authorize_loans = has_any_permission(request, "can_authorize_loans")
    context = _asset_context(request, asset, "inventory:asset_detail")
    context.update({
        "documents": DocumentSelectors.asset_documents(asset.id),
        "photos": DocumentSelectors.asset_photos(asset.id),
        "can_edit_asset": has_any_permission(request, "can_edit_asset"),
        "can_loan_asset": (
            can_authorize_loans
            and not can_manage_loans
            and not context["external_activity"].has_blocking_activity
            and asset.operational_status in {
                AssetOperationalStatus.AVAILABLE,
                AssetOperationalStatus.ASSIGNED,
            }
        ),
    })
    return render_inventory(request, page="inventory/pages/asset_detail.html", content="inventory/content/asset_detail_content.html", context=context)


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_view_assets")
def asset_technical_view(request, asset_id):
    asset = _visible_asset(request, asset_id)
    return _render_asset_section(request, asset, current_view="inventory:asset_technical", section="technical")


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_view_assets")
def asset_custodies_view(request, asset_id):
    asset = _visible_asset(request, asset_id)
    return _render_asset_section(request, asset, current_view="inventory:asset_custodies", section="custodies", extra={"records": asset.custody_assignments.all()})


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_view_assets")
def asset_loans_view(request, asset_id):
    asset = _visible_asset(request, asset_id)
    return _render_asset_section(request, asset, current_view="inventory:asset_loans", section="loans", extra={"records": asset.loans.all()})


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_view_assets")
def asset_movements_view(request, asset_id):
    asset = _visible_asset(request, asset_id)
    return _render_asset_section(request, asset, current_view="inventory:asset_movements", section="movements", extra={"records": asset.movements.all()})


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_view_assets")
def asset_external_activity_view(request, asset_id):
    asset = _visible_asset(request, asset_id)
    return _render_asset_section(
        request,
        asset,
        current_view="inventory:asset_external_activity",
        section="external_activity",
    )


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_view_assets")
def asset_documents_view(request, asset_id):
    asset = _visible_asset(request, asset_id)
    return _render_asset_section(request, asset, current_view="inventory:asset_documents", section="documents", extra={"records": DocumentSelectors.asset_documents(asset.id)})


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_view_assets")
def asset_photos_view(request, asset_id):
    asset = _visible_asset(request, asset_id)
    can_upload = has_any_permission(request, "can_manage_photos")
    if request.method == "POST" and not can_upload:
        raise PermissionDenied("No cuenta con permiso para cargar fotografías.")
    form = AssetPhotoUploadForm(request.POST or None, request.FILES or None, asset_id=asset.id) if can_upload else None
    if request.method == "POST" and form and form.is_valid():
        photo = run_service(form, lambda: upload_asset_photo(asset_id=asset.id, data=form.to_dto(), actor_id=request.user.pk, request=request))
        if photo:
            success(request, "Fotografía agregada al expediente.")
            return redirect(reverse("inventory:asset_photos", kwargs={"asset_id": asset.id}))
    return _render_asset_section(
        request,
        asset,
        current_view="inventory:asset_photos",
        section="photos",
        extra={"records": DocumentSelectors.asset_photos(asset.id), "form": form, "can_upload_photos": can_upload},
        status=422 if request.method == "POST" else 200,
    )


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_view_financials")
def asset_financials_view(request, asset_id):
    asset = _visible_asset(request, asset_id)
    return _render_asset_section(request, asset, current_view="inventory:asset_financials", section="financials", extra={"records": asset.depreciation_records.all()})


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_view_assets")
def asset_audits_view(request, asset_id):
    asset = _visible_asset(request, asset_id)
    if not has_any_permission(request, "can_manage_physical_audits", "can_scan_physical_audits"):
        raise PermissionDenied
    return _render_asset_section(request, asset, current_view="inventory:asset_audits", section="audits", extra={"records": asset.physical_audit_items.all()})


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_view_assets")
def asset_disposals_view(request, asset_id):
    asset = _visible_asset(request, asset_id)
    if not has_any_permission(request, "can_request_disposals", "can_manage_disposals", "can_authorize_disposals"):
        raise PermissionDenied
    return _render_asset_section(request, asset, current_view="inventory:asset_disposals", section="disposals", extra={"records": asset.disposal_requests.all()})


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_view_audit")
def asset_history_view(request, asset_id):
    asset = _visible_asset(request, asset_id)
    return _render_asset_section(request, asset, current_view="inventory:asset_history", section="history", extra={"records": asset.audit_logs.all()})


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_view_assets")
def asset_technical_sheet_view(request, asset_id):
    return render(
        request,
        "inventory/reports/asset_technical_sheet.html",
        _asset_report_context(request, asset_id),
    )


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_view_assets")
def asset_extended_record_view(request, asset_id):
    return render(
        request,
        "inventory/reports/asset_extended_record.html",
        _asset_report_context(request, asset_id),
    )


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
            **_asset_context(request, asset, "inventory:asset_loans"),
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
        **_asset_context(request, asset, "inventory:asset_detail"), "form": form, "form_title": title,
    }, status=422 if request.method == "POST" else 200)


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_edit_asset")
def asset_correct_view(request, asset_id):
    return _asset_action(request, asset_id, form_class=AssetCorrectionForm, service=correct_asset, title="Activo corregido correctamente.")


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_edit_asset")
def asset_condition_view(request, asset_id):
    return _asset_action(request, asset_id, form_class=AssetConditionUpdateForm, service=update_asset_condition, title="Condición del activo actualizada.")
