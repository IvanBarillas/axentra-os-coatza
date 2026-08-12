"""Vistas de expedientes secundarios de Inventory."""

from django import forms
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import FileResponse, JsonResponse
from django.db.models import Q
from django.shortcuts import redirect, render
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
    AssetLocationChangeForm,
    AssetReassignmentForm,
    AssetTransferForm,
    DisposalCancelForm,
    DisposalExecuteForm,
    DisposalFinalApprovalForm,
    DisposalRequestCreateForm,
    DisposalStageResolutionForm,
    DisposalSubmitForm,
    DisposalStageDocumentUploadForm,
    DocumentValidationResolveForm,
    ContextDocumentUploadForm,
    PhysicalAuditCancelForm,
    PhysicalAuditCloseForm,
    PhysicalAuditCreateForm,
    PhysicalAuditFreezeForm,
    PhysicalAuditNotFoundForm,
    PhysicalAuditReconcileForm,
    PhysicalAuditScanForm,
    PhysicalAuditStartForm,
    PhysicalAuditUnlistedItemForm,
    PhysicalAuditDocumentUploadForm,
    PhysicalAuditPhotoUploadForm,
)
from apps.inventory.integrations import core_directory
from apps.inventory.documents import (
    get_acknowledgement_spec,
    get_acknowledgement_state,
)
from apps.inventory.models import (
    AssetDocument,
    AssetLoan,
    AssetLoanStatus,
    CustodyStatus,
    AssetMovementRequest,
    AssetMovementRequestStatus,
    AssetPhoto,
    CustodyAssignment,
    DisposalStageDocumentRequirement,
    DisposalRequest,
    DisposalStatus,
    DocumentType,
    DocumentValidationStatus,
    InventoryDocumentOwnerType,
    CustodyDocument,
    CustodyDocumentStatus,
    CustodyDocumentType,
    MovementType,
)

from apps.inventory.selectors import (
    AssetSelectors, CoreDirectorySelectors, CustodySelectors, DisposalSelectors, DocumentSelectors, FinancialSelectors, IntakeSelectors,
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
    cancel_disposal,
    create_disposal_request,
    execute_disposal,
    finalize_disposal_approval,
    resolve_disposal_stage,
    submit_disposal_request,
    resolve_inventory_document,
    upload_disposal_stage_document,
    upload_inventory_document,
    begin_physical_audit_reconciliation,
    cancel_physical_audit,
    close_physical_audit,
    create_physical_audit,
    freeze_physical_audit,
    mark_audit_item_not_found,
    mark_pending_audit_items_not_found,
    reconcile_physical_audit_item,
    register_unlisted_audit_item,
    scan_physical_audit_item,
    start_physical_audit,
    upload_physical_audit_document,
    upload_physical_audit_photo,
    build_audit_request_context,
    accept_movement_destination,
    approve_movement_origin,
    can_authorize_department_movement,
    create_movement_request,
    execute_approved_movement,
)

from .access import asset_scope, custody_scope, department_id, disposal_scope, has_any_permission, intake_scope, is_inventory_root, loan_scope, movement_scope, physical_audit_scope, require_any_permission
from .common import apply_directory_choices, render_inventory, run_service, selector_or_404, success


def _filters(request, *names):
    return {name: request.GET.get(name, "").strip() for name in names}


def _registry_filter_context(filters, scope, scope_department_id):
    """Limita filtros institucionales al alcance efectivo del operador."""
    is_global = scope == RegistryScope.GLOBAL
    is_department = scope == RegistryScope.DEPARTMENT

    if not is_global:
        filters["site_id"] = ""
        filters["department_id"] = ""
    if scope == RegistryScope.OWN:
        filters["area_id"] = ""
        filters["user_id"] = ""
        filters["borrower_id"] = ""
        filters["requested_by_id"] = ""

    if is_global:
        directory = CoreDirectorySelectors.form_choices(
            site_id=filters.get("site_id") or None,
            department_id=filters.get("department_id") or None,
        )
    elif is_department and scope_department_id:
        directory = {
            "site_choices": [],
            "department_choices": [],
            "area_choices": [
                (str(item.id), f"{item.name} [{item.site_name}]")
                for item in CoreDirectorySelectors.areas(
                    department_id=scope_department_id,
                )
            ],
            "user_choices": [
                (str(item.id), item.display_name)
                for item in CoreDirectorySelectors.users(
                    department_id=scope_department_id,
                )
            ],
        }
    else:
        directory = {
            "site_choices": [], "department_choices": [],
            "area_choices": [], "user_choices": [],
        }

    return {
        **directory,
        "is_global_inventory_scope": is_global,
        "is_department_inventory_scope": is_department,
    }


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
        # Un resguardo activo es un instrumento de control patrimonial, no un
        # préstamo. Sólo Patrimonio puede iniciar su retiro o cierre.
        # El retiro se formaliza exclusivamente mediante una constancia de
        # liberación (individual o masiva), nunca desde el resguardo aislado.
        "can_request_custody_return": False,
        "can_complete_custody_return": False,
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
@axentra_gate_enforcer(
    AppIdentifier.INVENTORY,
    required_fine_permission="can_manage_custody",
)
def custody_asset_options_view(request):
    query = request.GET.get("q", "").strip()
    asset_id = request.GET.get("asset_id", "").strip()

    assets = (
        AssetSelectors.listar_activos(q=query)
        .filter(current_custodian__isnull=True)
        .exclude(
            custody_assignments__is_deleted=False,
            custody_assignments__status__in=(
                CustodyStatus.PENDING_AUTHORIZATION,
                CustodyStatus.PENDING_ACCEPTANCE,
                CustodyStatus.ACTIVE,
                CustodyStatus.RETURN_PENDING,
            ),
        )
        .distinct()
    )

    if asset_id:
        assets = assets.filter(pk=asset_id)

    options = []
    for asset in assets[:30]:
        options.append({
            "value": str(asset.id),
            "label": (
                f"{asset.display_inventory_number} · {asset.name}"
                + (
                    f" · Serie {asset.serial_number}"
                    if asset.serial_number else ""
                )
            ),
            "folio": asset.display_inventory_number,
            "name": asset.name,
            "serial_number": asset.serial_number or "Sin serie",
            "site_id": (
                str(asset.current_sede_id)
                if asset.current_sede_id else ""
            ),
            "site_name": (
                asset.current_sede.nombre
                if asset.current_sede_id else "Sin sede"
            ),
            "department_id": (
                str(asset.current_dependencia_id)
                if asset.current_dependencia_id else ""
            ),
            "department_name": (
                asset.current_dependencia.nombre
                if asset.current_dependencia_id else "Sin dependencia"
            ),
            "area_id": (
                str(asset.current_area_id)
                if asset.current_area_id else ""
            ),
            "area_name": (
                asset.current_area.nombre
                if asset.current_area_id else "Sin área"
            ),
        })

    return JsonResponse({"options": options})


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
@axentra_gate_enforcer(
    AppIdentifier.INVENTORY,
    required_fine_permission="can_manage_custody",
)
def custody_directory_users_view(request):
    selected_department = (
        request.GET.get("department_id", "").strip() or None
    )
    area_id = request.GET.get("area_id", "").strip() or None

    department = (
        core_directory.get_department(selected_department)
        if selected_department else None
    )

    users = list(
        CoreDirectorySelectors.users(
            department_id=selected_department,
            area_id=area_id,
        )
    )

    manager_user_id = (
        department.manager_user_id
        if department and department.manager_user_id else None
    )
    manager_user_label = ""

    if manager_user_id:
        try:
            manager = core_directory.get_user_identity(manager_user_id)
            manager_user_label = (
                f"{manager.display_name} · {manager.normalized_email}"
                if manager.normalized_email
                else manager.display_name
            )
        except core_directory.CoreDirectoryError:
            manager_user_id = None

    options = [
        (
            item.id,
            (
                f"{item.display_name} · {item.email}"
                if item.email else item.display_name
            ),
        )
        for item in users
    ]

    return _custody_options(
        options,
        manager_user_id=(
            str(manager_user_id) if manager_user_id else ""
        ),
        manager_user_label=manager_user_label,
    )


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="has_access_module")
def custody_list_view(request):
    require_any_permission(request, "can_manage_custody", "can_accept_custody")
    f = _filters(request, "q", "status", "asset_id", "assigned_to_id", "department_id", "site_id", "area_id", "date_from", "date_to")
    scope, department_id = custody_scope(request)
    is_global_scope = scope == "GLOBAL"
    is_department_scope = scope == "DEPARTMENT"
    permissions = set(getattr(request, "axentra_permissions_list", []) or [])
    is_patrimony_custody_operator = bool(
        getattr(request, "axentra_is_root", False)
        or {
            "can_manage_custody",
            "can_review_patrimony_disposal",
        }.issubset(permissions)
    )
    if not is_global_scope:
        f["site_id"] = ""
        f["department_id"] = ""
    if scope == "OWN":
        f["area_id"] = ""
        f["assigned_to_id"] = ""
    tab = request.GET.get("tab", "current").strip().lower()
    if tab not in {"current", "history", "unassigned", "releases"}:
        tab = "current"
    if tab == "releases" and not is_patrimony_custody_operator:
        tab = "current"
    queryset = CustodySelectors.listar(**f, scope=scope, actor_id=request.user.pk, scope_department_id=department_id)
    historical = {CustodyStatus.RETURNED, CustodyStatus.CANCELLED}
    assets_without_custody = None
    pending_release_documents = CustodyDocument.objects.filter(
        document_type=CustodyDocumentType.RELEASE,
        status__in={
            CustodyDocumentStatus.DRAFT,
            CustodyDocumentStatus.IN_PROCESS,
        },
        is_deleted=False,
    )
    pending_release_count = (
        pending_release_documents.count()
        if is_patrimony_custody_operator else 0
    )
    if tab == "releases":
        if f["q"]:
            pending_release_documents = pending_release_documents.filter(
                Q(folio__icontains=f["q"])
                | Q(department_name_snapshot__icontains=f["q"])
                | Q(assigned_to_name_snapshot__icontains=f["q"])
                | Q(items__inventory_number_snapshot__icontains=f["q"])
                | Q(items__asset_name_snapshot__icontains=f["q"])
            )
        if f["department_id"]:
            pending_release_documents = pending_release_documents.filter(
                department_id=f["department_id"],
            )
        if f["date_from"]:
            pending_release_documents = pending_release_documents.filter(
                prepared_at__date__gte=f["date_from"],
            )
        if f["date_to"]:
            pending_release_documents = pending_release_documents.filter(
                prepared_at__date__lte=f["date_to"],
            )
        page_obj = Paginator(
            pending_release_documents.distinct().order_by("-prepared_at"),
            30,
        ).get_page(request.GET.get("page"))
    elif tab == "unassigned" and has_any_permission(request, "can_manage_custody"):
        occupied_asset_ids = CustodyAssignment.objects.filter(
            is_deleted=False,
            status__in={
                CustodyStatus.DRAFT,
                CustodyStatus.PENDING_AUTHORIZATION,
                CustodyStatus.PENDING_ACCEPTANCE,
                CustodyStatus.ACTIVE,
                CustodyStatus.RETURN_PENDING,
            },
        ).values_list("asset_id", flat=True)
        assets_without_custody = AssetSelectors.listar_activos(
            q=f["q"],
            site_id=f["site_id"],
            department_id=f["department_id"],
            area_id=f["area_id"],
            capitalizable="",
            scope="GLOBAL",
        ).filter(
            patrimonial_status="ACTIVE",
        ).exclude(id__in=occupied_asset_ids)
        page_obj = Paginator(assets_without_custody, 30).get_page(
            request.GET.get("page")
        )
    else:
        queryset = queryset.filter(status__in=historical) if tab == "history" else queryset.exclude(status__in=historical)
        page_obj = Paginator(queryset, 30).get_page(request.GET.get("page"))
    pagination_params = request.GET.copy(); pagination_params.pop("page", None)
    if is_global_scope:
        directory = CoreDirectorySelectors.form_choices(
            site_id=f["site_id"] or None,
            department_id=f["department_id"] or None,
        )
    elif is_department_scope:
        directory = {
            "site_choices": [],
            "department_choices": [],
            "area_choices": [
                (str(item.id), item.name)
                for item in CoreDirectorySelectors.areas(
                    department_id=department_id,
                )
            ],
            "user_choices": [
                (str(item.id), item.display_name)
                for item in CoreDirectorySelectors.users(
                    department_id=department_id,
                )
            ],
        }
    else:
        directory = {
            "site_choices": [], "department_choices": [],
            "area_choices": [], "user_choices": [],
        }
    return render_inventory(request, page="inventory/pages/custody_list.html", content="inventory/content/custody_list_content.html", context={"current_inventory_view":"inventory:custody_list", "custodies":(page_obj.object_list if tab in {"current", "history"} else []), "assets_without_custody":(page_obj.object_list if tab == "unassigned" else []), "pending_release_documents":(page_obj.object_list if tab == "releases" else []), "pending_release_count":pending_release_count, "page_obj":page_obj, "pagination_query":pagination_params.urlencode(), "tab":tab, "is_global_inventory_scope":is_global_scope, "is_department_inventory_scope":is_department_scope, "is_patrimony_custody_operator":is_patrimony_custody_operator, "can_create_custody":has_any_permission(request, "can_manage_custody"), "custody_statuses":CustodySelectors.status_choices(), **directory, **f})


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="has_access_module")
def custody_detail_view(request, custody_id):
    require_any_permission(request, "can_manage_custody", "can_accept_custody")
    custody = _custody(request, custody_id)
    return render_inventory(request, page="inventory/pages/custody_detail.html", content="inventory/content/custody_detail_content.html", context={"current_inventory_view":"inventory:custody_list", **_custody_context(request, custody)})


