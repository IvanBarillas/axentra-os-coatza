"""Vistas de consulta de expedientes secundarios de Inventory.

Las vistas resuelven permisos y contexto organizacional. Los selectores aplican
el alcance efectivo a listados, detalles y agregados. Las transiciones de
escritura se conectarán mediante servicios específicos.
"""

from django.core.exceptions import PermissionDenied

from apps.inventory.integrations import core_directory
from apps.inventory.selectors import (
    CustodyScope,
    CustodySelectors,
    DisposalSelectors,
    DocumentScope,
    DocumentSelectors,
    FinancialScope,
    FinancialSelectors,
    LoanSelectors,
    MovementSelectors,
    PhysicalAuditSelectors,
    PhysicalAuditVisibilityScope,
    RegistryScope,
)
from apps.security.decorators import axentra_gate_enforcer
from apps.shared.apps_config import AppIdentifier

from .common import render_inventory, selector_or_404


MODULE_PERMISSION = "has_access_module"


def _filters(request, *names):
    return {
        name: str(request.GET.get(name, "")).strip()
        for name in names
    }


def _permissions(request):
    return {
        str(permission).strip()
        for permission in (
            getattr(request, "axentra_permissions_list", None) or []
        )
        if str(permission).strip()
    }


def _is_root(request):
    user = request.user
    return bool(
        getattr(request, "axentra_is_root", False)
        or getattr(user, "is_superuser", False)
        or getattr(user, "is_manager", False)
    )


def _has_any_permission(request, *required_permissions):
    if _is_root(request):
        return True

    granted = _permissions(request)
    return any(permission in granted for permission in required_permissions)


def _require_any_permission(request, *required_permissions):
    if not _has_any_permission(request, *required_permissions):
        raise PermissionDenied(
            "No cuentas con permisos para consultar este expediente."
        )


def _organizational_context(request):
    """Resuelve una sola vez la adscripción mediante el adaptador del Core."""

    cache_attribute = "_inventory_organizational_context"
    if hasattr(request, cache_attribute):
        return getattr(request, cache_attribute)

    try:
        context = core_directory.get_user_organizational_context(
            request.user.pk,
            require_profile=False,
        )
    except core_directory.CoreDirectoryError:
        context = None

    setattr(request, cache_attribute, context)
    return context


def _department_id(request):
    context = _organizational_context(request)
    return context.department_id if context else None


def _render(request, *, page, content, current_view, context):
    return render_inventory(
        request,
        page=page,
        content=content,
        context={
            "current_inventory_view": current_view,
            **context,
        },
    )


# =============================================================================
# RESGUARDOS
# =============================================================================

def _custody_scope(request):
    if _is_root(request) or _has_any_permission(request, "can_manage_custody"):
        return CustodyScope.GLOBAL, None

    return CustodyScope.OWN, None


@axentra_gate_enforcer(
    AppIdentifier.INVENTORY,
    required_fine_permission=MODULE_PERMISSION,
)
def custody_list_view(request):
    _require_any_permission(
        request,
        "can_manage_custody",
        "can_accept_custody",
    )

    filters = _filters(
        request,
        "q",
        "status",
        "asset_id",
        "assigned_to_id",
        "department_id",
    )
    scope, scope_department_id = _custody_scope(request)

    custodies = CustodySelectors.listar(
        **filters,
        scope=scope,
        actor_id=request.user.pk,
        scope_department_id=scope_department_id,
    )

    return _render(
        request,
        page="inventory/pages/custody_list.html",
        content="inventory/content/custody_list_content.html",
        current_view="inventory:custody_list",
        context={
            "custodies": custodies,
            "inventory_scope": scope,
            **filters,
        },
    )


@axentra_gate_enforcer(
    AppIdentifier.INVENTORY,
    required_fine_permission=MODULE_PERMISSION,
)
def custody_detail_view(request, custody_id):
    _require_any_permission(
        request,
        "can_manage_custody",
        "can_accept_custody",
    )
    scope, department_id = _custody_scope(request)

    custody = selector_or_404(
        lambda: CustodySelectors.obtener(
            custody_id,
            scope=scope,
            actor_id=request.user.pk,
            department_id=department_id,
        )
    )

    return _render(
        request,
        page="inventory/pages/custody_detail.html",
        content="inventory/content/custody_detail_content.html",
        current_view="inventory:custody_list",
        context={"custody": custody, "inventory_scope": scope},
    )


