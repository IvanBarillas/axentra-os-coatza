"""Vistas de consulta para expedientes cuyo flujo de escritura se conecta después."""

from apps.inventory.selectors import (
    CustodySelectors, DisposalSelectors, DocumentSelectors, FinancialSelectors,
    LoanSelectors, MovementSelectors, PhysicalAuditSelectors,
)
from apps.security.decorators import axentra_gate_enforcer
from apps.shared.apps_config import AppIdentifier

from .common import render_inventory, selector_or_404


def _filters(request, *names):
    return {name: request.GET.get(name, "").strip() for name in names}


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_manage_custody")
def custody_list_view(request):
    f = _filters(request, "q", "status", "asset_id", "assigned_to_id", "department_id")
    return render_inventory(request, page="inventory/pages/custody_list.html", content="inventory/content/custody_list_content.html", context={"current_inventory_view":"inventory:custody_list", "custodies":CustodySelectors.listar(**f), **f})


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_manage_custody")
def custody_detail_view(request, custody_id):
    custody = selector_or_404(lambda: CustodySelectors.obtener(custody_id))
    return render_inventory(request, page="inventory/pages/custody_detail.html", content="inventory/content/custody_detail_content.html", context={"current_inventory_view":"inventory:custody_list", "custody":custody})


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_manage_movements")
def movement_list_view(request):
    f = _filters(request, "q", "asset_id", "movement_type")
    return render_inventory(request, page="inventory/pages/movement_list.html", content="inventory/content/movement_list_content.html", context={"current_inventory_view":"inventory:movement_list", "movements":MovementSelectors.listar(**f), **f})


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_manage_movements")
def movement_detail_view(request, movement_id):
    movement = selector_or_404(lambda: MovementSelectors.obtener(movement_id))
    return render_inventory(request, page="inventory/pages/movement_detail.html", content="inventory/content/movement_detail_content.html", context={"current_inventory_view":"inventory:movement_list", "movement":movement})


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_manage_movements")
def loan_list_view(request):
    f = _filters(request, "q", "status", "asset_id", "borrower_id")
    f["overdue"] = request.GET.get("overdue") == "1"
    return render_inventory(request, page="inventory/pages/loan_list.html", content="inventory/content/loan_list_content.html", context={"current_inventory_view":"inventory:loan_list", "loans":LoanSelectors.listar(**f), **f})


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_manage_movements")
def loan_detail_view(request, loan_id):
    loan = selector_or_404(lambda: LoanSelectors.obtener(loan_id))
    return render_inventory(request, page="inventory/pages/loan_detail.html", content="inventory/content/loan_detail_content.html", context={"current_inventory_view":"inventory:loan_list", "loan":loan})


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
