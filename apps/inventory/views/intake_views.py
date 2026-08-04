from django.http import JsonResponse
from django.core.paginator import Paginator
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from apps.inventory.forms import (
    AssetIntakeCreateForm, CancelAssetIntakeForm, DepartmentIntakeDecisionForm,
    PatrimonyApprovalForm, PatrimonyObservationForm,
)
from apps.inventory.integrations import core_directory
from apps.inventory.selectors import CatalogSelectors, CoreDirectorySelectors, IntakeSelectors
from apps.inventory.services import (
    approve_patrimony_intake, cancel_intake, create_and_submit_intake,
    create_intake_draft,
    decide_department_intake, observe_patrimony_intake,
    register_approved_intake, send_to_patrimony, submit_intake,
)
from apps.security.decorators import axentra_gate_enforcer
from apps.shared.apps_config import AppIdentifier

from .common import render_inventory, run_service, selector_or_404, success
from .access import has_any_permission, intake_scope, is_inventory_root


def _detail_url(intake_id):
    return reverse("inventory:intake_detail", kwargs={"intake_id": intake_id})


def _options_response(options):
    return JsonResponse(
        {
            "options": [
                {"value": str(value), "label": label}
                for value, label in options
            ]
        }
    )


def _set_choices(field, options):
    field.choices = [("", "--- Seleccione ---"), *options]


def _apply_intake_directory_choices(form, data):
    """Carga sólo el siguiente nivel válido de la cascada organizacional."""
    site_id = str(data.get("requested_site_id", "") or "").strip()
    department_id = str(data.get("requested_department_id", "") or "").strip()
    area_id = str(data.get("requested_area_id", "") or "").strip()

    _set_choices(
        form.fields["requested_site_id"],
        [(str(item.id), item.name) for item in CoreDirectorySelectors.sites()],
    )
    departments = CoreDirectorySelectors.departments(site_id=site_id) if site_id else []
    _set_choices(
        form.fields["requested_department_id"],
        [
            (str(item.id), f"{item.code or 'SIN-CÓDIGO'} · {item.name}")
            for item in departments
        ],
    )
    areas = (
        CoreDirectorySelectors.areas(
            site_id=site_id,
            department_id=department_id,
        )
        if site_id and department_id
        else []
    )
    _set_choices(
        form.fields["requested_area_id"],
        [
            (
                str(item.id),
                f"{item.department_name} → {item.name} [{item.site_name}]",
            )
            for item in areas
        ],
    )
    users = (
        CoreDirectorySelectors.users(
            department_id=department_id,
            area_id=area_id or None,
        )
        if department_id
        else []
    )
    _set_choices(
        form.fields["proposed_custodian_id"],
        [
            (
                str(item.id),
                f"{item.display_name} · {item.email}" if item.email else item.display_name,
            )
            for item in users
        ],
    )
    return form


@axentra_gate_enforcer(
    AppIdentifier.INVENTORY,
    required_fine_permission="can_create_asset",
)
@require_GET
def intake_directory_departments_view(request):
    site_id = request.GET.get("site_id", "").strip() or None
    options = (
        (item.id, f"{item.code or 'SIN-CÓDIGO'} · {item.name}")
        for item in CoreDirectorySelectors.departments(site_id=site_id)
    )
    return _options_response(options)


@axentra_gate_enforcer(
    AppIdentifier.INVENTORY,
    required_fine_permission="can_create_asset",
)
@require_GET
def intake_directory_areas_view(request):
    site_id = request.GET.get("site_id", "").strip() or None
    department_id = request.GET.get("department_id", "").strip() or None
    options = (
        (
            item.id,
            (
                f"{item.department_code or 'SIN-CÓDIGO'} · "
                f"{item.department_name} → {item.name} "
                f"[{item.site_name}]"
            ),
        )
        for item in CoreDirectorySelectors.areas(
            site_id=site_id,
            department_id=department_id,
        )
    )
    return _options_response(options)