# =============================================================================
# MOVIMIENTOS
# =============================================================================

def _movement_scope(request):
    if _is_root(request) or _has_any_permission(request, "can_manage_movements"):
        return RegistryScope.GLOBAL, None

    department_id = _department_id(request)
    if department_id:
        return RegistryScope.DEPARTMENT, department_id

    return RegistryScope.OWN, None


@axentra_gate_enforcer(
    AppIdentifier.INVENTORY,
    required_fine_permission=MODULE_PERMISSION,
)
def movement_list_view(request):
    _require_any_permission(
        request,
        "can_manage_movements",
        "can_authorize_movements",
    )
    filters = _filters(request, "q", "asset_id", "movement_type")
    scope, department_id = _movement_scope(request)

    movements = MovementSelectors.listar(
        **filters,
        scope=scope,
        actor_id=request.user.pk,
        scope_department_id=department_id,
    )

    return _render(
        request,
        page="inventory/pages/movement_list.html",
        content="inventory/content/movement_list_content.html",
        current_view="inventory:movement_list",
        context={
            "movements": movements,
            "inventory_scope": scope,
            **filters,
        },
    )


@axentra_gate_enforcer(
    AppIdentifier.INVENTORY,
    required_fine_permission=MODULE_PERMISSION,
)
def movement_detail_view(request, movement_id):
    _require_any_permission(
        request,
        "can_manage_movements",
        "can_authorize_movements",
    )
    scope, department_id = _movement_scope(request)

    movement = selector_or_404(
        lambda: MovementSelectors.obtener(
            movement_id,
            scope=scope,
            actor_id=request.user.pk,
            department_id=department_id,
        )
    )

    return _render(
        request,
        page="inventory/pages/movement_detail.html",
        content="inventory/content/movement_detail_content.html",
        current_view="inventory:movement_list",
        context={"movement": movement, "inventory_scope": scope},
    )


# =============================================================================
# PRÉSTAMOS
# =============================================================================

def _loan_scope(request):
    if _is_root(request) or _has_any_permission(request, "can_manage_loans"):
        return RegistryScope.GLOBAL, None

    if _has_any_permission(request, "can_authorize_loans"):
        department_id = _department_id(request)
        if department_id:
            return RegistryScope.DEPARTMENT, department_id

    return RegistryScope.OWN, None


@axentra_gate_enforcer(
    AppIdentifier.INVENTORY,
    required_fine_permission=MODULE_PERMISSION,
)
def loan_list_view(request):
    _require_any_permission(
        request,
        "can_request_loans",
        "can_manage_loans",
        "can_authorize_loans",
    )
    filters = _filters(request, "q", "status", "asset_id", "borrower_id")
    filters["overdue"] = request.GET.get("overdue") == "1"
    scope, department_id = _loan_scope(request)

    loans = LoanSelectors.listar(
        **filters,
        scope=scope,
        actor_id=request.user.pk,
        scope_department_id=department_id,
    )

    return _render(
        request,
        page="inventory/pages/loan_list.html",
        content="inventory/content/loan_list_content.html",
        current_view="inventory:loan_list",
        context={
            "loans": loans,
            "inventory_scope": scope,
            **filters,
        },
    )


@axentra_gate_enforcer(
    AppIdentifier.INVENTORY,
    required_fine_permission=MODULE_PERMISSION,
)
def loan_detail_view(request, loan_id):
    _require_any_permission(
        request,
        "can_request_loans",
        "can_manage_loans",
        "can_authorize_loans",
    )
    scope, department_id = _loan_scope(request)

    loan = selector_or_404(
        lambda: LoanSelectors.obtener(
            loan_id,
            scope=scope,
            actor_id=request.user.pk,
            department_id=department_id,
        )
    )

    return _render(
        request,
        page="inventory/pages/loan_detail.html",
        content="inventory/content/loan_detail_content.html",
        current_view="inventory:loan_list",
        context={"loan": loan, "inventory_scope": scope},
    )