def _document_generated_type(request):
    """Conserva el tipo de acuse entre la apertura y el POST del formulario."""
    generated_type = (
        request.GET.get("ack_for", "").strip().upper()
        or request.POST.get("ack_for", "").strip().upper()
        or request.GET.get("document_type", "").strip().upper()
        or request.POST.get("document_type", "").strip().upper()
    )
    return {
        DocumentType.SIGNED_LOAN_RECEIPT: DocumentType.LOAN_RECEIPT,
        DocumentType.SIGNED_RETURN_RECEIPT: DocumentType.RETURN_RECEIPT,
    }.get(generated_type, generated_type)


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(
    AppIdentifier.INVENTORY,
    required_fine_permission="can_manage_custody",
)
def custody_create_view(request):
    selected_asset_id = (
        request.POST.get("asset_id", "").strip()
        or request.GET.get("asset_id", "").strip()
    )
    selected_user_id = (
        request.POST.get("assigned_to_id", "").strip()
    )

    form = CustodyCreateForm(
        request.POST or None,
        initial=(
            {"asset_id": selected_asset_id}
            if selected_asset_id else None
        ),
    )

    if selected_asset_id:
        try:
            selected_asset = AssetSelectors.obtener(selected_asset_id)
        except Exception:
            selected_asset = None

        if selected_asset:
            form.fields["asset_id"].choices = [
                (
                    str(selected_asset.id),
                    (
                        f"{selected_asset.display_inventory_number} · "
                        f"{selected_asset.name}"
                    ),
                )
            ]

    if selected_user_id:
        try:
            selected_user = core_directory.get_user_identity(
                selected_user_id
            )
        except core_directory.CoreDirectoryError:
            selected_user = None

        if selected_user:
            form.fields["assigned_to_id"].choices = [
                (
                    str(selected_user.id),
                    (
                        f"{selected_user.display_name} · "
                        f"{selected_user.normalized_email}"
                    ),
                )
            ]

    if not getattr(request, "axentra_is_root", False):
        form.fields.pop("bypass_reason", None)

    if request.method == "POST" and form.is_valid():
        custody = run_service(
            form,
            lambda: create_custody_assignment(
                data=form.to_dto(),
                actor_id=request.user.pk,
                request=request,
            ),
        )
        if custody:
            success(
                request,
                f"Resguardo {custody.folio} creado en borrador.",
            )
            return redirect(_custody_url(custody.id))

    return render_inventory(
        request,
        page="inventory/pages/custody_form.html",
        content="inventory/content/custody_form_content.html",
        context={
            "current_inventory_view": "inventory:custody_list",
            "form": form,
        },
        status=422 if request.method == "POST" else 200,
    )


def _custody_action(request, custody_id, form_class, callback, title):
    custody = _custody(request, custody_id)
    form = form_class(request.POST or None)
    if "bypass_reason" in form.fields and not is_inventory_root(request):
        form.fields.pop("bypass_reason", None)
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
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_manage_custody")
def custody_request_return_view(request, custody_id):
    raise PermissionDenied(
        "El retiro debe iniciarse desde el documento de resguardo mediante "
        "una constancia de liberación."
    )


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_manage_custody")
def custody_complete_return_view(request, custody_id):
    raise PermissionDenied(
        "El resguardo se cierra automáticamente al integrar el acuse firmado "
        "de la constancia de liberación."
    )


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_manage_custody")
def custody_cancel_view(request, custody_id):
    return _custody_action(request, custody_id, CustodyCancelForm, lambda c, f: cancel_custody_assignment(custody_id=c.id, actor_id=request.user.pk, data=f.to_dto(), request=request), "Resguardo cancelado.")


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="has_access_module")
def movement_list_view(request):
    require_any_permission(request, "can_manage_movements", "can_authorize_movements")
    tab = request.GET.get("tab", "pending").strip().lower()
    if tab not in {"pending", "history"}:
        tab = "pending"
    f = _filters(request, "q", "asset_id", "movement_type", "site_id", "department_id", "area_id", "user_id", "date_from", "date_to")
    scope, scope_department_id = movement_scope(request)
    filter_context = _registry_filter_context(f, scope, scope_department_id)
    requests_qs = AssetMovementRequest.objects.filter(is_deleted=False).select_related("asset", "origin_dependencia", "destination_dependencia")
    if scope == RegistryScope.DEPARTMENT:
        requests_qs = requests_qs.filter(Q(origin_dependencia_id=scope_department_id) | Q(destination_dependencia_id=scope_department_id))
    elif scope == RegistryScope.OWN:
        requests_qs = requests_qs.filter(requested_by_id=request.user.pk)
    pending_statuses = {
        AssetMovementRequestStatus.PENDING_ORIGIN_APPROVAL,
        AssetMovementRequestStatus.PENDING_DESTINATION_ACCEPTANCE,
        AssetMovementRequestStatus.PENDING_PATRIMONY_EXECUTION,
    }
    if tab == "pending":
        requests_qs = requests_qs.filter(status__in=pending_statuses)
        movements = ()
    else:
        requests_qs = requests_qs.exclude(status__in=pending_statuses)
        movements = MovementSelectors.listar(
            **f,
            scope=scope,
            actor_id=request.user.pk,
            scope_department_id=scope_department_id,
        )
    return render_inventory(request, page="inventory/pages/movement_list.html", content="inventory/content/movement_list_content.html", context={"current_inventory_view":"inventory:movement_list", "tab":tab, "movement_requests":requests_qs.order_by("-requested_at"), "movements":movements, "movement_types":MovementType.choices, "can_create_movement":scope in {RegistryScope.GLOBAL, RegistryScope.DEPARTMENT}, **filter_context, **f})


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="has_access_module")
def movement_detail_view(request, movement_id):
    require_any_permission(request, "can_manage_movements", "can_authorize_movements")
    scope, scope_department_id = movement_scope(request)
    movement = selector_or_404(lambda: MovementSelectors.obtener(movement_id, scope=scope, actor_id=request.user.pk, department_id=scope_department_id))
    return render_inventory(request, page="inventory/pages/movement_detail.html", content="inventory/content/movement_detail_content.html", context={"current_inventory_view":"inventory:movement_list", "movement":movement})


_MOVEMENT_FORMS = {
    "transferencia": (AssetTransferForm, "Transferencia definitiva"),
    "reasignacion": (AssetReassignmentForm, "Cambio de resguardatario"),
    "ubicacion": (AssetLocationChangeForm, "Cambio de ubicación"),
}


def _movement_choice(items, label):
    return [("", f"--- Seleccione {label} ---"), *items]


def _movement_asset_context(asset):
    return {
        "department_id": str(asset.current_dependencia_id or ""),
        "department_label": str(asset.current_dependencia or "Sin dependencia"),
        "site_id": str(asset.current_sede_id or ""),
        "site_label": str(asset.current_sede or "Sin sede"),
        "area_id": str(asset.current_area_id or ""),
        "area_label": str(asset.current_area or "Sin área"),
        "custodian_id": str(asset.current_custodian_id or ""),
        "custodian_label": (
            asset.current_custodian.get_full_name()
            or asset.current_custodian.email
            if asset.current_custodian else "Sin resguardatario"
        ),
    }