@axentra_gate_enforcer(
    AppIdentifier.INVENTORY,
    required_fine_permission="can_create_asset",
)
@require_GET
def intake_directory_users_view(request):
    department_id = request.GET.get("department_id", "").strip() or None
    area_id = request.GET.get("area_id", "").strip() or None
    options = (
        (
            item.id,
            (
                f"{item.display_name} · {item.email}"
                if item.email
                else item.display_name
            ),
        )
        for item in CoreDirectorySelectors.users(
            department_id=department_id,
            area_id=area_id,
        )
    )
    return _options_response(options)


@axentra_gate_enforcer(
    AppIdentifier.INVENTORY,
    required_fine_permission="can_create_asset",
)
@require_GET
def intake_models_view(request):
    manufacturer_id = request.GET.get("manufacturer_id", "").strip() or None
    models = CatalogSelectors.models(manufacturer_id=manufacturer_id) if manufacturer_id else []
    return _options_response((item.id, item.name) for item in models)


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_view_assets")
def intake_list_view(request):
    scope, scope_department_id = intake_scope(request)
    filters = {
        "q": request.GET.get("q", "").strip(),
        "status": request.GET.get("status", "").strip(),
        "department_id": request.GET.get("department", "").strip(),
        "site_id": request.GET.get("site", "").strip(),
        "area_id": request.GET.get("area", "").strip(),
        "requested_by_id": request.GET.get("requested_by", "").strip(),
        "date_from": request.GET.get("date_from", "").strip() or None,
        "date_to": request.GET.get("date_to", "").strip() or None,
    }
    tab = request.GET.get("tab", "pending").strip().lower()
    if tab not in {"pending", "history"}:
        tab = "pending"
    intakes = IntakeSelectors.listar(
        **filters,
        scope=scope,
        actor_id=request.user.pk,
        scope_department_id=scope_department_id,
    )
    department_inbox = has_any_permission(
        request, "can_view_department_intake_inbox"
    ) and scope == "DEPARTMENT"
    historical_statuses = {
        "REGISTERED", "CANCELLED", "DEPARTMENT_REJECTED",
    }
    if department_inbox and tab == "pending":
        intakes = intakes.filter(status="SUBMITTED")
    elif tab == "history":
        intakes = intakes.filter(status__in=historical_statuses)
    else:
        intakes = intakes.exclude(status__in=historical_statuses)
    page_obj = Paginator(intakes, 30).get_page(request.GET.get("page"))
    pagination_params = request.GET.copy()
    pagination_params.pop("page", None)
    directory = CoreDirectorySelectors.form_choices(
        site_id=filters["site_id"] or None,
        department_id=filters["department_id"] or None,
    )
    return render_inventory(request, page="inventory/pages/intake_list.html", content="inventory/content/intake_list_content.html", context={
        "current_inventory_view": "inventory:intake_list",
        "intakes": page_obj.object_list,
        "page_obj": page_obj,
        "pagination_query": pagination_params.urlencode(),
        "inventory_scope": scope,
        "intake_statuses": IntakeSelectors.status_choices(),
        "department_inbox": department_inbox,
        "tab": tab,
        **directory,
        **filters,
    })


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_view_assets")
def intake_detail_view(request, intake_id):
    scope, scope_department_id = intake_scope(request)
    intake = selector_or_404(lambda: IntakeSelectors.obtener(
        intake_id,
        scope=scope,
        actor_id=request.user.pk,
        department_id=scope_department_id,
    ))
    try:
        can_decide = core_directory.user_can_approve_department(
            request.user.pk,
            intake.requested_dependencia_id,
        ).allowed
    except core_directory.CoreDirectoryError:
        can_decide = False
    return render_inventory(request, page="inventory/pages/intake_detail.html", content="inventory/content/intake_detail_content.html", context={
        "current_inventory_view": "inventory:intake_list", "intake": intake,
        "can_decide_department_intake": can_decide,
    })


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_create_asset")
def intake_create_view(request):
    form = AssetIntakeCreateForm(request.POST or None)
    form = _apply_intake_directory_choices(form, request.POST if request.method == "POST" else {})
    can_submit = has_any_permission(request, "can_submit_asset_intake")
    if request.method == "POST" and form.is_valid():
        submit_now = request.POST.get("intake_action") == "submit"
        service = create_and_submit_intake if submit_now else create_intake_draft
        intake = run_service(form, lambda: service(data=form.to_dto(), actor_id=request.user.id, request=request))
        if intake:
            success(request, f"Solicitud {intake.request_number} {'enviada para aceptación' if submit_now else 'guardada como borrador'}.")
            return redirect(_detail_url(intake.id))
    return render_inventory(request, page="inventory/pages/intake_form.html", content="inventory/content/intake_form_content.html", context={
        "current_inventory_view": "inventory:intake_create", "form": form,
        "can_submit_intake": can_submit,
    }, status=422 if request.method == "POST" else 200)


