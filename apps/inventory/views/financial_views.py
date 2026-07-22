"""Vistas financieras globales de Control Patrimonial."""

from django import forms
from django.core.paginator import Paginator
from django.http import FileResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from apps.inventory.forms import AccountingExportCreateForm, DepreciationPolicyCloseForm, DepreciationPolicyCreateForm, DepreciationPostForm, DepreciationRunCreateForm, ReconciliationCloseForm, ReconciliationCreateForm, ReconciliationProcessForm
from apps.inventory.models.financial_models import AccountingExportStatus, DepreciationRunStatus, ReconciliationStatus
from apps.inventory.selectors import FinancialScope, FinancialSelectors
from apps.inventory.services import calculate_depreciation_run, close_depreciation_policy, close_reconciliation, create_accounting_export, create_depreciation_policy, create_depreciation_run, create_reconciliation, post_depreciation_run, process_reconciliation
from apps.security.decorators import axentra_gate_enforcer
from apps.shared.apps_config import AppIdentifier

from .common import render_inventory, run_service, selector_or_404, success


def _run(run_id):
    return selector_or_404(lambda: FinancialSelectors.depreciation_run_detail(run_id, scope=FinancialScope.GLOBAL))


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_view_financials")
def financial_dashboard_view(request):
    return render_inventory(request, page="inventory/pages/financial_dashboard.html", content="inventory/content/financial_dashboard_content.html", context={
        "current_inventory_view": "inventory:financial_dashboard",
        "policies": FinancialSelectors.depreciation_policies(),
        "runs": FinancialSelectors.depreciation_runs(scope=FinancialScope.GLOBAL)[:5],
        "exports": FinancialSelectors.export_batches(scope=FinancialScope.GLOBAL)[:5],
        "reconciliations": FinancialSelectors.reconciliations(scope=FinancialScope.GLOBAL)[:5],
        "can_run_depreciation": "can_run_depreciation" in request.axentra_permissions_list or request.axentra_is_root,
        "can_post_depreciation": "can_post_depreciation" in request.axentra_permissions_list or request.axentra_is_root,
        "can_export_reports": "can_export_reports" in request.axentra_permissions_list or request.axentra_is_root,
        "can_manage_reconciliation": "can_manage_reconciliation" in request.axentra_permissions_list or request.axentra_is_root,
    })


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_view_financials")
def financial_history_view(request, section):
    section = str(section).strip().lower()
    q = request.GET.get("q", "").strip(); status = request.GET.get("status", "").strip()
    year = request.GET.get("year", "").strip()
    if section == "depreciations":
        queryset = FinancialSelectors.depreciation_runs(q=q, status=status, period_year=int(year) if year.isdigit() else None, scope=FinancialScope.GLOBAL)
        title = "Histórico de depreciaciones"; statuses = DepreciationRunStatus.choices
    elif section == "exports":
        queryset = FinancialSelectors.export_batches(q=q, status=status, scope=FinancialScope.GLOBAL)
        if year.isdigit(): queryset = queryset.filter(period_start__year=int(year))
        title = "Histórico de reportes"; statuses = AccountingExportStatus.choices
    elif section == "reconciliations":
        queryset = FinancialSelectors.reconciliations(q=q, status=status, scope=FinancialScope.GLOBAL)
        if year.isdigit(): queryset = queryset.filter(period_start__year=int(year))
        title = "Histórico de conciliaciones"; statuses = ReconciliationStatus.choices
    else:
        from django.http import Http404
        raise Http404("El histórico financiero solicitado no existe.")
    page = Paginator(queryset, 25).get_page(request.GET.get("page"))
    return render_inventory(request, page="inventory/pages/financial_history.html", content="inventory/content/financial_history_content.html", context={"current_inventory_view":"inventory:financial_dashboard", "section":section, "history_title":title, "records":page, "q":q, "status":status, "year":year, "statuses":statuses})


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_view_financials")
def depreciation_policy_list_view(request):
    policies = FinancialSelectors.depreciation_policies()
    uncovered = FinancialSelectors.assets_without_policy()
    return render_inventory(request, page="inventory/pages/depreciation_policy_list.html", content="inventory/content/depreciation_policy_list_content.html", context={"current_inventory_view":"inventory:financial_dashboard", "policies":policies, "uncovered_assets":uncovered, "can_manage_policies":request.axentra_is_root or "can_run_depreciation" in request.axentra_permissions_list})


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_run_depreciation")
def depreciation_policy_create_view(request):
    form = DepreciationPolicyCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        policy = run_service(form, lambda: create_depreciation_policy(data=form.to_dto(), actor_id=request.user.pk, request=request))
        if policy:
            success(request, f"Política {policy.policy_code} V{policy.version_number} creada correctamente.")
            return redirect("inventory:depreciation_policy_list")
    return render_inventory(request, page="inventory/pages/financial_form.html", content="inventory/content/financial_form_content.html", context={"current_inventory_view":"inventory:financial_dashboard", "form":form, "form_title":"Nueva política de depreciación", "form_help":"La versión se asignará automáticamente y no podrá traslaparse con otra vigencia."}, status=422 if request.method == "POST" else 200)


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_run_depreciation")
def depreciation_policy_close_view(request, policy_id):
    policy = selector_or_404(lambda: FinancialSelectors.depreciation_policy_detail(policy_id)); form = DepreciationPolicyCloseForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        result = run_service(form, lambda: close_depreciation_policy(policy_id=policy.id, data=form.to_dto(), actor_id=request.user.pk, request=request))
        if result:
            success(request, "Vigencia de la política cerrada correctamente.")
            return redirect("inventory:depreciation_policy_list")
    return render_inventory(request, page="inventory/pages/financial_form.html", content="inventory/content/financial_form_content.html", context={"current_inventory_view":"inventory:financial_dashboard", "form":form, "form_title":f"Cerrar vigencia · {policy.policy_code} V{policy.version_number}", "form_help":"Los cálculos históricos conservarán la versión aplicada."}, status=422 if request.method == "POST" else 200)


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_run_depreciation")
def depreciation_run_create_view(request):
    form = DepreciationRunCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        run = run_service(form, lambda: create_depreciation_run(data=form.to_dto(), actor_id=request.user.pk, request=request))
        if run:
            success(request, "Ejecución de depreciación creada.")
            return redirect("inventory:depreciation_run_detail", run_id=run.id)
    return render_inventory(request, page="inventory/pages/financial_form.html", content="inventory/content/financial_form_content.html", context={"current_inventory_view":"inventory:financial_dashboard", "form":form, "form_title":"Nueva ejecución de depreciación", "form_help":"Define el periodo que será calculado. El proceso no se aplica contablemente hasta su autorización."}, status=422 if request.method == "POST" else 200)


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_view_financials")
def depreciation_run_detail_view(request, run_id):
    run = _run(run_id)
    return render_inventory(request, page="inventory/pages/depreciation_run_detail.html", content="inventory/content/depreciation_run_detail_content.html", context={"current_inventory_view":"inventory:financial_dashboard", "run":run, "can_calculate":run.status in {DepreciationRunStatus.DRAFT, DepreciationRunStatus.FAILED} and (request.axentra_is_root or "can_run_depreciation" in request.axentra_permissions_list), "can_post":run.status == DepreciationRunStatus.COMPLETED and (request.axentra_is_root or "can_post_depreciation" in request.axentra_permissions_list)})