def _configure_movement_choices(form, movement_kind, asset, data):
    """Configura sólo destinos válidos para el bien seleccionado."""
    if not asset:
        for field_name in (
            "site_id", "area_id", "user_id", "destination_site_id",
            "destination_department_id", "destination_area_id",
            "destination_custodian_id",
        ):
            if field_name in form.fields:
                form.fields[field_name].choices = [("", "--- Seleccione primero un bien ---")]
        return

    selected_site_id = str(
        data.get("site_id") or data.get("destination_site_id") or ""
    ).strip()
    if movement_kind == "ubicacion":
        department_id_value = asset.current_dependencia_id
        sites = CoreDirectorySelectors.sites(
            department_id=department_id_value,
        )
        areas = CoreDirectorySelectors.areas(
            department_id=department_id_value,
            site_id=selected_site_id or None,
        ) if selected_site_id else ()
        form.fields["site_id"].choices = _movement_choice(
            [(str(item.id), item.name) for item in sites], "sede",
        )
        form.fields["area_id"].choices = _movement_choice(
            [(str(item.id), item.name) for item in areas], "área",
        )
    elif movement_kind == "reasignacion":
        users = CoreDirectorySelectors.users(
            department_id=asset.current_dependencia_id,
        )
        form.fields["user_id"].choices = _movement_choice(
            [(str(item.id), item.display_name) for item in users],
            "resguardatario",
        )
    else:
        sites = CoreDirectorySelectors.sites()
        departments = CoreDirectorySelectors.departments(
            site_id=selected_site_id or None,
        ) if selected_site_id else ()
        selected_department_id = str(
            data.get("destination_department_id") or ""
        ).strip()
        areas = CoreDirectorySelectors.areas(
            department_id=selected_department_id or None,
            site_id=selected_site_id or None,
        ) if selected_site_id and selected_department_id else ()
        users = CoreDirectorySelectors.users(
            department_id=selected_department_id or None,
        ) if selected_department_id else ()
        form.fields["destination_site_id"].choices = _movement_choice(
            [(str(item.id), item.name) for item in sites], "sede",
        )
        form.fields["destination_department_id"].choices = _movement_choice(
            [(str(item.id), f"{item.code or 'SIN-CÓDIGO'} · {item.name}") for item in departments],
            "dependencia",
        )
        form.fields["destination_area_id"].choices = _movement_choice(
            [(str(item.id), item.name) for item in areas], "área",
        )
        form.fields["destination_custodian_id"].choices = _movement_choice(
            [(str(item.id), item.display_name) for item in users],
            "resguardatario",
        )


@require_GET
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="has_access_module")
def movement_directory_options_view(request):
    require_any_permission(request, "can_manage_movements", "can_authorize_movements")
    movement_kind = request.GET.get("movement_kind", "transferencia").strip().lower()
    asset_id = request.GET.get("asset_id", "").strip()
    site_id = request.GET.get("site_id", "").strip() or None
    department_id_value = request.GET.get("department_id", "").strip() or None
    asset = None
    if asset_id:
        scope, scope_department_id = movement_scope(request)
        asset = selector_or_404(lambda: AssetSelectors.obtener(
            asset_id,
            scope=scope,
            actor_id=request.user.pk,
            department_id=scope_department_id,
        ))
    if movement_kind == "ubicacion" and asset:
        fixed_department_id = asset.current_dependencia_id
        choices = {
            "site_choices": [
                (str(item.id), item.name)
                for item in CoreDirectorySelectors.sites(
                    department_id=fixed_department_id,
                )
            ],
            "department_choices": [],
            "area_choices": [
                (str(item.id), item.name)
                for item in CoreDirectorySelectors.areas(
                    department_id=fixed_department_id,
                    site_id=site_id,
                )
            ] if site_id else [],
            "user_choices": [],
        }
    elif movement_kind == "reasignacion" and asset:
        choices = {
            "site_choices": [], "department_choices": [], "area_choices": [],
            "user_choices": [
                (str(item.id), item.display_name)
                for item in CoreDirectorySelectors.users(
                    department_id=asset.current_dependencia_id,
                )
            ],
        }
    else:
        choices = {
            "site_choices": [
                (str(item.id), item.name)
                for item in CoreDirectorySelectors.sites()
            ],
            "department_choices": [
                (str(item.id), f"{item.code or 'SIN-CÓDIGO'} · {item.name}")
                for item in CoreDirectorySelectors.departments(site_id=site_id)
            ] if site_id else [],
            "area_choices": [
                (str(item.id), item.name)
                for item in CoreDirectorySelectors.areas(
                    department_id=department_id_value,
                    site_id=site_id,
                )
            ] if site_id and department_id_value else [],
            "user_choices": [
                (str(item.id), item.display_name)
                for item in CoreDirectorySelectors.users(
                    department_id=department_id_value,
                )
            ] if department_id_value else [],
        }
    payload = {
        key: [{"value": str(value), "label": label} for value, label in values]
        for key, values in choices.items()
    }
    payload["asset_context"] = _movement_asset_context(asset) if asset else None
    return JsonResponse(payload)


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="has_access_module")
def movement_create_view(request, movement_kind):
    if movement_kind == "transferencia":
        require_any_permission(
            request,
            "can_manage_movements",
            "can_authorize_movements",
            "can_approve_department_intake",
        )
    else:
        require_any_permission(request, "can_manage_movements", "can_authorize_movements")
    definition = _MOVEMENT_FORMS.get(movement_kind)
    if not definition:
        raise PermissionDenied("El tipo de movimiento solicitado no está habilitado.")
    form_class, title = definition
    scope, scope_department_id = movement_scope(request)
    form_data = request.POST or None
    form = form_class(form_data)
    assets = AssetSelectors.listar_activos(
        scope=scope,
        actor_id=request.user.pk,
        scope_department_id=scope_department_id,
    )
    form.fields["asset_id"].choices = [
        ("", "--- Seleccione un bien ---"),
        *((str(asset.id), f"{asset.display_inventory_number} · {asset.name}") for asset in assets),
    ]
    selected_asset_id = str(
        (request.POST.get("asset_id") if request.method == "POST" else request.GET.get("asset_id"))
        or ""
    ).strip()
    assets_by_id = {str(asset.id): asset for asset in assets}
    selected_asset = assets_by_id.get(selected_asset_id)
    _configure_movement_choices(
        form,
        movement_kind,
        selected_asset,
        request.POST if request.method == "POST" else request.GET,
    )
    if "bypass_reason" in form.fields and not is_inventory_root(request):
        form.fields.pop("bypass_reason", None)
    if request.method == "POST" and form.is_valid():
        item = run_service(form, lambda: create_movement_request(data=form.to_dto(), actor_id=request.user.pk, request=request))
        if item:
            success(request, f"Solicitud {item.folio} registrada correctamente.")
            return redirect(reverse("inventory:movement_request_detail", kwargs={"request_id":item.id}))
    return render_inventory(request, page="inventory/pages/movement_form.html", content="inventory/content/movement_form_content.html", context={"current_inventory_view":"inventory:movement_list", "form":form, "form_title":title, "movement_kind":movement_kind, "selected_asset_context":_movement_asset_context(selected_asset) if selected_asset else None}, status=422 if request.method == "POST" else 200)


def _movement_request(request, request_id):
    scope, scope_department_id = movement_scope(request)
    qs = AssetMovementRequest.objects.select_related("asset", "origin_dependencia", "origin_area", "origin_sede", "origin_custodian", "destination_dependencia", "destination_area", "destination_sede", "destination_custodian", "requested_by", "resulting_movement").filter(is_deleted=False)
    if scope == RegistryScope.DEPARTMENT:
        qs = qs.filter(Q(origin_dependencia_id=scope_department_id) | Q(destination_dependencia_id=scope_department_id))
    elif scope == RegistryScope.OWN:
        qs = qs.filter(requested_by_id=request.user.pk)
    return selector_or_404(lambda: qs.get(pk=request_id))


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="has_access_module")
def movement_request_detail_view(request, request_id):
    item = _movement_request(request, request_id)
    scope_department_id = department_id(request)
    root = bool(getattr(request, "axentra_is_root", False))
    destination_authority = (
        can_authorize_department_movement(
            actor_id=request.user.pk,
            department_id=item.destination_dependencia_id,
        )
        if item.destination_dependencia_id else None
    )
    origin_authority = can_authorize_department_movement(
        actor_id=request.user.pk,
        department_id=item.origin_dependencia_id,
    )
    can_accept_destination = item.status == AssetMovementRequestStatus.PENDING_DESTINATION_ACCEPTANCE and bool(destination_authority)
    destination_area_choices = CoreDirectorySelectors.areas(
        department_id=item.destination_dependencia_id,
        site_id=item.destination_sede_id,
    ) if can_accept_destination and item.destination_dependencia_id else ()
    destination_user_choices = CoreDirectorySelectors.users(
        department_id=item.destination_dependencia_id,
    ) if can_accept_destination and item.destination_dependencia_id else ()
    return render_inventory(request, page="inventory/pages/movement_request_detail.html", content="inventory/content/movement_request_detail_content.html", context={"current_inventory_view":"inventory:movement_list", "movement_request":item, "can_approve_origin":item.status == AssetMovementRequestStatus.PENDING_ORIGIN_APPROVAL and origin_authority, "can_accept_destination":can_accept_destination, "can_execute_movement":item.status == AssetMovementRequestStatus.PENDING_PATRIMONY_EXECUTION and has_any_permission(request,"can_manage_movements"), "destination_area_choices":destination_area_choices, "destination_user_choices":destination_user_choices})


class _MovementDecisionForm(forms.Form):
    approve = forms.BooleanField(required=False, label="Aprobar")
    comment = forms.CharField(required=False, label="Comentario", widget=forms.Textarea(attrs={"rows":3}))


class _MovementDestinationDecisionForm(_MovementDecisionForm):
    destination_area_id = forms.UUIDField(required=False)
    destination_custodian_id = forms.UUIDField(required=False)


@require_POST
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="has_access_module")
def movement_origin_decision_view(request, request_id):
    item = _movement_request(request, request_id); form = _MovementDecisionForm(request.POST)
    if form.is_valid():
        result = run_service(form, lambda: approve_movement_origin(request_id=item.id, actor_id=request.user.pk, approve=form.cleaned_data["approve"], comment=form.cleaned_data["comment"], request=request))
        if result: success(request, "Decisión de la dependencia origen registrada.")
    return redirect(reverse("inventory:movement_request_detail", kwargs={"request_id":item.id}))


@require_POST
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="has_access_module")
def movement_destination_decision_view(request, request_id):
    item = _movement_request(request, request_id); form = _MovementDestinationDecisionForm(request.POST)
    if form.is_valid():
        result = run_service(form, lambda: accept_movement_destination(request_id=item.id, actor_id=request.user.pk, approve=form.cleaned_data["approve"], comment=form.cleaned_data["comment"], destination_area_id=form.cleaned_data.get("destination_area_id"), destination_custodian_id=form.cleaned_data.get("destination_custodian_id"), request=request))
        if result: success(request, "Decisión de la dependencia destino registrada.")
    return redirect(reverse("inventory:movement_request_detail", kwargs={"request_id":item.id}))


