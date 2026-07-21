"""Vistas de expedientes secundarios de Inventory."""

from django import forms
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from apps.inventory.forms import (
    CustodyAcceptForm,
    CustodyAuthorizeForm,
    CustodyCancelForm,
    CustodyCreateForm,
    CustodyDeliverForm,
    CustodyRejectForm,
    CustodyReturnForm,
    AssetLoanAuthorizationForm,
    AssetLoanCancelForm,
    AssetLoanCreateForm,
    AssetLoanDeliveryForm,
    AssetLoanReturnForm,
    AssetLoanReturnRequestForm,
    DepartmentLoanDecisionForm,
)
from apps.inventory.integrations import core_directory

from apps.inventory.selectors import (
    AssetSelectors, CoreDirectorySelectors, CustodySelectors, DisposalSelectors, DocumentSelectors, FinancialSelectors,
    LoanSelectors, MovementSelectors, PhysicalAuditSelectors, RegistryScope,
)
from apps.security.decorators import axentra_gate_enforcer
from apps.shared.apps_config import AppIdentifier
from apps.inventory.services import (
    accept_custody_assignment,
    authorize_custody_assignment,
    cancel_custody_assignment,
    complete_custody_return,
    create_custody_assignment,
    deliver_custody_assignment,
    reject_custody_assignment,
    request_custody_return,
    submit_custody_assignment,
    authorize_asset_loan,
    cancel_asset_loan,
    create_asset_loan,
    decide_department_loan,
    deliver_asset_loan,
    request_asset_loan_return,
    return_asset_loan,
    submit_asset_loan,
)

from .access import custody_scope, department_id, has_any_permission, loan_scope, require_any_permission
from .common import apply_directory_choices, render_inventory, run_service, selector_or_404, success


def _filters(request, *names):
    return {name: request.GET.get(name, "").strip() for name in names}


def _custody_url(custody_id):
    return reverse("inventory:custody_detail", kwargs={"custody_id": custody_id})


def _custody(request, custody_id):
    scope, department_id = custody_scope(request)
    return selector_or_404(lambda: CustodySelectors.obtener(
        custody_id,
        scope=scope,
        actor_id=request.user.pk,
        department_id=department_id,
    ))


def _custody_context(request, custody):
    permissions = set(getattr(request, "axentra_permissions_list", []) or [])
    root = bool(getattr(request, "axentra_is_root", False))
    manages = root or "can_manage_custody" in permissions
    owns = custody.assigned_to_id == request.user.pk
    accepts = root or (owns and "can_accept_custody" in permissions)
    department_authority = False
    custody_department_id = getattr(custody, "dependencia_id", None)
    if custody_department_id:
        try:
            department_authority = core_directory.user_can_approve_department(
                request.user.pk,
                custody_department_id,
            ).allowed
        except core_directory.CoreDirectoryError:
            department_authority = False
    return {
        "custody": custody,
        "can_submit_custody": manages and custody.status in {"DRAFT", "REJECTED"},
        "can_authorize_custody": (manages or department_authority) and custody.status == "PENDING_AUTHORIZATION",
        "can_deliver_custody": manages and custody.status == "PENDING_ACCEPTANCE" and not custody.delivered_at,
        "can_accept_custody": accepts and custody.status == "PENDING_ACCEPTANCE" and bool(custody.delivered_at),
        "can_reject_custody": accepts and custody.status == "PENDING_ACCEPTANCE",
        "can_request_custody_return": accepts and custody.status == "ACTIVE",
        "can_complete_custody_return": manages and custody.status == "RETURN_PENDING",
        "can_cancel_custody": manages and custody.status in {"DRAFT", "PENDING_AUTHORIZATION", "REJECTED"},
    }


def _custody_options(options, **extra):
    payload = {
        "options": [
            {"value": str(value), "label": label}
            for value, label in options
        ]
    }
    payload.update(extra)
    return JsonResponse(payload)


@require_GET
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_manage_custody")
def custody_directory_departments_view(request):
    site_id = request.GET.get("site_id", "").strip() or None
    departments = CoreDirectorySelectors.departments(site_id=site_id)
    return _custody_options(
        (
            item.id,
            f"{item.code or 'SIN-CÓDIGO'} · {item.name}",
        )
        for item in departments
    )