def _post_transition(request, intake_id, *, form_class, callback, message):
    scope, scope_department_id = intake_scope(request)
    intake = selector_or_404(lambda: IntakeSelectors.obtener(
        intake_id,
        scope=scope,
        actor_id=request.user.pk,
        department_id=scope_department_id,
    ))
    form = form_class(request.POST)
    if not is_inventory_root(request):
        form.fields.pop("bypass_reason", None)
    if form.is_valid():
        result = run_service(form, lambda: callback(intake, form))
        if result:
            success(request, message)
            return redirect(_detail_url(intake_id))
    return render_inventory(request, page="inventory/pages/intake_action_form.html", content="inventory/content/intake_action_form_content.html", context={
        "current_inventory_view": "inventory:intake_list", "intake": intake, "form": form,
    }, status=422)


@require_POST
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_submit_asset_intake")
def intake_submit_view(request, intake_id):
    from django import forms
    class ConfirmForm(forms.Form):
        confirm = forms.BooleanField()
    return _post_transition(request, intake_id, form_class=ConfirmForm, callback=lambda i, f: submit_intake(intake_request_id=i.id, actor_id=request.user.id, request=request), message="Solicitud enviada para aceptación.")


@require_POST
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="has_access_module")
def intake_department_decision_view(request, intake_id):
    return _post_transition(request, intake_id, form_class=DepartmentIntakeDecisionForm, callback=lambda i, f: decide_department_intake(intake_request_id=i.id, actor_id=request.user.id, approve=f.to_dto().approve, comment=f.to_dto().comment, bypass_reason=f.to_dto().bypass_reason, request=request), message="Decisión departamental registrada.")


@require_POST
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_submit_asset_intake")
def intake_send_to_patrimony_view(request, intake_id):
    from django import forms
    class ConfirmForm(forms.Form):
        confirm = forms.BooleanField()
    return _post_transition(request, intake_id, form_class=ConfirmForm, callback=lambda i, f: send_to_patrimony(intake_request_id=i.id, actor_id=request.user.id, request=request), message="Solicitud enviada a Control Patrimonial.")


@require_POST
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_validate_patrimony_intake")
def intake_observe_view(request, intake_id):
    return _post_transition(request, intake_id, form_class=PatrimonyObservationForm, callback=lambda i, f: observe_patrimony_intake(intake_request_id=i.id, actor_id=request.user.id, observation=f.to_dto().observation, request=request), message="Observación patrimonial registrada.")


@require_POST
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_validate_patrimony_intake")
def intake_approve_view(request, intake_id):
    return _post_transition(request, intake_id, form_class=PatrimonyApprovalForm, callback=lambda i, f: approve_patrimony_intake(intake_request_id=i.id, actor_id=request.user.id, data=f.to_dto(), bypass_reason=f.cleaned_data.get("bypass_reason", ""), request=request), message="Solicitud aprobada por Control Patrimonial.")


@require_POST
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_register_asset")
def intake_register_view(request, intake_id):
    from django import forms
    class RegisterForm(forms.Form):
        bypass_reason = forms.CharField(required=False)
    return _post_transition(request, intake_id, form_class=RegisterForm, callback=lambda i, f: register_approved_intake(intake_request_id=i.id, actor_id=request.user.id, bypass_reason=f.cleaned_data.get("bypass_reason", ""), request=request), message="Activo registrado oficialmente.")


@require_POST
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="has_access_module")
def intake_cancel_view(request, intake_id):
    return _post_transition(request, intake_id, form_class=CancelAssetIntakeForm, callback=lambda i, f: cancel_intake(intake_request_id=i.id, actor_id=request.user.id, reason=f.to_dto().reason, request=request), message="Solicitud cancelada.")