@require_http_methods(["POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_run_depreciation")
def depreciation_run_calculate_view(request, run_id):
    form = forms.Form(request.POST)
    run = run_service(form, lambda: calculate_depreciation_run(run_id=run_id, actor_id=request.user.pk, recalculate=request.POST.get("recalcular") == "1", request=request))
    if run: success(request, f"Se calcularon {run.asset_count} activos.")
    return redirect("inventory:depreciation_run_detail", run_id=run_id)


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_post_depreciation")
def depreciation_run_post_view(request, run_id):
    run = _run(run_id); form = DepreciationPostForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        result = run_service(form, lambda: post_depreciation_run(run_id=run.id, data=form.to_dto(), actor_id=request.user.pk, request=request))
        if result:
            success(request, "La depreciación fue aplicada y cerrada.")
            return redirect("inventory:depreciation_run_detail", run_id=run.id)
    return render_inventory(request, page="inventory/pages/financial_form.html", content="inventory/content/financial_form_content.html", context={"current_inventory_view":"inventory:financial_dashboard", "form":form, "form_title":"Aplicar depreciación", "form_help":"Esta acción cierra el lote y exige una referencia contable."}, status=422 if request.method == "POST" else 200)


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_export_reports")
def accounting_export_create_view(request):
    form = AccountingExportCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        batch = run_service(form, lambda: create_accounting_export(data=form.to_dto(), actor_id=request.user.pk, request=request))
        if batch:
            success(request, "Reporte generado correctamente.")
            return redirect("inventory:financial_dashboard")
    return render_inventory(request, page="inventory/pages/financial_form.html", content="inventory/content/financial_form_content.html", context={"current_inventory_view":"inventory:financial_dashboard", "form":form, "form_title":"Generar reporte oficial", "form_help":"Cada tipo utiliza un conjunto específico de datos y columnas. El archivo se genera en CSV UTF-8.", "show_report_layout_notice":True}, status=422 if request.method == "POST" else 200)


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_export_reports")
def accounting_export_download_view(request, batch_id):
    batch = selector_or_404(lambda: FinancialSelectors.export_batch_detail(batch_id, scope=FinancialScope.GLOBAL))
    if batch.status != AccountingExportStatus.COMPLETED or not batch.generated_file:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("El archivo todavía no está disponible.")
    return FileResponse(batch.generated_file.open("rb"), as_attachment=True, filename=batch.generated_filename)


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_manage_reconciliation")
def reconciliation_create_view(request):
    form = ReconciliationCreateForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        item = run_service(form, lambda: create_reconciliation(data=form.to_dto(), actor_id=request.user.pk, request=request))
        if item:
            success(request, "Archivo contable cargado para conciliación.")
            return redirect("inventory:financial_dashboard")
    return render_inventory(request, page="inventory/pages/financial_form.html", content="inventory/content/financial_form_content.html", context={"current_inventory_view":"inventory:financial_dashboard", "form":form, "form_title":"Nueva conciliación físico-contable", "form_help":"Carga la balanza o archivo fuente emitido por el sistema contable."}, status=422 if request.method == "POST" else 200)


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_view_financials")
def reconciliation_detail_view(request, reconciliation_id):
    item = selector_or_404(lambda: FinancialSelectors.reconciliation_detail(reconciliation_id, scope=FinancialScope.GLOBAL))
    manages = request.axentra_is_root or "can_manage_reconciliation" in request.axentra_permissions_list
    return render_inventory(request, page="inventory/pages/reconciliation_detail.html", content="inventory/content/reconciliation_detail_content.html", context={"current_inventory_view":"inventory:financial_dashboard", "reconciliation":item, "can_process":manages and item.status in {ReconciliationStatus.FILE_UPLOADED, ReconciliationStatus.FAILED}, "can_close":manages and item.status in {ReconciliationStatus.RECONCILED, ReconciliationStatus.WITH_DIFFERENCES, ReconciliationStatus.UNDER_REVIEW}})


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_manage_reconciliation")
def reconciliation_process_view(request, reconciliation_id):
    item = selector_or_404(lambda: FinancialSelectors.reconciliation_detail(reconciliation_id, scope=FinancialScope.GLOBAL)); form = ReconciliationProcessForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        result = run_service(form, lambda: process_reconciliation(reconciliation_id=item.id, data=form.to_dto(), actor_id=request.user.pk, request=request))
        if result:
            success(request, "Conciliación procesada correctamente.")
            return redirect("inventory:reconciliation_detail", reconciliation_id=item.id)
    return render_inventory(request, page="inventory/pages/financial_form.html", content="inventory/content/financial_form_content.html", context={"current_inventory_view":"inventory:financial_dashboard", "form":form, "form_title":"Procesar conciliación", "form_help":"Indica los nombres de las columnas que contienen la cuenta y el saldo."}, status=422 if request.method == "POST" else 200)


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="can_manage_reconciliation")
def reconciliation_close_view(request, reconciliation_id):
    item = selector_or_404(lambda: FinancialSelectors.reconciliation_detail(reconciliation_id, scope=FinancialScope.GLOBAL)); form = ReconciliationCloseForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        result = run_service(form, lambda: close_reconciliation(reconciliation_id=item.id, data=form.to_dto(), actor_id=request.user.pk, request=request))
        if result:
            success(request, "Conciliación cerrada correctamente.")
            return redirect("inventory:reconciliation_detail", reconciliation_id=item.id)
    return render_inventory(request, page="inventory/pages/financial_form.html", content="inventory/content/financial_form_content.html", context={"current_inventory_view":"inventory:financial_dashboard", "form":form, "form_title":"Cerrar conciliación", "form_help":"Registra las conclusiones y diferencias aceptadas antes del cierre."}, status=422 if request.method == "POST" else 200)


__all__ = [name for name in globals() if name.endswith("_view")]