@require_GET
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_manage_custody")
def custody_directory_areas_view(request):
    site_id = request.GET.get("site_id", "").strip() or None
    selected_department = request.GET.get("department_id", "").strip() or None
    return _custody_options(
        (
            item.id,
            f"{item.name} [{item.site_name}]",
        )
        for item in CoreDirectorySelectors.areas(
            site_id=site_id,
            department_id=selected_department,
        )
    )


@require_GET
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_manage_custody")
def custody_directory_users_view(request):
    selected_department = request.GET.get("department_id", "").strip() or None
    area_id = request.GET.get("area_id", "").strip() or None
    department = (
        core_directory.get_department(selected_department)
        if selected_department else None
    )
    options = (
        (
            item.id,
            f"{item.display_name} · {item.email}" if item.email else item.display_name,
        )
        for item in CoreDirectorySelectors.users(
            department_id=selected_department,
            area_id=area_id,
        )
    )
    return _custody_options(
        options,
        manager_user_id=(
            str(department.manager_user_id)
            if department and department.manager_user_id else ""
        ),
    )


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="has_access_module")
def custody_list_view(request):
    require_any_permission(request, "can_manage_custody", "can_accept_custody")
    f = _filters(request, "q", "status", "asset_id", "assigned_to_id", "department_id")
    scope, department_id = custody_scope(request)
    return render_inventory(request, page="inventory/pages/custody_list.html", content="inventory/content/custody_list_content.html", context={"current_inventory_view":"inventory:custody_list", "custodies":CustodySelectors.listar(**f, scope=scope, actor_id=request.user.pk, scope_department_id=department_id), "can_create_custody":has_any_permission(request, "can_manage_custody"), "custody_statuses":CustodySelectors.status_choices(), **f})


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="has_access_module")
def custody_detail_view(request, custody_id):
    require_any_permission(request, "can_manage_custody", "can_accept_custody")
    custody = _custody(request, custody_id)
    return render_inventory(request, page="inventory/pages/custody_detail.html", content="inventory/content/custody_detail_content.html", context={"current_inventory_view":"inventory:custody_list", **_custody_context(request, custody)})


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_manage_custody")
def custody_create_view(request):
    form = apply_directory_choices(CustodyCreateForm(request.POST or None))
    assets = AssetSelectors.listar_activos().filter(current_custodian__isnull=True)
    form.fields["asset_id"].choices = [("", "--- Seleccione un bien ---"), *((str(a.id), f"{a.display_inventory_number} · {a.name}") for a in assets)]
    if request.method == "POST" and form.is_valid():
        custody = run_service(form, lambda: create_custody_assignment(data=form.to_dto(), actor_id=request.user.pk, request=request))
        if custody:
            success(request, f"Resguardo {custody.folio} creado en borrador.")
            return redirect(_custody_url(custody.id))
    return render_inventory(request, page="inventory/pages/custody_form.html", content="inventory/content/custody_form_content.html", context={"current_inventory_view":"inventory:custody_list", "form":form}, status=422 if request.method == "POST" else 200)


def _custody_action(request, custody_id, form_class, callback, title):
    custody = _custody(request, custody_id)
    form = form_class(request.POST or None)
    if request.method == "POST" and form.is_valid():
        result = run_service(form, lambda: callback(custody, form))
        if result:
            success(request, title)
            return redirect(_custody_url(custody.id))
    return render_inventory(request, page="inventory/pages/custody_action_form.html", content="inventory/content/custody_action_form_content.html", context={"current_inventory_view":"inventory:custody_list", "custody":custody, "form":form, "form_title":title}, status=422 if request.method == "POST" else 200)


class _ConfirmForm(forms.Form):
    confirmar = forms.BooleanField(label="Confirmo esta operación")


@require_POST
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_manage_custody")
def custody_submit_view(request, custody_id):
    return _custody_action(request, custody_id, _ConfirmForm, lambda c, f: submit_custody_assignment(custody_id=c.id, actor_id=request.user.pk, request=request), "Resguardo enviado a autorización.")


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="has_access_module")
def custody_authorize_view(request, custody_id):
    return _custody_action(request, custody_id, CustodyAuthorizeForm, lambda c, f: authorize_custody_assignment(custody_id=c.id, actor_id=request.user.pk, data=f.to_dto(), request=request), "Resguardo autorizado.")


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_manage_custody")
def custody_deliver_view(request, custody_id):
    return _custody_action(request, custody_id, CustodyDeliverForm, lambda c, f: deliver_custody_assignment(custody_id=c.id, actor_id=request.user.pk, comment=f.cleaned_data.get("comment", ""), request=request), "Entrega física registrada.")


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_accept_custody")
def custody_accept_view(request, custody_id):
    return _custody_action(request, custody_id, CustodyAcceptForm, lambda c, f: accept_custody_assignment(custody_id=c.id, actor_id=request.user.pk, data=f.to_dto(), request=request), "Resguardo aceptado y activado.")


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_accept_custody")
def custody_reject_view(request, custody_id):
    return _custody_action(request, custody_id, CustodyRejectForm, lambda c, f: reject_custody_assignment(custody_id=c.id, actor_id=request.user.pk, data=f.to_dto(), request=request), "Resguardo rechazado.")