# =============================================================================
# BAJAS
# =============================================================================

def _disposal_scope(request):
    if _is_root(request) or _has_any_permission(
        request,
        "can_manage_disposals",
        "can_authorize_disposals",
        "can_execute_disposals",
    ):
        return RegistryScope.GLOBAL, None

    return RegistryScope.OWN, None


@axentra_gate_enforcer(
    AppIdentifier.INVENTORY,
    required_fine_permission=MODULE_PERMISSION,
)
def disposal_list_view(request):
    _require_any_permission(
        request,
        "can_request_disposals",
        "can_manage_disposals",
        "can_authorize_disposals",
        "can_execute_disposals",
    )
    filters = _filters(request, "q", "status", "asset_id", "reason")
    scope, department_id = _disposal_scope(request)

    disposals = DisposalSelectors.listar(
        **filters,
        scope=scope,
        actor_id=request.user.pk,
        scope_department_id=department_id,
    )

    return _render(
        request,
        page="inventory/pages/disposal_list.html",
        content="inventory/content/disposal_list_content.html",
        current_view="inventory:disposal_list",
        context={
            "disposals": disposals,
            "inventory_scope": scope,
            **filters,
        },
    )


@axentra_gate_enforcer(
    AppIdentifier.INVENTORY,
    required_fine_permission=MODULE_PERMISSION,
)
def disposal_detail_view(request, disposal_id):
    _require_any_permission(
        request,
        "can_request_disposals",
        "can_manage_disposals",
        "can_authorize_disposals",
        "can_execute_disposals",
    )
    scope, department_id = _disposal_scope(request)

    disposal = selector_or_404(
        lambda: DisposalSelectors.obtener(
            disposal_id,
            scope=scope,
            actor_id=request.user.pk,
            department_id=department_id,
        )
    )

    include_restricted = _is_root(request) or _has_any_permission(
        request,
        "can_view_restricted_documents",
    )
    documents = DocumentSelectors.documents(
        owner_type="DISPOSAL_REQUEST",
        owner_id=disposal.id,
        scope=DocumentScope.GLOBAL,
        include_restricted=include_restricted,
    )

    return _render(
        request,
        page="inventory/pages/disposal_detail.html",
        content="inventory/content/disposal_detail_content.html",
        current_view="inventory:disposal_list",
        context={
            "disposal": disposal,
            "documents": documents,
            "inventory_scope": scope,
        },
    )


# =============================================================================
# DOCUMENTOS
# =============================================================================

def _document_scope(request):
    if _is_root(request) or _has_any_permission(
        request,
        "can_validate_documents",
        "can_view_restricted_documents",
    ):
        return DocumentScope.GLOBAL, None

    return DocumentScope.OWN, None


@axentra_gate_enforcer(
    AppIdentifier.INVENTORY,
    required_fine_permission=MODULE_PERMISSION,
)
def document_list_view(request):
    _require_any_permission(
        request,
        "can_manage_documents",
        "can_validate_documents",
        "can_view_restricted_documents",
    )
    filters = _filters(
        request,
        "owner_type",
        "owner_id",
        "document_type",
        "validation_status",
        "q",
    )
    scope, department_id = _document_scope(request)
    include_restricted = _is_root(request) or _has_any_permission(
        request,
        "can_view_restricted_documents",
    )

    documents = DocumentSelectors.documents(
        **filters,
        scope=scope,
        actor_id=request.user.pk,
        scope_department_id=department_id,
        include_restricted=include_restricted,
    )

    return _render(
        request,
        page="inventory/pages/document_list.html",
        content="inventory/content/document_list_content.html",
        current_view="inventory:document_list",
        context={
            "documents": documents,
            "inventory_scope": scope,
            "include_restricted": include_restricted,
            **filters,
        },
    )


# =============================================================================
# AUDITORÍA FÍSICA
# =============================================================================

