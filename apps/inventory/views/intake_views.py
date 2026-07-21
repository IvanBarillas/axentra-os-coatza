from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from apps.inventory.forms import (
    AssetIntakeCreateForm, CancelAssetIntakeForm, DepartmentIntakeDecisionForm,
    PatrimonyApprovalForm, PatrimonyObservationForm,
)
from apps.inventory.integrations import core_directory
from apps.inventory.selectors import CoreDirectorySelectors, IntakeSelectors
from apps.inventory.services import (
    approve_patrimony_intake, cancel_intake, create_and_submit_intake,
    create_intake_draft,
    decide_department_intake, observe_patrimony_intake,
    register_approved_intake, send_to_patrimony, submit_intake,
)
from apps.security.decorators import axentra_gate_enforcer
from apps.shared.apps_config import AppIdentifier

from .common import apply_directory_choices, render_inventory, run_service, selector_or_404, success
from .access import has_any_permission, intake_scope


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


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_view_assets")
def intake_list_view(request):
    scope, scope_department_id = intake_scope(request)
    filters = {
        "q": request.GET.get("q", "").strip(),
        "status": request.GET.get("status", "").strip(),
        "department_id": request.GET.get("department", "").strip(),
    }
    return render_inventory(request, page="inventory/pages/intake_list.html", content="inventory/content/intake_list_content.html", context={
        "current_inventory_view": "inventory:intake_list",
        "intakes": IntakeSelectors.listar(
            **filters,
            scope=scope,
            actor_id=request.user.pk,
            scope_department_id=scope_department_id,
        ),
        "inventory_scope": scope,
        "intake_statuses": IntakeSelectors.status_choices(),
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
    form = apply_directory_choices(AssetIntakeCreateForm(request.POST or None))
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