@require_POST
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_manage_movements")
def movement_execute_view(request, request_id):
    item = _movement_request(request, request_id)
    result = execute_approved_movement(request_id=item.id, actor=request.user, request_context=build_audit_request_context(request))
    success(request, "Movimiento ejecutado y expediente actualizado.")
    return redirect(reverse("inventory:movement_detail", kwargs={"movement_id":result.resulting_movement_id}))


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
    if is_inventory_root(request):
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
    origin_matches = department_id(request) == getattr(
        loan,
        "origin_dependencia_id",
        None,
    )
    origin_operator = bool(
        is_inventory_root(request)
        or (origin_matches and (manages or requests))
    )
    destination_operator = bool(
        is_inventory_root(request)
        or (destination_matches and authorizes)
    )
    receipt = None
    acknowledgement = None
    return_receipt = None
    return_acknowledgement = None
    if getattr(loan, "id", None):
        acknowledgement = get_acknowledgement_state(
            owner_type=InventoryDocumentOwnerType.LOAN,
            owner_id=loan.id,
            generated_type="LOAN_RECEIPT",
        )
        receipt = acknowledgement.document
        return_acknowledgement = get_acknowledgement_state(
            owner_type=InventoryDocumentOwnerType.LOAN,
            owner_id=loan.id,
            generated_type="RETURN_RECEIPT",
        )
        return_receipt = return_acknowledgement.document
    receipt_ready = bool(
        acknowledgement
        and acknowledgement.code == "VALIDATED"
    )
    return_receipt_ready = bool(
        return_acknowledgement
        and return_acknowledgement.code == "VALIDATED"
    )
    blocking_disposal = None
    if (
        loan.status in {"DRAFT", "REJECTED"}
        and getattr(loan, "asset_id", None)
    ):
        blocking_disposal = (
            DisposalRequest.objects.filter(
                asset_id=loan.asset_id,
                status__in={
                    DisposalStatus.SUBMITTED,
                    DisposalStatus.EVIDENCE_PENDING,
                    DisposalStatus.TECHNICAL_REVIEW,
                    DisposalStatus.ADMINISTRATIVE_REVIEW,
                    DisposalStatus.AUTHORIZATION_PENDING,
                    DisposalStatus.APPROVED,
                },
                is_deleted=False,
            )
            .order_by("-requested_at")
            .first()
        )
    return {
        "loan": loan,
        "loan_receipt": receipt,
        "loan_acknowledgement": acknowledgement,
        "loan_return_receipt": return_receipt,
        "loan_return_acknowledgement": return_acknowledgement,
        "receipt_required": loan.status in {
            "DEPARTMENT_APPROVED", "AUTHORIZED", "DELIVERED", "OVERDUE", "RETURN_PENDING", "RETURNED",
        },
        "return_receipt_required": loan.status in {
            "RETURN_PENDING", "RETURNED",
        },
        "can_upload_loan_receipt": origin_operator and loan.status in {
            "DEPARTMENT_APPROVED", "AUTHORIZED", "DELIVERED", "OVERDUE", "RETURN_PENDING",
        },
        "can_confirm_loan_receipt": destination_operator and bool(
            acknowledgement and acknowledgement.code in {"UPLOADED", "OBSERVED"}
        ),
        "blocking_disposal": blocking_disposal,
        "can_submit_loan": requests and own_request and loan.status in {"DRAFT", "REJECTED"} and blocking_disposal is None,
        "can_decide_department_loan": authorizes and destination_matches and loan.status == "REQUESTED" and not loan.external_borrower,
        "can_authorize_loan": manages and loan.external_borrower and loan.status == "REQUESTED",
        "can_deliver_loan": origin_operator and receipt_ready and loan.status in {"DEPARTMENT_APPROVED", "AUTHORIZED"},
        "can_request_loan_return": (manages or own_request or own_receipt or (authorizes and destination_matches)) and loan.status in {"DELIVERED", "OVERDUE"},
        "can_upload_return_receipt": destination_operator and loan.status == "RETURN_PENDING",
        "can_confirm_return_receipt": origin_operator and bool(
            return_acknowledgement
            and return_acknowledgement.code in {"UPLOADED", "OBSERVED"}
        ),
        "can_receive_loan_return": origin_operator and return_receipt_ready and loan.status == "RETURN_PENDING",
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
    f = _filters(request, "q", "status", "asset_id", "borrower_id", "bucket", "site_id", "department_id", "area_id")
    f["overdue"] = request.GET.get("overdue") == "1"
    scope, scope_department_id = _loan_scope(request)
    filter_context = _registry_filter_context(f, scope, scope_department_id)
    return render_inventory(request, page="inventory/pages/loan_list.html", content="inventory/content/loan_list_content.html", context={"current_inventory_view":"inventory:loan_list", "loans":LoanSelectors.listar(**f, active_only=f["bucket"] != "history", scope=scope, actor_id=request.user.pk, scope_department_id=scope_department_id), "loan_summary":LoanSelectors.dashboard_metrics(scope=scope, actor_id=request.user.pk, department_id=scope_department_id), "can_create_full_loan":has_any_permission(request, "can_manage_loans"), "show_department_tabs":scope == RegistryScope.DEPARTMENT, "show_global_tabs":scope == RegistryScope.GLOBAL, "loan_statuses":LoanSelectors.status_choices(), **filter_context, **f})


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
    if not is_inventory_root(request):
        form.fields.pop("bypass_reason", None)
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
    if not is_inventory_root(request):
        form.fields.pop("bypass_reason", None)
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
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="has_access_module")
def loan_deliver_view(request, loan_id):
    return _loan_action(request, loan_id, AssetLoanDeliveryForm, lambda loan, form: deliver_asset_loan(loan_id=loan.id, actor_id=request.user.pk, data=form.to_dto(), request=request), "Entrega del préstamo registrada.")


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_request_loans")
def loan_request_return_view(request, loan_id):
    return _loan_action(request, loan_id, AssetLoanReturnRequestForm, lambda loan, form: request_asset_loan_return(loan_id=loan.id, actor_id=request.user.pk, data=form.to_dto(), request=request), "Solicitud de devolución registrada.")


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="has_access_module")
def loan_return_view(request, loan_id):
    return _loan_action(request, loan_id, AssetLoanReturnForm, lambda loan, form: return_asset_loan(loan_id=loan.id, actor_id=request.user.pk, data=form.to_dto(), request=request), "Devolución recibida y préstamo cerrado.")


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="has_access_module")
def loan_cancel_view(request, loan_id):
    return _loan_action(request, loan_id, AssetLoanCancelForm, lambda loan, form: cancel_asset_loan(loan_id=loan.id, actor_id=request.user.pk, data=form.to_dto(), request=request), "Préstamo cancelado.")


@require_GET
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="has_access_module")
def loan_print_view(request, loan_id):
    require_any_permission(
        request,
        "can_request_loans",
        "can_manage_loans",
        "can_authorize_loans",
    )
    document_kind = request.GET.get("document", "loan").strip().lower()
    if document_kind not in {"loan", "return"}:
        document_kind = "loan"
    return render(
        request,
        "inventory/pages/loan_print.html",
        {
            "loan": _loan(request, loan_id),
            "document_kind": document_kind,
        },
    )


def _disposal_url(disposal_id):
    return reverse("inventory:disposal_detail", kwargs={"disposal_id": disposal_id})


def _disposal(request, disposal_id):
    scope, scope_department_id = disposal_scope(request)
    return selector_or_404(lambda: DisposalSelectors.obtener(
        disposal_id,
        scope=scope,
        actor_id=request.user.pk,
        department_id=scope_department_id,
    ))