def _physical_audit_scope(request):
    if _is_root(request) or _has_any_permission(
        request,
        "can_manage_physical_audits",
    ):
        return PhysicalAuditVisibilityScope.GLOBAL, None

    department_id = _department_id(request)
    if department_id:
        return PhysicalAuditVisibilityScope.DEPARTMENT, department_id

    return PhysicalAuditVisibilityScope.OWN, None


@axentra_gate_enforcer(
    AppIdentifier.INVENTORY,
    required_fine_permission=MODULE_PERMISSION,
)
def physical_audit_list_view(request):
    _require_any_permission(
        request,
        "can_manage_physical_audits",
        "can_scan_physical_audits",
        "can_view_audit",
    )
    filters = _filters(request, "q", "status", "department_id")
    scope, department_id = _physical_audit_scope(request)

    sessions = PhysicalAuditSelectors.sessions(
        **filters,
        scope=scope,
        actor_id=request.user.pk,
        scope_department_id=department_id,
    )

    return _render(
        request,
        page="inventory/pages/physical_audit_list.html",
        content="inventory/content/physical_audit_list_content.html",
        current_view="inventory:physical_audit_list",
        context={
            "audit_sessions": sessions,
            "inventory_scope": scope,
            **filters,
        },
    )


@axentra_gate_enforcer(
    AppIdentifier.INVENTORY,
    required_fine_permission=MODULE_PERMISSION,
)
def physical_audit_detail_view(request, session_id):
    _require_any_permission(
        request,
        "can_manage_physical_audits",
        "can_scan_physical_audits",
        "can_view_audit",
    )
    scope, department_id = _physical_audit_scope(request)

    audit_session = selector_or_404(
        lambda: PhysicalAuditSelectors.session_detail(
            session_id,
            scope=scope,
            actor_id=request.user.pk,
            department_id=department_id,
        )
    )
    result_totals = PhysicalAuditSelectors.result_totals(
        audit_session.id,
        scope=scope,
        actor_id=request.user.pk,
        department_id=department_id,
    )

    return _render(
        request,
        page="inventory/pages/physical_audit_detail.html",
        content="inventory/content/physical_audit_detail_content.html",
        current_view="inventory:physical_audit_list",
        context={
            "audit_session": audit_session,
            "result_totals": result_totals,
            "inventory_scope": scope,
        },
    )


# =============================================================================
# FINANZAS Y CONCILIACIÓN
# =============================================================================

def _financial_scope(request):
    if _is_root(request) or _has_any_permission(
        request,
        "can_run_depreciation",
        "can_post_depreciation",
        "can_manage_reconciliation",
    ):
        return FinancialScope.GLOBAL, None

    department_id = _department_id(request)
    if department_id:
        return FinancialScope.DEPARTMENT, department_id

    return FinancialScope.OWN, None


@axentra_gate_enforcer(
    AppIdentifier.INVENTORY,
    required_fine_permission=MODULE_PERMISSION,
)
def financial_dashboard_view(request):
    _require_any_permission(
        request,
        "can_view_financials",
        "can_run_depreciation",
        "can_post_depreciation",
        "can_manage_reconciliation",
        "can_export_reports",
    )
    scope, department_id = _financial_scope(request)

    return _render(
        request,
        page="inventory/pages/financial_dashboard.html",
        content="inventory/content/financial_dashboard_content.html",
        current_view="inventory:financial_dashboard",
        context={
            "inventory_scope": scope,
            "policies": FinancialSelectors.depreciation_policies(),
            "records": FinancialSelectors.depreciation_records(
                scope=scope,
                actor_id=request.user.pk,
                scope_department_id=department_id,
            )[:20],
            "runs": FinancialSelectors.depreciation_runs(
                scope=scope,
            )[:20],
            "exports": FinancialSelectors.export_batches(
                scope=scope,
            )[:20],
            "reconciliations": FinancialSelectors.reconciliations(
                scope=scope,
            )[:20],
        },
    )


__all__ = [
    "custody_detail_view",
    "custody_list_view",
    "disposal_detail_view",
    "disposal_list_view",
    "document_list_view",
    "financial_dashboard_view",
    "loan_detail_view",
    "loan_list_view",
    "movement_detail_view",
    "movement_list_view",
    "physical_audit_detail_view",
    "physical_audit_list_view",
]

