# apps/security/views/dashboard_views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from apps.shared.apps_config import AppIdentifier
from apps.security.decorators import axentra_gate_enforcer
from apps.security.selectors import AccountsDashboardSelectors, SecurityDashboardSelectors

@login_required
@axentra_gate_enforcer(AppIdentifier.SECURITY, required_fine_permission="has_access_module")
def security_dashboard_view(request):
    """Consola Central de Ciberseguridad (Heimdall logs y balanceo de llaves)."""
    context = SecurityDashboardSelectors.obtener_metricas_firewall()
    context['recents_audits'] = SecurityDashboardSelectors.obtener_buffer_auditoria(limite=50)
    return render(request, 'security/dashboard/dashboard_security.html', context)

@login_required
@axentra_gate_enforcer(AppIdentifier.SECURITY, required_fine_permission="has_access_module")
def accounts_dashboard_view(request):
    """Cabina de Mando de Capital Humano: Pipeline demográfico e histórico de altas."""
    context = AccountsDashboardSelectors.obtener_metricas_plantilla()
    context['cronologia_altas'] = AccountsDashboardSelectors.obtener_cronologia_altas()
    return render(request, 'accounts/dashboard/accounts_dashboard.html', context)