def _disposal_context(request, disposal):
    from apps.inventory.services.disposal_service import (
        _missing_documents,
        disposal_stage_document_types,
    )
    from apps.inventory.services.document_service import (
        disposal_stage_document_upload_permissions,
        helpdesk_disposal_workflow_available,
    )

    permissions = set(getattr(request, "axentra_permissions_list", []) or [])
    root = bool(getattr(request, "axentra_is_root", False))
    manages = root or "can_manage_disposals" in permissions
    finalizes = root or bool({"can_finalize_disposal", "can_authorize_disposals"} & permissions)
    executes = root or "can_execute_disposals" in permissions
    can_operate_custody_release = bool(
        root
        or {
            "can_manage_custody",
            "can_review_patrimony_disposal",
        }.issubset(permissions)
    )
    owns = disposal.requested_by_id == request.user.pk
    terminal_statuses = {"REJECTED", "EXECUTED", "CANCELLED"}
    is_terminal = disposal.status in terminal_statuses
    blocking_custody = None
    pending_custody_release = None
    blocking_loan = None
    disposal_asset_id = getattr(disposal, "asset_id", None)
    if disposal_asset_id and disposal.status not in {
        "REJECTED", "EXECUTED", "CANCELLED",
    }:
        blocking_loan = (
            AssetLoan.objects.filter(
                asset_id=disposal_asset_id,
                status__in={
                    AssetLoanStatus.REQUESTED,
                    AssetLoanStatus.DEPARTMENT_APPROVED,
                    AssetLoanStatus.AUTHORIZED,
                    AssetLoanStatus.DELIVERED,
                    AssetLoanStatus.OVERDUE,
                    AssetLoanStatus.RETURN_PENDING,
                },
                is_deleted=False,
            )
            .order_by("-requested_at")
            .first()
        )
    if disposal.status == "APPROVED" and disposal_asset_id:
        blocking_custody = (
            CustodyAssignment.objects.select_related(
                "asset", "assigned_to", "dependencia",
            )
            .filter(
                asset_id=disposal_asset_id,
                status__in={
                    CustodyStatus.PENDING_AUTHORIZATION,
                    CustodyStatus.PENDING_ACCEPTANCE,
                    CustodyStatus.ACTIVE,
                    CustodyStatus.RETURN_PENDING,
                },
                is_deleted=False,
            )
            .order_by("-assigned_at")
            .first()
        )
        if blocking_custody:
            pending_custody_release = (
                CustodyDocument.objects.filter(
                    document_type=CustodyDocumentType.RELEASE,
                    status__in={
                        CustodyDocumentStatus.DRAFT,
                        CustodyDocumentStatus.IN_PROCESS,
                    },
                    items__custody_assignment_id=blocking_custody.id,
                    is_deleted=False,
                )
                .order_by("-prepared_at")
                .first()
            )
    accounting_confirmation_flow = (
        DocumentType.ACCOUNTING_DISPOSAL_CONFIRMATION
        in disposal_stage_document_types(
            disposal, "FINAL_AUTHORIZATION"
        )
    )
    approvals_manager = disposal.approvals
    pending_stages = approvals_manager.filter(decision__in=("PENDING", "OBSERVED"))
    approvals = list(approvals_manager.all()) if hasattr(approvals_manager, "all") else []
    allowed_stages = set()
    # La dependencia ya confirmó su voluntad al enviar la solicitud y firmar
    # el oficio. La validación documental de Patrimonio cierra esta etapa sin
    # exigir un segundo clic al director.
    permission_stage = {
        "can_review_technical_disposal": "TECHNICAL",
        "can_review_patrimony_disposal": "PATRIMONY",
        "can_review_legal_disposal": "LEGAL",
        "can_review_internal_control_disposal": "INTERNAL_CONTROL",
        "can_record_council_disposal": "COUNCIL",
    }
    if root:
        allowed_stages.update(permission_stage.values())
    else:
        allowed_stages.update(
            stage for permission, stage in permission_stage.items()
            if permission in permissions
        )
    ordered = [
        approval for approval in approvals
        if approval.decision in {"PENDING", "OBSERVED"}
    ]
    current_stage = (
        ordered[0].stage
        if ordered
        else "DEPARTMENT"
        if not approvals and pending_stages.exists()
        else None
    )
    resolvable_stages = pending_stages.filter(
        stage=current_stage,
        stage__in=allowed_stages,
    )
    resolve_action_labels = {
        "DEPARTMENT": "Revisar y confirmar solicitud",
        "TECHNICAL": "Integrar y confirmar dictamen",
        "PATRIMONY": "Revisar expediente patrimonial",
        "LEGAL": "Resolver revisión jurídica",
        "INTERNAL_CONTROL": "Resolver intervención del OIC",
        "COUNCIL": "Registrar resolución de Cabildo",
    }
    # Los selectores entregan normalmente un RelatedManager de Django. Mantener
    # este contexto tolerante a objetos sin ``all()`` facilita su reutilización
    # en pruebas unitarias y evita acoplar la visibilidad de botones al ORM.
    approval_ids = [approval.id for approval in approvals]
    documents = AssetDocument.objects.filter(
        owner_type=InventoryDocumentOwnerType.DISPOSAL_APPROVAL,
        owner_id__in=approval_ids,
        is_deleted=False,
        is_current_version=True,
    ).select_related("uploaded_by", "validated_by")
    stage_cards = []
    helpdesk_available = (
        helpdesk_disposal_workflow_available()
        if any(approval.stage == "TECHNICAL" for approval in approvals)
        else False
    )
    for approval in approvals:
        requirements = DisposalStageDocumentRequirement.objects.filter(
            is_active=True,
            is_deleted=False,
            stage=approval.stage,
            disposal_reason__in=("", disposal.reason),
        )
        missing_document_types = {
            document_type
            for _stage, document_type in _missing_documents(
                disposal, stage=approval.stage
            )
        }
        document_type_labels = dict(DocumentType.choices)
        missing_documents = [
            {
                "document_type": document_type,
                "label": document_type_labels.get(document_type, document_type),
            }
            for document_type in sorted(missing_document_types)
        ]
        stage_documents = [
            document for document in documents
            if document.owner_id == approval.id
        ]
        has_rejected_document = any(
            document.validation_status == DocumentValidationStatus.REJECTED
            for document in stage_documents
        )
        can_upload_missing_type = any(
            bool(
                set(disposal_stage_document_upload_permissions(
                    approval.stage,
                    document_type=document_type,
                    helpdesk_available=helpdesk_available,
                )) & permissions
            )
            for document_type in missing_document_types
        )
        patrimony_custodian = bool(
            "can_review_patrimony_disposal" in permissions
            and approval.stage in {"FINAL_AUTHORIZATION", "TECHNICAL"}
            and {
                "TECHNICAL": "can_review_technical_disposal",
                "FINAL_AUTHORIZATION": "can_finalize_disposal",
            }.get(approval.stage) not in permissions
            and (
                approval.stage == "FINAL_AUTHORIZATION"
                or not helpdesk_available
            )
        )
        stage_cards.append({
            "approval": approval,
            "requirements": requirements,
            "documents": stage_documents,
            "missing_documents": missing_documents,
            "has_rejected_document": has_rejected_document,
            "patrimony_custodian": patrimony_custodian,
            "custodial_note": (
                "Control Patrimonial puede integrar el documento firmado como custodio; la autoría permanece en el área o autoridad emisora."
                if patrimony_custodian
                else ""
            ),
            "upload_label": (
                "Sustituir documento observado"
                if has_rejected_document
                else "Agregar documento"
            ),
            "can_upload": not is_terminal and bool(missing_document_types) and (
                root
                or can_upload_missing_type
            ),
        })
    return {
        "disposal": disposal,
        "blocking_loan": blocking_loan,
        "can_submit_disposal": (
            (owns or manages)
            and disposal.status == "DRAFT"
            and blocking_loan is None
        ),
        "can_resolve_disposal": (
            not is_terminal
            and current_stage != "DEPARTMENT"
            and resolvable_stages.exists()
        ),
        "can_finalize_disposal": (
            finalizes
            and not accounting_confirmation_flow
            and disposal.status == "AUTHORIZATION_PENDING"
        ),
        "can_execute_disposal": (
            executes
            and disposal.status == "APPROVED"
            and blocking_custody is None
            and blocking_loan is None
        ),
        "blocking_custody": blocking_custody,
        "pending_custody_release": pending_custody_release,
        "can_prepare_custody_release": (
            blocking_custody is not None
            and blocking_custody.status in {
                CustodyStatus.ACTIVE,
                CustodyStatus.RETURN_PENDING,
            }
            and can_operate_custody_release
        ),
        "can_operate_custody_release": can_operate_custody_release,
        "can_cancel_disposal": (
            manages
            and disposal.status not in {"APPROVED", "REJECTED", "EXECUTED", "CANCELLED"}
        ) or (
            owns and disposal.status in {"DRAFT", "SUBMITTED"}
        ),
        "resolve_disposal_action_label": resolve_action_labels.get(
            current_stage, "Resolver etapa"
        ),
        "pending_stages": resolvable_stages,
        "stage_cards": stage_cards,
        "can_upload_disposal_document": root or "can_manage_documents" in permissions,
        "can_validate_disposal_document": not is_terminal and (
            root or "can_validate_documents" in permissions
        ),
    }


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="has_access_module")
def disposal_list_view(request):
    require_any_permission(request, "can_request_disposals", "can_manage_disposals", "can_authorize_disposals", "can_finalize_disposal", "can_confirm_department_disposal", "can_review_technical_disposal", "can_review_patrimony_disposal", "can_review_legal_disposal", "can_review_internal_control_disposal", "can_record_council_disposal", "can_execute_disposals")
    f = _filters(request, "q", "status", "asset_id", "reason", "site_id", "department_id", "area_id", "requested_by_id", "date_from", "date_to")
    tab = request.GET.get("tab", "active").strip().lower()
    if tab not in {"active", "history"}:
        tab = "active"
    scope, scope_department_id = disposal_scope(request)
    filter_context = _registry_filter_context(f, scope, scope_department_id)
    historical_statuses = {
        "REJECTED",
        "EXECUTED",
        "CANCELLED",
    }
    queryset = DisposalSelectors.listar(
        **f,
        scope=scope,
        actor_id=request.user.pk,
        scope_department_id=scope_department_id,
    )
    queryset = (
        queryset.filter(status__in=historical_statuses)
        if tab == "history"
        else queryset.exclude(status__in=historical_statuses)
    )
    page_obj = Paginator(queryset, 30).get_page(request.GET.get("page"))
    pagination_params = request.GET.copy()
    pagination_params.pop("page", None)
    available_statuses = [
        (value, label)
        for value, label in DisposalSelectors.status_choices()
        if (value in historical_statuses) == (tab == "history")
    ]
    return render_inventory(
        request,
        page="inventory/pages/disposal_list.html",
        content="inventory/content/disposal_list_content.html",
        context={
            "current_inventory_view": "inventory:disposal_list",
            "disposals": page_obj.object_list,
            "page_obj": page_obj,
            "pagination_query": pagination_params.urlencode(),
            "tab": tab,
            "can_create_disposal": has_any_permission(
                request, "can_request_disposals", "can_manage_disposals"
            ),
            "disposal_statuses": available_statuses,
            **filter_context,
            **f,
        },
    )


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="has_access_module")
def disposal_detail_view(request, disposal_id):
    require_any_permission(request, "can_request_disposals", "can_manage_disposals", "can_authorize_disposals", "can_finalize_disposal", "can_confirm_department_disposal", "can_review_technical_disposal", "can_review_patrimony_disposal", "can_review_legal_disposal", "can_review_internal_control_disposal", "can_record_council_disposal", "can_execute_disposals")
    disposal = _disposal(request, disposal_id)
    context = _disposal_context(request, disposal)
    context.update({"current_inventory_view":"inventory:disposal_list", "documents":DocumentSelectors.documents(owner_type="DISPOSAL_REQUEST", owner_id=disposal.id)})
    return render_inventory(request, page="inventory/pages/disposal_detail.html", content="inventory/content/disposal_detail_content.html", context=context)


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="has_access_module")
def disposal_create_view(request):
    require_any_permission(request, "can_request_disposals", "can_manage_disposals")
    requested_asset_id = request.GET.get("asset_id", "").strip()
    form = DisposalRequestCreateForm(
        request.POST or None,
        initial={"asset_id": requested_asset_id} if requested_asset_id else None,
    )
    scope, scope_department_id = disposal_scope(request)
    assets = AssetSelectors.listar_activos(scope=scope, actor_id=request.user.pk, scope_department_id=scope_department_id).filter(patrimonial_status="ACTIVE")
    form.fields["asset_id"].choices = [("", "--- Seleccione un bien ---"), *((str(a.id), f"{a.display_inventory_number} · {a.name}") for a in assets)]
    if request.method == "POST" and form.is_valid():
        disposal = run_service(form, lambda: create_disposal_request(data=form.to_dto(), actor_id=request.user.pk, request=request))
        if disposal:
            success(request, f"Solicitud {disposal.folio} creada en borrador.")
            return redirect(_disposal_url(disposal.id))
    return render_inventory(request, page="inventory/pages/disposal_form.html", content="inventory/content/disposal_form_content.html", context={"current_inventory_view":"inventory:disposal_list", "form":form}, status=422 if request.method == "POST" else 200)


