# apps/inventory/views/intake_views.py

from django import forms
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.http import (
    require_POST,
    require_http_methods,
)

from apps.inventory.forms import (
    AssetIntakeCreateForm,
    CancelAssetIntakeForm,
    DepartmentIntakeDecisionForm,
    PatrimonyApprovalForm,
    PatrimonyObservationForm,
)
from apps.inventory.selectors import IntakeSelectors
from apps.inventory.services import (
    approve_patrimony_intake,
    cancel_intake,
    create_intake_draft,
    decide_department_intake,
    observe_patrimony_intake,
    register_approved_intake,
    send_to_patrimony,
    submit_intake,
)
from apps.security.decorators import axentra_gate_enforcer
from apps.shared.apps_config import AppIdentifier

from .common import (
    apply_directory_choices,
    render_inventory,
    run_service,
    selector_or_404,
    success,
)


class ConfirmTransitionForm(forms.Form):
    """Confirmación explícita para transiciones sin datos adicionales."""

    confirm = forms.BooleanField(
        label="Confirmo que deseo continuar",
        required=True,
    )


class RegisterApprovedIntakeForm(forms.Form):
    """El bypass sólo será obligatorio si el servicio detecta que se usó."""

    bypass_reason = forms.CharField(
        label="Justificación de bypass",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )


def _detail_url(intake_id):
    return reverse(
        "inventory:intake_detail",
        kwargs={"intake_id": intake_id},
    )


def _list_filters(request):
    return {
        "q": request.GET.get("q", "").strip(),
        "status": request.GET.get("status", "").strip(),
        "department_id": request.GET.get("department", "").strip(),
        "scope": request.GET.get("scope", "").strip(),
    }


@axentra_gate_enforcer(
    AppIdentifier.INVENTORY,
    required_fine_permission="can_view_assets",
)
def intake_list_view(request):
    filters = _list_filters(request)
    intakes = IntakeSelectors.listar(
        actor_id=request.user.id,
        **filters,
    )

    return render_inventory(
        request,
        page="inventory/pages/intake_list.html",
        content="inventory/content/intake_list_content.html",
        context={
            "current_inventory_view": "inventory:intake_list",
            "intakes": intakes,
            **filters,
        },
    )


@axentra_gate_enforcer(
    AppIdentifier.INVENTORY,
    required_fine_permission="can_view_assets",
)
def intake_detail_view(request, intake_id):
    intake = selector_or_404(
        lambda: IntakeSelectors.obtener(
            actor_id=request.user.id,
            request_id=intake_id,
        )
    )

    return render_inventory(
        request,
        page="inventory/pages/intake_detail.html",
        content="inventory/content/intake_detail_content.html",
        context={
            "current_inventory_view": "inventory:intake_list",
            "intake": intake,
        },
    )


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(
    AppIdentifier.INVENTORY,
    required_fine_permission="can_create_asset",
)
def intake_create_view(request):
    form = AssetIntakeCreateForm(request.POST or None)
    form = apply_directory_choices(form)

    if request.method == "POST" and form.is_valid():
        intake = run_service(
            form,
            lambda: create_intake_draft(
                data=form.to_dto(),
                actor_id=request.user.id,
                request=request,
            ),
        )

        if intake:
            success(
                request,
                f"Solicitud {intake.request_number} creada en borrador.",
            )
            return redirect(_detail_url(intake.id))

    return render_inventory(
        request,
        page="inventory/pages/intake_form.html",
        content="inventory/content/intake_form_content.html",
        context={
            "current_inventory_view": "inventory:intake_create",
            "form": form,
        },
        status=422 if request.method == "POST" else 200,
    )


def _post_transition(
    request,
    intake_id,
    *,
    form_class,
    callback,
    message,
):
    """Ejecuta una transición y conserva los errores dentro del formulario."""

    intake = selector_or_404(
        lambda: IntakeSelectors.obtener(
            actor_id=request.user.id,
            request_id=intake_id,
        )
    )
    form = form_class(request.POST)

    if form.is_valid():
        result = run_service(
            form,
            lambda: callback(intake, form),
        )

        if result:
            success(request, message)
            return redirect(_detail_url(intake_id))

    return render_inventory(
        request,
        page="inventory/pages/intake_action_form.html",
        content="inventory/content/intake_action_form_content.html",
        context={
            "current_inventory_view": "inventory:intake_list",
            "intake": intake,
            "form": form,
        },
        status=422,
    )