@require_POST
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_accept_custody")
def custody_request_return_view(request, custody_id):
    return _custody_action(request, custody_id, _ConfirmForm, lambda c, f: request_custody_return(custody_id=c.id, actor_id=request.user.pk, request=request), "Solicitud de devolución registrada.")


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_manage_custody")
def custody_complete_return_view(request, custody_id):
    return _custody_action(request, custody_id, CustodyReturnForm, lambda c, f: complete_custody_return(custody_id=c.id, actor_id=request.user.pk, data=f.to_dto(), request=request), "Devolución recibida y resguardo cerrado.")


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_manage_custody")
def custody_cancel_view(request, custody_id):
    return _custody_action(request, custody_id, CustodyCancelForm, lambda c, f: cancel_custody_assignment(custody_id=c.id, actor_id=request.user.pk, data=f.to_dto(), request=request), "Resguardo cancelado.")


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_manage_movements")
def movement_list_view(request):
    f = _filters(request, "q", "asset_id", "movement_type")
    return render_inventory(request, page="inventory/pages/movement_list.html", content="inventory/content/movement_list_content.html", context={"current_inventory_view":"inventory:movement_list", "movements":MovementSelectors.listar(**f), **f})


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_manage_movements")
def movement_detail_view(request, movement_id):
    movement = selector_or_404(lambda: MovementSelectors.obtener(movement_id))
    return render_inventory(request, page="inventory/pages/movement_detail.html", content="inventory/content/movement_detail_content.html", context={"current_inventory_view":"inventory:movement_list", "movement":movement})


def _loan_scope(request):
    return loan_scope(request)


def _loan_options(options):
    return JsonResponse({
        "options": [
            {"value": str(value), "label": label}
            for value, label in options
        ]
    })


def _loan_origin_department_id(request):
    if has_any_permission(request, "can_manage_loans"):
        return None
    return department_id(request)


@require_GET
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_request_loans")
def loan_directory_departments_view(request):
    site_id = request.GET.get("site_id", "").strip() or None
    side = request.GET.get("side", "destination").strip().lower()
    allowed_origin = _loan_origin_department_id(request) if side == "origin" else None
    departments = CoreDirectorySelectors.departments(site_id=site_id)
    if allowed_origin:
        departments = tuple(item for item in departments if item.id == allowed_origin)
    return _loan_options(
        (item.id, f"{item.code or 'SIN-CÓDIGO'} · {item.name}")
        for item in departments
    )


@require_GET
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_request_loans")
def loan_directory_areas_view(request):
    site_id = request.GET.get("site_id", "").strip() or None
    selected_department = request.GET.get("department_id", "").strip() or None
    side = request.GET.get("side", "destination").strip().lower()
    allowed_origin = _loan_origin_department_id(request) if side == "origin" else None
    if allowed_origin and str(allowed_origin) != str(selected_department):
        return _loan_options(())
    areas = CoreDirectorySelectors.areas(
        site_id=site_id,
        department_id=selected_department,
    )
    return _loan_options(
        (
            item.id,
            f"{item.department_code or 'SIN-CÓDIGO'} · {item.department_name} → {item.name} [{item.site_name}]",
        )
        for item in areas
    )


@require_GET
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_request_loans")
def loan_directory_users_view(request):
    selected_department = request.GET.get("department_id", "").strip() or None
    area_id = request.GET.get("area_id", "").strip() or None
    return _loan_options(
        (
            item.id,
            f"{item.display_name} · {item.email}" if item.email else item.display_name,
        )
        for item in CoreDirectorySelectors.users(
            department_id=selected_department,
            area_id=area_id,
        )
    )