def _disposal_action(request, disposal_id, form_class, callback, title):
    disposal = _disposal(request, disposal_id)
    form = form_class(request.POST or None)
    if not is_inventory_root(request):
        form.fields.pop("bypass_reason", None)
    if request.method == "POST" and form.is_valid():
        result = run_service(form, lambda: callback(disposal, form))
        if result:
            success(request, title)
            return redirect(_disposal_url(disposal.id))
    return render_inventory(request, page="inventory/pages/disposal_action_form.html", content="inventory/content/disposal_action_form_content.html", context={"current_inventory_view":"inventory:disposal_list", "disposal":disposal, "form":form, "form_title":title}, status=422 if request.method == "POST" else 200)


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="has_access_module")
def disposal_submit_view(request, disposal_id):
    return _disposal_action(request, disposal_id, DisposalSubmitForm, lambda d, f: submit_disposal_request(disposal_id=d.id, actor_id=request.user.pk, data=f.to_dto(), request=request), "Solicitud enviada a revisión.")


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="has_access_module")
def disposal_resolve_stage_view(request, disposal_id):
    disposal = _disposal(request, disposal_id)
    context = _disposal_context(request, disposal)
    if not context["can_resolve_disposal"]:
        raise PermissionDenied("No tiene etapas de baja pendientes por resolver.")
    form = DisposalStageResolutionForm(request.POST or None)
    if not is_inventory_root(request):
        form.fields.pop("bypass_reason", None)
        form.fields["decision"].choices = [
            choice for choice in form.fields["decision"].choices
            if choice[0] not in {"PENDING", "NOT_REQUIRED"}
        ]
    form.fields["stage"].choices = [
        (approval.stage, approval.get_stage_display())
        for approval in context["pending_stages"]
    ]
    if request.method == "POST" and form.is_valid():
        result = run_service(form, lambda: resolve_disposal_stage(disposal_id=disposal.id, actor_id=request.user.pk, data=form.to_dto(), request=request))
        if result:
            success(request, "Etapa de revisión resuelta.")
            return redirect(_disposal_url(disposal.id))
    return render_inventory(request, page="inventory/pages/disposal_action_form.html", content="inventory/content/disposal_action_form_content.html", context={"current_inventory_view":"inventory:disposal_list", "disposal":disposal, "form":form, "form_title":"Resolver etapa de revisión"}, status=422 if request.method == "POST" else 200)


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="has_access_module")
def disposal_finalize_view(request, disposal_id):
    require_any_permission(request, "can_finalize_disposal", "can_authorize_disposals")
    return _disposal_action(request, disposal_id, DisposalFinalApprovalForm, lambda d, f: finalize_disposal_approval(disposal_id=d.id, actor_id=request.user.pk, data=f.to_dto(), request=request), "Decisión final registrada.")


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_execute_disposals")
def disposal_execute_view(request, disposal_id):
    return _disposal_action(request, disposal_id, DisposalExecuteForm, lambda d, f: execute_disposal(disposal_id=d.id, actor_id=request.user.pk, data=f.to_dto(), request=request), "Baja patrimonial ejecutada.")


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="has_access_module")
def disposal_cancel_view(request, disposal_id):
    return _disposal_action(request, disposal_id, DisposalCancelForm, lambda d, f: cancel_disposal(disposal_id=d.id, actor_id=request.user.pk, data=f.to_dto(), request=request), "Solicitud de baja cancelada.")


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="has_access_module")
def disposal_stage_document_upload_view(request, disposal_id, approval_id):
    from apps.inventory.services.disposal_service import (
        _missing_documents,
        disposal_stage_document_types,
    )
    from apps.inventory.services.document_service import (
        disposal_stage_document_upload_permissions,
        helpdesk_disposal_workflow_available,
    )

    disposal = _disposal(request, disposal_id)
    approval = selector_or_404(lambda: disposal.approvals.get(pk=approval_id))
    helpdesk_available = helpdesk_disposal_workflow_available()
    permissions = set(getattr(request, "axentra_permissions_list", []) or [])
    allowed_types = disposal_stage_document_types(disposal, approval.stage)
    missing_types = {
        document_type
        for _stage, document_type in _missing_documents(
            disposal, stage=approval.stage
        )
    }
    root = bool(getattr(request, "axentra_is_root", False))
    allowed_types = tuple(
        document_type
        for document_type in allowed_types
        if document_type in missing_types
        and (
            root
            or bool(
                set(disposal_stage_document_upload_permissions(
                    approval.stage,
                    document_type=document_type,
                    helpdesk_available=helpdesk_available,
                )) & permissions
            )
        )
    )
    if not allowed_types:
        raise PermissionDenied(
            "No cuenta con documentos pendientes que pueda integrar en esta etapa."
        )
    custodial_types = {
        DocumentType.TECHNICAL_REPORT,
        DocumentType.ACCOUNTING_DISPOSAL_CONFIRMATION,
    }
    custodial_integration = bool(
        "can_review_patrimony_disposal" in permissions
        and any(document_type in custodial_types for document_type in allowed_types)
    )
    document_labels = dict(DocumentType.choices)
    choices = [
        (document_type, document_labels.get(document_type, document_type))
        for document_type in allowed_types
    ]
    form = DisposalStageDocumentUploadForm(
        request.POST or None,
        request.FILES or None,
        approval_id=approval.id,
        document_choices=choices,
        custodial_integration=custodial_integration,
    )
    if request.method == "POST" and form.is_valid():
        document = run_service(form, lambda: upload_disposal_stage_document(approval_id=approval.id, data=form.to_dto(), actor_id=request.user.pk, request=request))
        if document:
            success(request, "Documento cargado y enviado a validación.")
            return redirect(_disposal_url(disposal.id))
    return render_inventory(request, page="inventory/pages/disposal_action_form.html", content="inventory/content/disposal_action_form_content.html", context={"current_inventory_view":"inventory:disposal_list", "disposal":disposal, "form":form, "form_title":f"Agregar documento · {approval.get_stage_display()}", "custodial_integration":custodial_integration, "pending_document_labels": [label for _value, label in choices]}, status=422 if request.method == "POST" else 200)


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_validate_documents")
def disposal_document_validate_view(request, disposal_id, document_id):
    disposal = _disposal(request, disposal_id)
    approval_ids = disposal.approvals.values_list("id", flat=True)
    document = selector_or_404(lambda: AssetDocument.objects.get(pk=document_id, owner_type=InventoryDocumentOwnerType.DISPOSAL_APPROVAL, owner_id__in=approval_ids, is_deleted=False))
    form = DocumentValidationResolveForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        result = run_service(form, lambda: resolve_inventory_document(document_id=document.id, data=form.to_dto(), actor_id=request.user.pk, request=request))
        if result:
            success(request, "Validación documental registrada.")
            return redirect(_disposal_url(disposal.id))
    return render_inventory(request, page="inventory/pages/disposal_action_form.html", content="inventory/content/disposal_action_form_content.html", context={"current_inventory_view":"inventory:disposal_list", "disposal":disposal, "form":form, "form_title":f"Validar documento · {document.title}"}, status=422 if request.method == "POST" else 200)


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="has_access_module")
def document_list_view(request):
    require_any_permission(request, "can_manage_documents", "can_validate_documents")
    f = _filters(request, "owner_type", "owner_id", "document_type", "validation_status", "q", "date_from", "date_to", "department_id")
    tab = request.GET.get("tab", "pending").strip().lower()
    if tab not in {"pending", "observed", "history"}:
        tab = "pending"
    scope, scope_department_id = asset_scope(request)
    document_org_filters = {
        "site_id": "", "department_id": f.get("department_id", ""),
        "area_id": "", "user_id": "",
    }
    filter_context = _registry_filter_context(
        document_org_filters, scope, scope_department_id,
    )
    include_restricted = has_any_permission(request, "can_view_restricted_documents")
    bucket = {
        "pending": [DocumentValidationStatus.PENDING],
        "observed": [DocumentValidationStatus.REJECTED],
        "history": [DocumentValidationStatus.VALIDATED, DocumentValidationStatus.EXPIRED, DocumentValidationStatus.SUPERSEDED, DocumentValidationStatus.CANCELLED],
    }[tab]
    explicit_status = f.pop("validation_status")
    filter_department_id = f.pop("department_id") if scope == RegistryScope.GLOBAL else ""
    queryset = DocumentSelectors.documents(**f, validation_status=explicit_status, validation_statuses=None if explicit_status else bucket, scope=scope, actor_id=request.user.pk, scope_department_id=scope_department_id, include_restricted=include_restricted, filter_department_id=filter_department_id)
    if tab != "history":
        queryset = queryset.exclude(
            owner_type=InventoryDocumentOwnerType.LOAN,
            document_type__in={
                DocumentType.SIGNED_LOAN_RECEIPT,
                DocumentType.SIGNED_RETURN_RECEIPT,
            },
        )
    page_obj = Paginator(queryset, 30).get_page(request.GET.get("page"))
    pagination_params = request.GET.copy(); pagination_params.pop("page", None)
    return render_inventory(request, page="inventory/pages/document_list.html", content="inventory/content/document_list_content.html", context={"current_inventory_view":"inventory:document_list", "documents":page_obj.object_list, "page_obj":page_obj, "pagination_query":pagination_params.urlencode(), "tab":tab, "validation_statuses":DocumentValidationStatus.choices, "validation_status":explicit_status, "document_types":DocumentType.choices, "owner_types":InventoryDocumentOwnerType.choices, "can_validate_documents":has_any_permission(request,"can_validate_documents"), "department_id":filter_department_id, **filter_context, **f})


def _document_owner_context(request, owner_type, owner_id):
    if owner_type == InventoryDocumentOwnerType.ASSET:
        scope, dep = asset_scope(request); owner = selector_or_404(lambda: AssetSelectors.obtener(owner_id, scope=scope, actor_id=request.user.pk, department_id=dep)); return owner, owner.id, str(owner)
    if owner_type == InventoryDocumentOwnerType.INTAKE_REQUEST:
        scope, dep = intake_scope(request); owner = selector_or_404(lambda: IntakeSelectors.obtener(owner_id, scope=scope, actor_id=request.user.pk, department_id=dep)); return owner, None, str(owner)
    if owner_type == InventoryDocumentOwnerType.CUSTODY_ASSIGNMENT:
        owner = _custody(request, owner_id); return owner, owner.asset_id, str(owner)
    if owner_type == InventoryDocumentOwnerType.CUSTODY_DOCUMENT:
        require_any_permission(request, "can_manage_custody")
        owner = selector_or_404(
            lambda: CustodyDocument.objects.get(
                pk=owner_id,
                is_deleted=False,
            )
        )
        return owner, None, str(owner)
    if owner_type == InventoryDocumentOwnerType.LOAN:
        scope, dep = loan_scope(request); owner = selector_or_404(lambda: LoanSelectors.obtener(owner_id, scope=scope, actor_id=request.user.pk, department_id=dep)); return owner, owner.asset_id, str(owner)
    if owner_type == InventoryDocumentOwnerType.MOVEMENT:
        scope, dep = movement_scope(request); owner = selector_or_404(lambda: MovementSelectors.obtener(owner_id, scope=scope, actor_id=request.user.pk, department_id=dep)); return owner, owner.asset_id, str(owner)
    if owner_type == InventoryDocumentOwnerType.MOVEMENT_REQUEST:
        owner = _movement_request(request, owner_id); return owner, owner.asset_id, str(owner)
    if owner_type == InventoryDocumentOwnerType.DISPOSAL_REQUEST:
        owner = _disposal(request, owner_id); return owner, owner.asset_id, str(owner)
    if owner_type == InventoryDocumentOwnerType.PHYSICAL_AUDIT_SESSION:
        owner = _physical_audit(request, owner_id); return owner, None, str(owner)
    raise PermissionDenied("Este expediente no admite carga documental desde esta vista.")


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="has_access_module")
def document_upload_view(request, owner_type, owner_id):
    owner_type = str(owner_type).strip().upper()
    owner, asset_id, owner_label = _document_owner_context(request, owner_type, owner_id)
    generated_type = _document_generated_type(request)
    upload_permission = "can_manage_documents"
    manages_documents = has_any_permission(request, "can_manage_documents")
    loan_acknowledgement_upload = False
    if owner_type == InventoryDocumentOwnerType.LOAN:
        current_department = str(department_id(request) or "")
        if generated_type == DocumentType.LOAN_RECEIPT:
            loan_acknowledgement_upload = bool(
                has_any_permission(
                    request,
                    "can_request_loans",
                    "can_manage_loans",
                )
                and current_department
                == str(owner.origin_dependencia_id or "")
            )
            if loan_acknowledgement_upload and not manages_documents:
                upload_permission = (
                    "can_request_loans"
                    if has_any_permission(request, "can_request_loans")
                    else "can_manage_loans"
                )
        elif generated_type == DocumentType.RETURN_RECEIPT:
            loan_acknowledgement_upload = bool(
                has_any_permission(request, "can_authorize_loans")
                and current_department
                == str(owner.destination_dependencia_id or "")
            )
            if loan_acknowledgement_upload and not manages_documents:
                upload_permission = "can_authorize_loans"
    if not loan_acknowledgement_upload and not manages_documents:
        raise PermissionDenied(
            "No cuenta con autorización para agregar documentos a este expediente."
        )
    acknowledgement_spec = None
    if generated_type:
        try:
            acknowledgement_spec = get_acknowledgement_spec(
                generated_type,
                owner_type,
            )
        except ValueError:
            acknowledgement_spec = None
    form_data = request.POST.copy() if request.method == "POST" else None
    if acknowledgement_spec and form_data is not None:
        form_data["document_type"] = acknowledgement_spec.acknowledgement_type
        form_data["is_required_evidence"] = "on"
    form = ContextDocumentUploadForm(
        form_data,
        request.FILES or None,
        owner_type=owner_type,
        owner_id=owner.id,
    )
    if acknowledgement_spec:
        form.fields["ack_for"] = forms.CharField(
            initial=generated_type,
            required=False,
            widget=forms.HiddenInput(),
        )
        form.fields["document_type"].initial = (
            acknowledgement_spec.acknowledgement_type
        )
        form.fields["document_type"].widget = forms.HiddenInput()
        owner_folio = getattr(owner, "folio", str(owner))
        form.fields["title"].initial = (
            f"{acknowledgement_spec.acknowledgement_label} {owner_folio}"
        )
        form.fields["external_reference"].initial = owner_folio
        form.fields["is_required_evidence"].initial = True
    if request.method == "POST" and form.is_valid():
        document = run_service(form, lambda: upload_inventory_document(data=form.to_dto(), actor_id=request.user.pk, authorized_owner=owner, request=request, required_permission=upload_permission))
        if document:
            success(request, "Documento agregado y enviado a validación.")
            if owner_type == InventoryDocumentOwnerType.LOAN:
                return redirect(_loan_url(owner.id))
            if owner_type == InventoryDocumentOwnerType.CUSTODY_DOCUMENT:
                return redirect(
                    "inventory:custody_document_detail",
                    document_id=owner.id,
                )
            return redirect(reverse("inventory:document_list") + f"?owner_type={owner_type}&owner_id={owner.id}")
    return render_inventory(request, page="inventory/pages/document_form.html", content="inventory/content/document_form_content.html", context={"current_inventory_view":"inventory:document_list", "form":form, "owner_label":owner_label, "owner_type_label":dict(InventoryDocumentOwnerType.choices).get(owner_type, owner_type)}, status=422 if request.method == "POST" else 200)


