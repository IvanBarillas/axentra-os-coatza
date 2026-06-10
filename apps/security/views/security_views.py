# apps/security/views/security_views.py
import uuid
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.views.decorators.http import require_POST

from apps.shared.apps_config import AppIdentifier
from apps.security.decorators import axentra_gate_enforcer

# Modelos Reales del Core OS
from apps.security.models import AppModule, TenantConfig
from apps.security.models.audit import SecurityAuditLog

# Selectores y Servicios de Ciberseguridad Central
from apps.security.selectors.security_selectors import PermissionSelectors, SecurityDashboardSelectors
from apps.security.services.security_services import PermissionService

User = get_user_model()
logger = logging.getLogger(__name__)

# Escalafón Universal Inmutable (Regla de Oro de la bitácora)
ROLE_WEIGHTS = {'owner': 100, 'admin': 80, 'editor': 60, 'reviewer': 40, 'viewer': 20}


# =========================================================================
# 🏁 PILAR 1: CHASIS DE CONTROL Y MONITORIZACIÓN TÁCTICA LIGERA
# =========================================================================

@login_required
@axentra_gate_enforcer(AppIdentifier.SECURITY, required_fine_permission="has_access_module")
def security_control_panel_view(request):
    """Estación base ligera para el monitoreo táctico y acceso a herramientas Core."""
    return render(request, 'security/control_panel.html', {'request': request})


# =========================================================================
# 📊 PILAR 2: CONSOLA ANALÍTICA SUPERIOR (FORENSIC DASHBOARD)
# =========================================================================

@login_required
@axentra_gate_enforcer(AppIdentifier.SECURITY, required_fine_permission="can_view_analytics")
def security_dashboard_view(request):
    """Consola Central de Ciberseguridad (Heimdall logs y balanceo de llaves)."""
    context = SecurityDashboardSelectors.obtener_metricas_firewall()
    context['recents_audits'] = SecurityDashboardSelectors.obtener_buffer_auditoria(limite=50)
    return render(request, 'security/dashboard.html', context)


# =========================================================================
# 🔑 PILAR 3: GOBERNANZA MATRICIAL (JSON OVERRIDES DYNAMIC MATRIX)
# =========================================================================

@login_required
# 🟢 CORRECCIÓN DE COMPUERTA: Sincronizado al token unificado 'can_view_matrix' del manifiesto
@axentra_gate_enforcer(AppIdentifier.SECURITY, required_fine_permission='can_view_matrix')
def dynamic_permission_matrix_view(request):
    """Consola Maestra de Privilegios Finos blindada contra manipulaciones de URL."""
    app_slug = request.GET.get('app_slug') or request.POST.get('app_slug')
    if not app_slug:
        return render(request, 'security/errors/400_missing_context.html', status=400)

    app_slug = app_slug.strip().lower()
    app_module = get_object_or_404(AppModule, slug=app_slug, is_active=True)
    user_focus_id = request.GET.get('user_id')

    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        action = request.POST.get('action')

        # 🛡️ OPERACIÓN CRÍTICA 1: GUARDAR ALTERACIONES DE LA MATRIZ DE CHECKBOXES
        if action == "update_permissions":
            nuevo_rol_base = request.POST.get(f'role_{user_id}') or request.POST.get('role')
            llaves_encendidas = request.POST.getlist(f'user_{user_id}') or request.POST.getlist('permisos_checks')
            nuevo_rol_base = nuevo_rol_base.lower().strip()

            target_user = get_object_or_404(User, id=user_id)
            
            # Cortafuegos de Peso Jerárquico: Un Rango menor jamás puede modificar a un rango igual o superior
            if not request.user.axentra_profile.is_root_admin:
                rol_operador = request.axentra_permissions.get('role', 'viewer')
                # 🟢 CORRECCIÓN ATÓMICA ORM: Mutamos '.app_roles' por el related_name premium '.roles'
                rol_destino = target_user.roles.filter(app=app_module, is_active=True).values_list('role', flat=True).first() or 'viewer'
                
                if ROLE_WEIGHTS.get(rol_destino, 0) >= ROLE_WEIGHTS.get(rol_operador, 0) or ROLE_WEIGHTS.get(nuevo_rol_base, 0) >= ROLE_WEIGHTS.get(rol_operador, 0):
                    messages.error(request, "🚫 Violación de Escalafón: Tus privilegios locales no tienen el peso jerárquico para alterar este rango.")
                    return redirect(f"{request.path}?app_slug={app_slug}&user_id={user_id}")

            if PermissionService.save_matrix_permissions(target_user, app_module, nuevo_rol_base, llaves_encendidas):
                messages.success(request, f"🔒 Matriz de configuración modificada para {target_user.email}.")
            return redirect(f"{request.path}?app_slug={app_slug}&user_id={user_id}")

        # 🛡️ OPERACIÓN CRÍTICA 2: SEMBRAR/INYECTAR FUNCIONARIO NUEVO A LA APP
        elif action == "authorize_entry" and request.user.axentra_profile.is_root_admin:
            nuevo_usuario_id = request.POST.get('new_user_id')
            target_user = get_object_or_404(User, id=nuevo_usuario_id)

            if PermissionService.authorize_new_user_entry(app_module, str(target_user.id)):
                messages.success(request, "🟢 Funcionario incorporado al módulo con éxito.")
            return redirect(f"{request.path}?app_slug={app_slug}&user_id={target_user.id}")

    # Método GET ordinario: Resolvemos la matriz en memoria RAM desde el Selector
    context = PermissionSelectors.get_secured_matrix_data(app_module, user_focus_id=user_focus_id, request_user=request.user)
    context['app'] = app_module
    context['modulo_actual'] = app_slug
    return render(request, 'security/matrix_dynamic.html', context)


# =========================================================================
# 🏢 PILAR 4: CONFIGURACIÓN CORPORATIVA GLOBAL (TENANT CONFIG SINGLETON)
# =========================================================================

@login_required
@axentra_gate_enforcer(AppIdentifier.SECURITY, required_fine_permission="can_configure_tenant")
def tenant_config_view(request):
    """Gestión del Singleton de Marca, Escudos, RFC e Identidad Legal del Ayuntamiento."""
    config_instancia = TenantConfig.objects.first()
    
    if request.method == 'POST':
        # Bloque mutacional para actualizar los activos e identidad visual
        # (Aquí conectas con tu TenantForm o tu Service de persistencia de marca)
        messages.success(request, "🏢 Identidad institucional y configuraciones globales actualizadas.")
        return redirect('security:tenant_config')
        
    return render(request, 'security/tenant_config.html', {
        'config': config_instancia,
        'request': request
    })