@require_GET
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_request_loans")
def loan_directory_assets_view(request):
    selected_department = request.GET.get("department_id", "").strip() or None
    area_id = request.GET.get("area_id", "").strip() or None
    site_id = request.GET.get("site_id", "").strip() or None
    scope, scope_department_id = _loan_scope(request)
    assets = AssetSelectors.listar_activos(
        department_id=selected_department or "",
        scope=scope,
        actor_id=request.user.pk,
        scope_department_id=scope_department_id,
    ).exclude(operational_status__in=["LOANED", "IN_REPAIR", "OUT_OF_SERVICE"])
    if area_id:
        assets = assets.filter(current_area_id=area_id)
    if site_id:
        assets = assets.filter(current_sede_id=site_id)
    return _loan_options(
        (
            asset.id,
            f"{asset.display_inventory_number} · {asset.name}",
        )
        for asset in assets
    )


def _loan_url(loan_id):
    return reverse("inventory:loan_detail", kwargs={"loan_id": loan_id})


def _loan(request, loan_id):
    scope, scope_department_id = _loan_scope(request)
    return selector_or_404(lambda: LoanSelectors.obtener(
        loan_id,
        scope=scope,
        actor_id=request.user.pk,
        department_id=scope_department_id,
    ))


def _loan_context(request, loan):
    manages = has_any_permission(request, "can_manage_loans")
    authorizes = has_any_permission(request, "can_authorize_loans")
    requests = has_any_permission(request, "can_request_loans")
    own_request = loan.requested_by_id == request.user.pk
    own_receipt = loan.borrower_id == request.user.pk
    destination_matches = department_id(request) == loan.destination_dependencia_id
    return {
        "loan": loan,
        "can_submit_loan": requests and own_request and loan.status in {"DRAFT", "REJECTED"},
        "can_decide_department_loan": authorizes and destination_matches and loan.status == "REQUESTED" and not loan.external_borrower,
        "can_authorize_loan": manages and (loan.status == "DEPARTMENT_APPROVED" or (loan.external_borrower and loan.status == "REQUESTED")),
        "can_deliver_loan": manages and loan.status == "AUTHORIZED",
        "can_request_loan_return": (manages or own_request or own_receipt) and loan.status in {"DELIVERED", "OVERDUE"},
        "can_receive_loan_return": manages and loan.status in {"DELIVERED", "OVERDUE", "RETURN_PENDING"},
        "can_cancel_loan": (manages or own_request) and loan.status in {"DRAFT", "REQUESTED", "REJECTED"},
    }


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="has_access_module")
def loan_list_view(request):
    require_any_permission(
        request,
        "can_request_loans",
        "can_manage_loans",
        "can_authorize_loans",
    )
    f = _filters(request, "q", "status", "asset_id", "borrower_id", "bucket")
    f["overdue"] = request.GET.get("overdue") == "1"
    scope, scope_department_id = _loan_scope(request)
    return render_inventory(request, page="inventory/pages/loan_list.html", content="inventory/content/loan_list_content.html", context={"current_inventory_view":"inventory:loan_list", "loans":LoanSelectors.listar(**f, active_only=True, scope=scope, actor_id=request.user.pk, scope_department_id=scope_department_id), "loan_summary":LoanSelectors.dashboard_metrics(scope=scope, actor_id=request.user.pk, department_id=scope_department_id), "can_create_full_loan":has_any_permission(request, "can_manage_loans"), "show_department_tabs":scope == RegistryScope.DEPARTMENT, "show_global_tabs":scope == RegistryScope.GLOBAL, "loan_statuses":LoanSelectors.status_choices(), **f})


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="has_access_module")
def loan_detail_view(request, loan_id):
    require_any_permission(request, "can_request_loans", "can_manage_loans", "can_authorize_loans")
    scope, scope_department_id = _loan_scope(request)
    loan = selector_or_404(lambda: LoanSelectors.obtener(loan_id, scope=scope, actor_id=request.user.pk, department_id=scope_department_id))
    return render_inventory(request, page="inventory/pages/loan_detail.html", content="inventory/content/loan_detail_content.html", context={"current_inventory_view":"inventory:loan_list", **_loan_context(request, loan)})


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_manage_loans")
def loan_create_view(request):
    form = apply_directory_choices(AssetLoanCreateForm(request.POST or None))
    scope, scope_department_id = _loan_scope(request)
    selected_origin_department = (
        request.POST.get("origin_department_id", "").strip()
        if request.method == "POST" else ""
    )
    selected_origin_area = (
        request.POST.get("origin_area_id", "").strip()
        if request.method == "POST" else ""
    )
    selected_origin_site = (
        request.POST.get("origin_site_id", "").strip()
        if request.method == "POST" else ""
    )
    fixed_origin_department = _loan_origin_department_id(request)
    if fixed_origin_department:
        department = CoreDirectorySelectors.departments()
        department = next(
            (item for item in department if item.id == fixed_origin_department),
            None,
        )
        origin_department_choices = [
            ("", "--- Seleccione dependencia ---"),
        ]
        if department:
            origin_department_choices.append((
                str(department.id),
                f"{department.code or 'SIN-CÓDIGO'} · {department.name}",
            ))
        form.fields["origin_department_id"].choices = origin_department_choices
        form.fields["origin_department_id"].initial = str(fixed_origin_department)
        selected_origin_department = selected_origin_department or str(fixed_origin_department)
        origin_areas = CoreDirectorySelectors.areas(
            department_id=fixed_origin_department,
            site_id=selected_origin_site or None,
        )
        form.fields["origin_area_id"].choices = [
            ("", "--- Seleccione área ---"),
            *((str(item.id), f"{item.name} [{item.site_name}]") for item in origin_areas),
        ]
    assets = AssetSelectors.listar_activos(
        department_id=selected_origin_department,
        scope=scope,
        actor_id=request.user.pk,
        scope_department_id=scope_department_id,
    ).exclude(operational_status__in=["LOANED", "IN_REPAIR", "OUT_OF_SERVICE"])
    if selected_origin_area:
        assets = assets.filter(current_area_id=selected_origin_area)
    if selected_origin_site:
        assets = assets.filter(current_sede_id=selected_origin_site)
    form.fields["asset_id"].choices = [("", "--- Seleccione un bien ---"), *((str(asset.id), f"{asset.display_inventory_number} · {asset.name}") for asset in assets)]
    if request.method == "POST" and form.is_valid():
        loan = run_service(form, lambda: create_asset_loan(data=form.to_dto(), actor_id=request.user.pk, request=request))
        if loan:
            success(request, f"Préstamo {loan.folio} creado en borrador.")
            return redirect(_loan_url(loan.id))
    return render_inventory(request, page="inventory/pages/loan_form.html", content="inventory/content/loan_form_content.html", context={"current_inventory_view":"inventory:loan_list", "form":form}, status=422 if request.method == "POST" else 200)