def _loan_acknowledgement_confirmation(request, document):
    if (
        document.owner_type != InventoryDocumentOwnerType.LOAN
        or document.document_type not in {
            DocumentType.SIGNED_LOAN_RECEIPT,
            DocumentType.SIGNED_RETURN_RECEIPT,
        }
    ):
        return None
    loan = _loan(request, document.owner_id)
    if is_inventory_root(request):
        return loan, "can_validate_documents"
    current_department = str(department_id(request) or "")
    if loan.external_borrower:
        if has_any_permission(request, "can_validate_documents"):
            return loan, "can_validate_documents"
        return None
    if (
        document.document_type == DocumentType.SIGNED_LOAN_RECEIPT
        and has_any_permission(request, "can_authorize_loans")
        and current_department == str(loan.destination_dependencia_id or "")
    ):
        return loan, "can_authorize_loans"
    if (
        document.document_type == DocumentType.SIGNED_RETURN_RECEIPT
        and current_department == str(loan.origin_dependencia_id or "")
    ):
        if has_any_permission(request, "can_request_loans"):
            return loan, "can_request_loans"
        if has_any_permission(request, "can_manage_loans"):
            return loan, "can_manage_loans"
    return None


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="has_access_module")
def document_download_view(request, document_id):
    loan_document = AssetDocument.objects.filter(
        pk=document_id,
        is_deleted=False,
        owner_type=InventoryDocumentOwnerType.LOAN,
    ).first()
    if loan_document:
        _loan(request, loan_document.owner_id)
        document = loan_document
    else:
        scope, dep = asset_scope(request)
        document = selector_or_404(lambda: DocumentSelectors.obtener_documento(document_id, scope=scope, actor_id=request.user.pk, department_id=dep, include_restricted=has_any_permission(request,"can_view_restricted_documents")))
    return FileResponse(document.file.open("rb"), as_attachment=False, filename=document.original_filename)


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="has_access_module")
def document_validate_view(request, document_id):
    document = selector_or_404(
        lambda: AssetDocument.objects.filter(
            pk=document_id,
            is_deleted=False,
            is_current_version=True,
        ).first()
    )
    loan_confirmation = _loan_acknowledgement_confirmation(request, document)
    if document.owner_type == InventoryDocumentOwnerType.LOAN:
        if not loan_confirmation:
            raise PermissionDenied(
                "El acuse debe ser confirmado por la dependencia contraparte."
            )
        if (
            document.uploaded_by_id == request.user.pk
            and not is_inventory_root(request)
        ):
            raise PermissionDenied(
                "Quien integró el acuse no puede confirmar su propia evidencia."
            )
        loan, required_permission = loan_confirmation
    else:
        require_any_permission(request, "can_validate_documents")
        scope, dep = asset_scope(request)
        document = selector_or_404(lambda: DocumentSelectors.obtener_documento(document_id, scope=scope, actor_id=request.user.pk, department_id=dep, include_restricted=True))
        loan = None
        required_permission = "can_validate_documents"
    form = DocumentValidationResolveForm(request.POST or None)
    if not getattr(request, "axentra_is_root", False):
        form.fields.pop("bypass_reason", None)
    if request.method == "POST" and form.is_valid():
        result = run_service(form, lambda: resolve_inventory_document(document_id=document.id, data=form.to_dto(), actor_id=request.user.pk, request=request, required_permission=required_permission))
        if result:
            success(request, "Confirmación documental registrada.")
            if loan:
                return redirect(_loan_url(loan.id))
            return redirect("inventory:document_list")
    return render_inventory(request, page="inventory/pages/document_form.html", content="inventory/content/document_form_content.html", context={"current_inventory_view":"inventory:loan_list" if loan else "inventory:document_list", "form":form, "form_title":"Confirmar acuse" if loan else "Validar documento", "owner_label":document.title, "owner_type_label":"Confirmación de la contraparte" if loan else "Validación documental", "document_review_url":reverse("inventory:document_download", kwargs={"document_id":document.id})}, status=422 if request.method == "POST" else 200)


def _physical_audit(request, session_id):
    scope, scope_department_id = physical_audit_scope(request)
    return selector_or_404(lambda: PhysicalAuditSelectors.session_detail(
        session_id, scope=scope, actor_id=request.user.pk,
        department_id=scope_department_id,
    ))


def _physical_audit_url(session_id):
    return reverse("inventory:physical_audit_detail", kwargs={"session_id": session_id})


def _physical_audit_context(request, session):
    manages = has_any_permission(request, "can_manage_physical_audits")
    scans = has_any_permission(request, "can_scan_physical_audits")
    scope, scope_department_id = physical_audit_scope(request)
    context = {
        "audit_session": session,
        "result_totals": PhysicalAuditSelectors.result_totals(
            session.id, scope=scope, actor_id=request.user.pk,
            department_id=scope_department_id,
        ),
        "can_freeze_audit": manages and session.status in {"DRAFT", "PREPARING"},
        "can_start_audit": manages and session.status == "FROZEN",
        "can_scan_audit": scans and session.status == "IN_PROGRESS",
        "can_reconcile_audit": manages and session.status == "IN_PROGRESS",
        "can_close_audit": manages and session.status == "RECONCILIATION",
        "can_cancel_audit": manages and session.status not in {"CLOSED", "CANCELLED"},
    }
    if session.status == "CLOSED":
        context["audit_acknowledgement"] = get_acknowledgement_state(
            owner_type=InventoryDocumentOwnerType.PHYSICAL_AUDIT_SESSION,
            owner_id=session.id,
            generated_type="PHYSICAL_AUDIT_REPORT",
        )
    return context


def _require_physical_audit_operator(request):
    require_any_permission(
        request,
        "can_manage_physical_audits",
        "can_scan_physical_audits",
    )


@require_GET
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="has_access_module")
def physical_audit_directory_departments_view(request):
    _require_physical_audit_operator(request)
    site_id = request.GET.get("site_id", "").strip() or None
    return _custody_options(
        (item.id, f"{item.code or 'SIN-CÓDIGO'} · {item.name}")
        for item in CoreDirectorySelectors.departments(site_id=site_id)
    )


@require_GET
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="has_access_module")
def physical_audit_directory_areas_view(request):
    _require_physical_audit_operator(request)
    site_id = request.GET.get("site_id", "").strip() or None
    selected_department = request.GET.get("department_id", "").strip() or None
    return _custody_options(
        (item.id, f"{item.name} [{item.site_name}]")
        for item in CoreDirectorySelectors.areas(
            site_id=site_id,
            department_id=selected_department,
        )
    )


@require_GET
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="has_access_module")
def physical_audit_directory_users_view(request):
    _require_physical_audit_operator(request)
    selected_department = request.GET.get("department_id", "").strip() or None
    area_id = request.GET.get("area_id", "").strip() or None
    return _custody_options(
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
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="has_access_module")
def physical_audit_eligible_assets_view(request):
    _require_physical_audit_operator(request)
    site_id = request.GET.get("site_id", "").strip() or None
    department_id_value = request.GET.get("department_id", "").strip() or None
    queryset = PhysicalAuditSelectors.eligible_assets(
        site_id=site_id,
        department_id=department_id_value,
    )
    return JsonResponse({"total": queryset.count()})


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="has_access_module")
def physical_audit_list_view(request):
    require_any_permission(request, "can_manage_physical_audits", "can_scan_physical_audits")
    f = _filters(request, "q", "status", "department_id", "site_id", "fiscal_year")
    tab = request.GET.get("tab", "active").strip().lower()
    if tab not in {"active", "history"}:
        tab = "active"
    scope, scope_department_id = physical_audit_scope(request)
    sessions = PhysicalAuditSelectors.sessions(**f, scope=scope, actor_id=request.user.pk, scope_department_id=scope_department_id)
    if tab == "history":
        sessions = sessions.filter(status__in={"CLOSED", "CANCELLED"})
        statuses = [(value, label) for value, label in PhysicalAuditSelectors.status_choices() if value in {"CLOSED", "CANCELLED"}]
    else:
        sessions = sessions.exclude(status__in={"CLOSED", "CANCELLED"})
        statuses = [(value, label) for value, label in PhysicalAuditSelectors.status_choices() if value not in {"CLOSED", "CANCELLED"}]
    directory_choices = CoreDirectorySelectors.form_choices()
    return render_inventory(request, page="inventory/pages/physical_audit_list.html", content="inventory/content/physical_audit_list_content.html", context={"current_inventory_view":"inventory:physical_audit_list", "audit_sessions":sessions, "statuses":statuses, "tab":tab, "site_choices":directory_choices["site_choices"], "department_choices":directory_choices["department_choices"], "can_create_audit":has_any_permission(request, "can_manage_physical_audits"), **f})


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_manage_physical_audits")
def physical_audit_create_view(request):
    form = apply_directory_choices(PhysicalAuditCreateForm(request.POST or None))
    if request.method == "POST" and form.is_valid():
        session = run_service(form, lambda: create_physical_audit(data=form.to_dto(), actor_id=request.user.pk))
        if session:
            success(request, "Auditoría física creada en borrador.")
            return redirect(_physical_audit_url(session.id))
    return render_inventory(request, page="inventory/pages/physical_audit_action_form.html", content="inventory/content/physical_audit_action_form_content.html", context={"current_inventory_view":"inventory:physical_audit_list", "form":form, "form_title":"Nueva auditoría física"}, status=422 if request.method == "POST" else 200)


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="has_access_module")
def physical_audit_detail_view(request, session_id):
    require_any_permission(request, "can_manage_physical_audits", "can_scan_physical_audits")
    session = _physical_audit(request, session_id)
    return render_inventory(request, page="inventory/pages/physical_audit_detail.html", content="inventory/content/physical_audit_detail_content.html", context={"current_inventory_view":"inventory:physical_audit_list", **_physical_audit_context(request, session)})