@require_POST
@axentra_gate_enforcer(
    AppIdentifier.INVENTORY,
    required_fine_permission="can_submit_asset_intake",
)
def intake_submit_view(request, intake_id):
    return _post_transition(
        request,
        intake_id,
        form_class=ConfirmTransitionForm,
        callback=lambda intake, _form: submit_intake(
            intake_request_id=intake.id,
            actor_id=request.user.id,
            request=request,
        ),
        message="Solicitud enviada para aceptación departamental.",
    )


@require_POST
@axentra_gate_enforcer(
    AppIdentifier.INVENTORY,
    required_fine_permission="can_approve_department_intake",
)
def intake_department_decision_view(request, intake_id):
    def execute(intake, form):
        data = form.to_dto()
        return decide_department_intake(
            intake_request_id=intake.id,
            actor_id=request.user.id,
            approve=data.approve,
            comment=data.comment,
            bypass_reason=data.bypass_reason,
            request=request,
        )

    return _post_transition(
        request,
        intake_id,
        form_class=DepartmentIntakeDecisionForm,
        callback=execute,
        message="Decisión departamental registrada.",
    )


@require_POST
@axentra_gate_enforcer(
    AppIdentifier.INVENTORY,
    # Esta transición admite can_submit_asset_intake o
    # can_approve_department_intake. El gate no expresa OR; el servicio sí
    # valida ambos permisos y el alcance de la dependencia.
    required_fine_permission="has_access_module",
)
def intake_send_to_patrimony_view(request, intake_id):
    return _post_transition(
        request,
        intake_id,
        form_class=ConfirmTransitionForm,
        callback=lambda intake, _form: send_to_patrimony(
            intake_request_id=intake.id,
            actor_id=request.user.id,
            request=request,
        ),
        message="Solicitud enviada a Control Patrimonial.",
    )


@require_POST
@axentra_gate_enforcer(
    AppIdentifier.INVENTORY,
    required_fine_permission="can_validate_patrimony_intake",
)
def intake_observe_view(request, intake_id):
    def execute(intake, form):
        data = form.to_dto()
        return observe_patrimony_intake(
            intake_request_id=intake.id,
            actor_id=request.user.id,
            observation=data.observation,
            request=request,
        )

    return _post_transition(
        request,
        intake_id,
        form_class=PatrimonyObservationForm,
        callback=execute,
        message="Observación patrimonial registrada.",
    )


@require_POST
@axentra_gate_enforcer(
    AppIdentifier.INVENTORY,
    required_fine_permission="can_validate_patrimony_intake",
)
def intake_approve_view(request, intake_id):
    def execute(intake, form):
        return approve_patrimony_intake(
            intake_request_id=intake.id,
            actor_id=request.user.id,
            data=form.to_dto(),
            bypass_reason=form.cleaned_data.get("bypass_reason", ""),
            request=request,
        )

    return _post_transition(
        request,
        intake_id,
        form_class=PatrimonyApprovalForm,
        callback=execute,
        message="Solicitud aprobada por Control Patrimonial.",
    )


@require_POST
@axentra_gate_enforcer(
    AppIdentifier.INVENTORY,
    required_fine_permission="can_register_asset",
)
def intake_register_view(request, intake_id):
    return _post_transition(
        request,
        intake_id,
        form_class=RegisterApprovedIntakeForm,
        callback=lambda intake, form: register_approved_intake(
            intake_request_id=intake.id,
            actor_id=request.user.id,
            bypass_reason=form.cleaned_data.get("bypass_reason", ""),
            request=request,
        ),
        message="Activo registrado oficialmente.",
    )


@require_POST
@axentra_gate_enforcer(
    AppIdentifier.INVENTORY,
    # El creador puede cancelar etapas tempranas aunque no tenga can_edit_asset.
    # La autorización final se aplica dentro de cancel_intake.
    required_fine_permission="has_access_module",
)
def intake_cancel_view(request, intake_id):
    def execute(intake, form):
        data = form.to_dto()
        return cancel_intake(
            intake_request_id=intake.id,
            actor_id=request.user.id,
            reason=data.reason,
            request=request,
        )

    return _post_transition(
        request,
        intake_id,
        form_class=CancelAssetIntakeForm,
        callback=execute,
        message="Solicitud cancelada.",
    )


__all__ = [
    "intake_approve_view",
    "intake_cancel_view",
    "intake_create_view",
    "intake_department_decision_view",
    "intake_detail_view",
    "intake_list_view",
    "intake_observe_view",
    "intake_register_view",
    "intake_send_to_patrimony_view",
    "intake_submit_view",
]