def _loan_action(request, loan_id, form_class, callback, title):
    loan = _loan(request, loan_id)
    form = apply_directory_choices(form_class(request.POST or None))
    if request.method == "POST" and form.is_valid():
        result = run_service(form, lambda: callback(loan, form))
        if result:
            success(request, title)
            return redirect(_loan_url(loan.id))
    return render_inventory(request, page="inventory/pages/loan_action_form.html", content="inventory/content/loan_action_form_content.html", context={"current_inventory_view":"inventory:loan_list", "loan":loan, "form":form, "form_title":title}, status=422 if request.method == "POST" else 200)


@require_POST
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_request_loans")
def loan_submit_view(request, loan_id):
    return _loan_action(request, loan_id, _ConfirmForm, lambda loan, form: submit_asset_loan(loan_id=loan.id, actor_id=request.user.pk, request=request), "Préstamo enviado a la dependencia receptora.")


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_authorize_loans")
def loan_department_decision_view(request, loan_id):
    loan = _loan(request, loan_id)
    form = apply_directory_choices(DepartmentLoanDecisionForm(request.POST or None))
    areas = CoreDirectorySelectors.areas(department_id=loan.destination_dependencia_id)
    users = CoreDirectorySelectors.users(department_id=loan.destination_dependencia_id)
    form.fields["destination_area_id"].choices = [
        ("", "--- Seleccione el área receptora ---"),
        *((str(item.id), f"{item.name} [{item.site_name}]") for item in areas),
    ]
    form.fields["borrower_id"].choices = [
        ("", "--- Sin responsable individual ---"),
        *((str(item.id), item.display_name) for item in users),
    ]
    if request.method == "POST" and form.is_valid():
        result = run_service(
            form,
            lambda: decide_department_loan(
                loan_id=loan.id,
                actor_id=request.user.pk,
                data=form.to_dto(),
                request=request,
            ),
        )
        if result:
            success(request, "Decisión de la dependencia registrada.")
            return redirect(_loan_url(loan.id))
    return render_inventory(
        request,
        page="inventory/pages/loan_action_form.html",
        content="inventory/content/loan_action_form_content.html",
        context={
            "current_inventory_view": "inventory:loan_list",
            "loan": loan,
            "form": form,
            "form_title": "Aceptar o rechazar préstamo",
        },
        status=422 if request.method == "POST" else 200,
    )


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_manage_loans")
def loan_authorize_view(request, loan_id):
    return _loan_action(request, loan_id, AssetLoanAuthorizationForm, lambda loan, form: authorize_asset_loan(loan_id=loan.id, actor_id=request.user.pk, data=form.to_dto(), request=request), "Decisión patrimonial registrada.")


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_manage_loans")
def loan_deliver_view(request, loan_id):
    return _loan_action(request, loan_id, AssetLoanDeliveryForm, lambda loan, form: deliver_asset_loan(loan_id=loan.id, actor_id=request.user.pk, data=form.to_dto(), request=request), "Entrega del préstamo registrada.")


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_request_loans")
def loan_request_return_view(request, loan_id):
    return _loan_action(request, loan_id, AssetLoanReturnRequestForm, lambda loan, form: request_asset_loan_return(loan_id=loan.id, actor_id=request.user.pk, data=form.to_dto(), request=request), "Solicitud de devolución registrada.")


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_manage_loans")
def loan_return_view(request, loan_id):
    return _loan_action(request, loan_id, AssetLoanReturnForm, lambda loan, form: return_asset_loan(loan_id=loan.id, actor_id=request.user.pk, data=form.to_dto(), request=request), "Devolución recibida y préstamo cerrado.")


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="has_access_module")
def loan_cancel_view(request, loan_id):
    return _loan_action(request, loan_id, AssetLoanCancelForm, lambda loan, form: cancel_asset_loan(loan_id=loan.id, actor_id=request.user.pk, data=form.to_dto(), request=request), "Préstamo cancelado.")


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_manage_disposals")
def disposal_list_view(request):
    f = _filters(request, "q", "status", "asset_id", "reason")
    return render_inventory(request, page="inventory/pages/disposal_list.html", content="inventory/content/disposal_list_content.html", context={"current_inventory_view":"inventory:disposal_list", "disposals":DisposalSelectors.listar(**f), **f})


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_manage_disposals")
def disposal_detail_view(request, disposal_id):
    disposal = selector_or_404(lambda: DisposalSelectors.obtener(disposal_id))
    return render_inventory(request, page="inventory/pages/disposal_detail.html", content="inventory/content/disposal_detail_content.html", context={"current_inventory_view":"inventory:disposal_list", "disposal":disposal, "documents":DocumentSelectors.documents(owner_type="DISPOSAL_REQUEST", owner_id=disposal.id)})


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_manage_documents")
def document_list_view(request):
    f = _filters(request, "owner_type", "owner_id", "document_type", "validation_status", "q")
    return render_inventory(request, page="inventory/pages/document_list.html", content="inventory/content/document_list_content.html", context={"current_inventory_view":"inventory:document_list", "documents":DocumentSelectors.documents(**f), **f})


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_manage_physical_audits")
def physical_audit_list_view(request):
    f = _filters(request, "q", "status", "department_id")
    return render_inventory(request, page="inventory/pages/physical_audit_list.html", content="inventory/content/physical_audit_list_content.html", context={"current_inventory_view":"inventory:physical_audit_list", "audit_sessions":PhysicalAuditSelectors.sessions(**f), **f})


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_manage_physical_audits")
def physical_audit_detail_view(request, session_id):
    session = selector_or_404(lambda: PhysicalAuditSelectors.session_detail(session_id))
    return render_inventory(request, page="inventory/pages/physical_audit_detail.html", content="inventory/content/physical_audit_detail_content.html", context={"current_inventory_view":"inventory:physical_audit_list", "audit_session":session, "result_totals":PhysicalAuditSelectors.result_totals(session.id)})


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_view_financials")
def financial_dashboard_view(request):
    return render_inventory(request, page="inventory/pages/financial_dashboard.html", content="inventory/content/financial_dashboard_content.html", context={
        "current_inventory_view":"inventory:financial_dashboard",
        "policies":FinancialSelectors.depreciation_policies(),
        "runs":FinancialSelectors.depreciation_runs()[:20],
        "exports":FinancialSelectors.export_batches()[:20],
        "reconciliations":FinancialSelectors.reconciliations()[:20],
    })
