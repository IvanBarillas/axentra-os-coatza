# apps/security/views/dashboard_views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from apps.security.models.accounts import User
from apps.security.models.audit import SecurityAuditLog
from apps.security.models.organigrama import AreaOperativa, Dependencia, Sede
from apps.shared.apps_config import AppIdentifier
from apps.security.decorators import axentra_gate_enforcer
from apps.security.selectors import AccountsDashboardSelectors, SecurityDashboardSelectors

@login_required
@axentra_gate_enforcer(AppIdentifier.SECURITY, required_fine_permission="can_view_matrix")
def security_dashboard_view(request):
    """Consola Central de Ciberseguridad (Heimdall logs y balanceo de llaves)."""
    context = SecurityDashboardSelectors.obtener_metricas_firewall()
    context['recents_audits'] = SecurityDashboardSelectors.obtener_buffer_auditoria(limite=50)
    return render(request, 'security/dashboard.html', context)

@login_required
# 🟢 CORRECCIÓN DE COM PUERTA: Apuntamos legítimamente a ACCOUNTS y validamos su has_access
@axentra_gate_enforcer(AppIdentifier.ACCOUNTS, required_fine_permission="has_access")
def accounts_dashboard_view(request):
    """Cabina de Mando de Capital Humano: Pipeline demográfico e histórico de altas."""
    context = AccountsDashboardSelectors.obtener_metricas_plantilla()
    context['cronologia_altas'] = AccountsDashboardSelectors.obtener_cronologia_altas()
    return render(request, 'accounts/dashboard/accounts_dashboard.html', context)

@login_required
@axentra_gate_enforcer(AppIdentifier.ORGANIGRAMA, required_fine_permission="has_access")
def organigrama_dashboard_view(request):
    """
    🧠 CABINA DE MANDO GEOGRÁFICA Y ESTRUCTURAL:
    Despacha las métricas globales de densidad burocrática e infraestructura física.
    Mide de forma dinámica la base de datos real sin strings harcodeados.
    """
    # 🎰 AGREGACIONES EN CALIENTE DESDE POSTGRESQL (Cero Hardcodeo)
    total_sedes = Sede.objects.filter(is_active=True).count()
    total_dependencias = Dependencia.objects.filter(is_active=True, is_deleted=False).count()
    total_areas = AreaOperativa.objects.filter(is_active=True, is_deleted=False).count()
    
    # Detección de anomalías: Servidores públicos sin celda de adscripción resuelta
    funcionarios_sin_area = User.objects.filter(
        is_active=True, 
        axentra_profile__area__isnull=True
    ).count() if hasattr(User, 'axentra_profile') else 0

    # 📡 BITÁCORA FORENSE DEL ENTORNO:
    # Extrae los últimos 5 movimientos reales de la BD; si está vacío, el template opera el fallback
    logs_reales = SecurityAuditLog.objects.filter(
        module=AppIdentifier.ORGANIGRAMA
    ).order_by('-created_at')[:5]

    context = {
        'total_sedes': total_sedes,
        'total_dependencias': total_dependencias,
        'total_areas': total_areas,
        'funcionarios_sin_area': funcionarios_sin_area,
        'cronologia_mutaciones': logs_reales, 
    }
    return render(request, 'organigrama/dashboard/organigrama_dashboard.html', context)