def _physical_audit_action(request, session_id, form_class, callback, title, *, choices=False):
    session = _physical_audit(request, session_id)
    form = form_class(request.POST or None)
    if choices:
        form = apply_directory_choices(form)
    if request.method == "POST" and form.is_valid():
        result = run_service(form, lambda: callback(session, form))
        if result:
            success(request, title)
            return redirect(_physical_audit_url(session.id))
    return render_inventory(request, page="inventory/pages/physical_audit_action_form.html", content="inventory/content/physical_audit_action_form_content.html", context={"current_inventory_view":"inventory:physical_audit_list", "audit_session":session, "form":form, "form_title":title}, status=422 if request.method == "POST" else 200)


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_manage_physical_audits")
def physical_audit_freeze_view(request, session_id):
    return _physical_audit_action(request, session_id, PhysicalAuditFreezeForm, lambda s, f: freeze_physical_audit(session_id=s.id, data=f.to_dto(), actor_id=request.user.pk), "Inventario esperado congelado.")


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_manage_physical_audits")
def physical_audit_start_view(request, session_id):
    return _physical_audit_action(request, session_id, PhysicalAuditStartForm, lambda s, f: start_physical_audit(session_id=s.id, data=f.to_dto(), actor_id=request.user.pk), "Levantamiento físico iniciado.")


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_scan_physical_audits")
def physical_audit_scan_view(request, session_id):
    return _physical_audit_action(request, session_id, PhysicalAuditScanForm, lambda s, f: scan_physical_audit_item(session_id=s.id, data=f.to_dto(), actor_id=request.user.pk), "Lectura registrada.", choices=True)


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_scan_physical_audits")
def physical_audit_unlisted_view(request, session_id):
    return _physical_audit_action(request, session_id, PhysicalAuditUnlistedItemForm, lambda s, f: register_unlisted_audit_item(session_id=s.id, data=f.to_dto(), actor_id=request.user.pk), "Sobrante no registrado agregado.", choices=True)


@require_POST
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_manage_physical_audits")
def physical_audit_reconciliation_view(request, session_id):
    session = _physical_audit(request, session_id)
    begin_physical_audit_reconciliation(session_id=session.id, actor_id=request.user.pk)
    success(request, "La auditoría pasó a conciliación.")
    return redirect(_physical_audit_url(session.id))


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_manage_physical_audits")
def physical_audit_not_found_view(request, session_id, item_id):
    session = _physical_audit(request, session_id)
    item = selector_or_404(lambda: session.items.get(pk=item_id, is_deleted=False))
    form = PhysicalAuditNotFoundForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        result = run_service(form, lambda: mark_audit_item_not_found(item_id=item.id, data=form.to_dto(), actor_id=request.user.pk))
        if result:
            success(request, "Activo marcado como no localizado.")
            return redirect(_physical_audit_url(session.id))
    return render_inventory(request, page="inventory/pages/physical_audit_action_form.html", content="inventory/content/physical_audit_action_form_content.html", context={"current_inventory_view":"inventory:physical_audit_list", "audit_session":session, "audit_item":item, "form":form, "form_title":"Marcar activo no localizado"}, status=422 if request.method == "POST" else 200)


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_manage_physical_audits")
def physical_audit_pending_not_found_view(request, session_id):
    session = _physical_audit(request, session_id)
    form = PhysicalAuditNotFoundForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        result = run_service(form, lambda: mark_pending_audit_items_not_found(
            session_id=session.id,
            reason=form.to_dto().reason,
            actor_id=request.user.pk,
        ))
        if result is not None:
            success(request, f"{result} bienes pendientes fueron marcados como no localizados.")
            return redirect(_physical_audit_url(session.id))
    return render_inventory(request, page="inventory/pages/physical_audit_action_form.html", content="inventory/content/physical_audit_action_form_content.html", context={"current_inventory_view":"inventory:physical_audit_list", "audit_session":session, "form":form, "form_title":"Cerrar bienes pendientes como no localizados"}, status=422 if request.method == "POST" else 200)


def _physical_audit_evidence_target(session, item_id=None):
    if item_id is None:
        return InventoryDocumentOwnerType.PHYSICAL_AUDIT_SESSION, session.id, None
    item = selector_or_404(lambda: session.items.get(pk=item_id, is_deleted=False))
    return InventoryDocumentOwnerType.PHYSICAL_AUDIT_ITEM, item.id, item


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="has_access_module")
def physical_audit_document_upload_view(request, session_id, item_id=None):
    _require_physical_audit_operator(request)
    session = _physical_audit(request, session_id)
    owner_type, owner_id, item = _physical_audit_evidence_target(session, item_id)
    form = PhysicalAuditDocumentUploadForm(
        request.POST or None, request.FILES or None,
        owner_type=owner_type, owner_id=owner_id,
    )
    if request.method == "POST" and form.is_valid():
        result = run_service(form, lambda: upload_physical_audit_document(
            data=form.to_dto(), actor_id=request.user.pk,
        ))
        if result:
            success(request, "Documento de evidencia agregado.")
            return redirect(_physical_audit_url(session.id))
    return render_inventory(request, page="inventory/pages/physical_audit_action_form.html", content="inventory/content/physical_audit_action_form_content.html", context={"current_inventory_view":"inventory:physical_audit_list", "audit_session":session, "audit_item":item, "form":form, "form_title":"Agregar documento de evidencia"}, status=422 if request.method == "POST" else 200)


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="has_access_module")
def physical_audit_photo_upload_view(request, session_id, item_id=None):
    _require_physical_audit_operator(request)
    session = _physical_audit(request, session_id)
    owner_type, owner_id, item = _physical_audit_evidence_target(session, item_id)
    form = PhysicalAuditPhotoUploadForm(
        request.POST or None, request.FILES or None,
        owner_type=owner_type, owner_id=owner_id,
    )
    if request.method == "POST" and form.is_valid():
        result = run_service(form, lambda: upload_physical_audit_photo(
            data=form.to_dto(), actor_id=request.user.pk,
        ))
        if result:
            success(request, "Fotografía de evidencia agregada.")
            return redirect(_physical_audit_url(session.id))
    return render_inventory(request, page="inventory/pages/physical_audit_action_form.html", content="inventory/content/physical_audit_action_form_content.html", context={"current_inventory_view":"inventory:physical_audit_list", "audit_session":session, "audit_item":item, "form":form, "form_title":"Agregar fotografía de evidencia"}, status=422 if request.method == "POST" else 200)


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="has_access_module")
def physical_audit_report_view(request, session_id):
    _require_physical_audit_operator(request)
    session = _physical_audit(request, session_id)
    item_ids = session.items.filter(is_deleted=False).values_list("id", flat=True)
    documents = AssetDocument.objects.filter(
        is_deleted=False,
        owner_type__in={InventoryDocumentOwnerType.PHYSICAL_AUDIT_SESSION, InventoryDocumentOwnerType.PHYSICAL_AUDIT_ITEM},
    ).filter(Q(owner_id=session.id) | Q(owner_id__in=item_ids))
    photos = AssetPhoto.objects.filter(
        is_deleted=False,
        owner_type__in={InventoryDocumentOwnerType.PHYSICAL_AUDIT_SESSION, InventoryDocumentOwnerType.PHYSICAL_AUDIT_ITEM},
    ).filter(Q(owner_id=session.id) | Q(owner_id__in=item_ids))
    return render(request, "inventory/reports/physical_audit_report.html", {
        "audit_session": session,
        "documents": documents,
        "photos": photos,
    })


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_manage_physical_audits")
def physical_audit_item_reconcile_view(request, session_id, item_id):
    session = _physical_audit(request, session_id)
    item = selector_or_404(lambda: session.items.get(pk=item_id, is_deleted=False))
    form = PhysicalAuditReconcileForm(request.POST or None, initial={"result":item.result})
    if request.method == "POST" and form.is_valid():
        result = run_service(form, lambda: reconcile_physical_audit_item(item_id=item.id, data=form.to_dto(), actor_id=request.user.pk))
        if result:
            success(request, "Hallazgo conciliado.")
            return redirect(_physical_audit_url(session.id))
    return render_inventory(request, page="inventory/pages/physical_audit_action_form.html", content="inventory/content/physical_audit_action_form_content.html", context={"current_inventory_view":"inventory:physical_audit_list", "audit_session":session, "audit_item":item, "form":form, "form_title":"Conciliar hallazgo"}, status=422 if request.method == "POST" else 200)


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_manage_physical_audits")
def physical_audit_close_view(request, session_id):
    return _physical_audit_action(request, session_id, PhysicalAuditCloseForm, lambda s, f: close_physical_audit(session_id=s.id, data=f.to_dto(), actor_id=request.user.pk), "Auditoría física cerrada.")


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_manage_physical_audits")
def physical_audit_cancel_view(request, session_id):
    return _physical_audit_action(request, session_id, PhysicalAuditCancelForm, lambda s, f: cancel_physical_audit(session_id=s.id, data=f.to_dto(), actor_id=request.user.pk), "Auditoría física cancelada.")


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_view_financials")
def financial_dashboard_view(request):
    return render_inventory(request, page="inventory/pages/financial_dashboard.html", content="inventory/content/financial_dashboard_content.html", context={
        "current_inventory_view":"inventory:financial_dashboard",
        "policies":FinancialSelectors.depreciation_policies(),
        "runs":FinancialSelectors.depreciation_runs()[:20],
        "exports":FinancialSelectors.export_batches()[:20],
        "reconciliations":FinancialSelectors.reconciliations()[:20],
    })
