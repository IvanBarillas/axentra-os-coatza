# apps/security/views/security_views.py
import uuid
import logging
import importlib
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.http import HttpResponse, HttpResponseBadRequest
from django.contrib import messages
from django.views.decorators.http import require_POST

from apps.security.models.organigrama import AppDependencyCapability, Dependencia
from apps.security.services.permission_loader import get_app_permissions
from apps.shared.apps_config import AppIdentifier
from apps.security.decorators import axentra_gate_enforcer

# Modelos del Núcleo Organizacional y Ciberseguridad
from apps.security.models import AppModule, UserAppRole, TenantConfig
from apps.security.forms import TenantConfigForm

# Selectores y Servicios Remotos Orientados a Dominio
from apps.security.selectors.security_selectors import (
    CapabilitySelectors,
    SecurityDashboardSelectors,
    PermissionSelectors
)
from apps.security.services.security_services import PermissionService

User = get_user_model()
logger = logging.getLogger(__name__)

# Escalafón Universal Inmutable
ROLE_WEIGHTS = {'owner': 100, 'admin': 80, 'editor': 60, 'reviewer': 40, 'viewer': 20}

# =========================================================================
# 🏁 PILAR 1: CHASIS DE CONTROL TÁCTICO LIGERO
# =========================================================================
@login_required
@axentra_gate_enforcer(AppIdentifier.SECURITY, required_fine_permission="has_access_module")
def security_control_panel_view(request):
    """Estación base ligera para el monitoreo táctico y accesos rápidos Core."""
    context = SecurityDashboardSelectors.obtener_metricas_firewall()
    return render(request, 'security/control_panel.html', context)


# =========================================================================
# 📊 PILAR 2: CABINA DE MANDO ANALÍTICA (HEIMDALL FORENSIC LAYER)
# =========================================================================
@login_required
@axentra_gate_enforcer(AppIdentifier.SECURITY, required_fine_permission="can_view_analytics")
def security_dashboard_view(request):
    """Consola Central de Ciberseguridad: Audita densidad de llaves JSONField y logs."""
    context = SecurityDashboardSelectors.obtener_metricas_firewall()
    context['recents_audits'] = SecurityDashboardSelectors.obtener_buffer_auditoria(limite=50)
    return render(request, 'security/dashboard/dashboard_security.html', context)


# =========================================================================
# 🏢 PILAR 3: CONFIGURACIÓN GLOBAL INSTITUCIONAL (TENANT CONFIG MASTER)
# =========================================================================
@login_required
@axentra_gate_enforcer(AppIdentifier.SECURITY, required_fine_permission="can_configure_tenant")
def tenant_config_view(request):
    """⚙️ SINGLETON IDENTITY ENFORCER: Gobernanza central de marca institucional."""
    config_instancia = TenantConfig.objects.first()
    if not config_instancia:
        config_instancia = TenantConfig.objects.create(
            app_name="Axentra OS",
            entidad_nombre="H. Ayuntamiento Constitucional",
            siglas="AXN"
        )

    if request.method == 'POST':
        form = TenantConfigForm(request.POST, request.FILES, instance=config_instancia)
        if form.is_valid():
            form.save()
            messages.success(request, "🏢 Los activos de marca de la institución se reconfiguraron correctamente de forma global.")
            return redirect('security:control_panel')
    else:
        form = TenantConfigForm(instance=config_instancia)
        
    return render(request, 'security/forms/tenant_form.html', {
        'form': form,
        'config': config_instancia
    })


# =========================================================================
# 🪐 PILAR 4: CONSOLE MASTER DE PRIVILEGIOS FINOS (UNIVERSAL MATRIX)
# =========================================================================

@login_required
@axentra_gate_enforcer(AppIdentifier.SECURITY, required_fine_permission="can_view_matrix")
def dynamic_permission_matrix_view(request):
    """
    🔍 CONTROLADOR DE LECTURA PURO (GET): Despacha el estado de la matriz.
    Mantiene cero responsabilidades mutacionales.
    """
    app_slug = request.GET.get('app_slug')
    
    # 🛡️ Cortafuegos de URLs Desnudas: Intercepta peticiones sin contexto de app
    if not app_slug:
        logger.warning(f"🛑 [INTENTO DE BYPASS]: {request.user.email} intentó entrar a la matriz sin app_slug.")
        return render(request, 'security/errors/400_missing_context.html', {
            'error_detalle': "Bloqueo de Infraestructura: La Consola de Privilegios requiere una firma de aplicación explícita."
        }, status=400)

    app_slug = app_slug.strip().lower()
    app_module = get_object_or_404(AppModule, slug=app_slug, is_active=True)
    user_focus_id = request.GET.get('user_id')
    is_manager_global = getattr(request.user, 'is_manager', False) or (hasattr(request.user, 'axentra_profile') and request.user.axentra_profile.is_root_admin)

    # Resolución delegada limpiamente a la capa de Selectores de dominio
    context = PermissionSelectors.get_secured_matrix_data(
        app_module=app_module,
        user_focus_id=user_focus_id,
        request_user=request.user,
        is_manager_global=is_manager_global
    )
    
    context.update({
        'app': app_module,
        'app_slug_actual': app_module.slug,
        'modulo_actual': app_slug,
        'roles_buscador': list(UserAppRole.Roles.choices),
    })

    return render(request, 'security/matrix_dynamic.html', context)


@login_required
@axentra_gate_enforcer(AppIdentifier.SECURITY, required_fine_permission="can_modify_matrix")
@require_POST
def guardar_llaves_json_view(request, app_id, user_id):
    """
    💾 MUTADOR ATÓMICO A: Compila la grilla de checkboxes y actualiza el JSONField en Postgres.
    """
    app_module = get_object_or_404(AppModule, id=app_id, is_active=True)
    target_user = get_object_or_404(User, id=user_id)
    is_manager_global = getattr(request.user, 'is_manager', False) or (hasattr(request.user, 'axentra_profile') and request.user.axentra_profile.is_root_admin)

    nuevo_rol_base = request.POST.get(f'role_{user_id}') or request.POST.get('role') or request.POST.get('nuevo_rol')
    llaves_encendidas = request.POST.getlist(f'user_{user_id}') or request.POST.getlist('permisos_checks') or []
    nuevo_rol_base = nuevo_rol_base.lower().strip()

    rol_actual_obj = UserAppRole.objects.filter(user=target_user, app=app_module).first()
    rol_actual_str = rol_actual_obj.role if rol_actual_obj else 'viewer'

    # Guardián Jerárquico de Pesos locales (Aduana de Seguridad de Bloqueo)
    if not is_manager_global:
        rol_operador_obj = UserAppRole.objects.filter(user=request.user, app=app_module, is_active=True).first()
        rol_operador_str = rol_operador_obj.role if rol_operador_obj else 'viewer'
        
        peso_operador = ROLE_WEIGHTS.get(rol_operador_str, 0)
        peso_actual_destino = ROLE_WEIGHTS.get(rol_actual_str, 0)
        peso_nuevo_destino = ROLE_WEIGHTS.get(nuevo_rol_base, 0)

        if peso_actual_destino >= peso_operador or peso_nuevo_destino >= peso_operador:
            messages.error(request, "🚫 Violación de Escalafón: Tus privilegios locales no tienen el peso jerárquico para alterar o declarar este rango.")
            return redirect(f"security:dynamic_matrix")

    config_app = get_app_permissions(app_module.slug)
    if nuevo_rol_base == "owner":
        llaves_encendidas = list(config_app.get('permissions', {}).keys())

    if 'has_access_module' not in llaves_encendidas:
        llaves_encendidas.append('has_access_module')

    if PermissionService.save_matrix_permissions(target_user, app_module, nuevo_rol_base, llaves_encendidas):
        messages.success(request, f"🔒 Matriz de configuración actualizada para {target_user.full_name}.")
    else:
        messages.error(request, "❌ Error de consistencia al procesar la mutación en PostgreSQL.")
        
    return redirect(f"/app/security/matriz/?app_slug={app_module.slug}&user_id={target_user.id}")


@login_required
@axentra_gate_enforcer(AppIdentifier.SECURITY, required_fine_permission="can_modify_matrix")
@require_POST
def inyectar_funcionario_view(request, app_id):
    """
    🟢 MUTADOR ATÓMICO B: Incorpora un nuevo servidor público al módulo satélite federado.
    """
    app_module = get_object_or_404(AppModule, id=app_id, is_active=True)
    is_manager_global = getattr(request.user, 'is_manager', False) or (hasattr(request.user, 'axentra_profile') and request.user.axentra_profile.is_root_admin)

    if not is_manager_global:
        messages.error(request, "🚫 Acceso Denegado: La inyección perimetral de personal es exclusiva del Master central.")
        return redirect(f"/app/security/matriz/?app_slug={app_module.slug}")

    nuevo_usuario_id = request.POST.get('new_user_id')
    rol_a_inyectar = request.POST.get('initial_role', 'viewer').lower().strip()
    target_user = get_object_or_404(User, id=nuevo_usuario_id)

    if PermissionService.authorize_new_user_entry(app_module, str(target_user.id), rol_a_inyectar):
        messages.success(request, f"🟢 Funcionario {target_user.email} inyectado con éxito como [{rol_a_inyectar.upper()}].")
    else:
        messages.warning(request, "⚠️ Operación cancelada: El funcionario ya cuenta con membresía activa o el proceso falló.")
        
    return redirect(f"/app/security/matriz/?app_slug={app_module.slug}&user_id={target_user.id}")
    
# =========================================================================
# 🎛️ PILAR 5: CONSOLA DE CAPACIDADES REGIONALES POR DEPENDENCIAS (HTMX)
# =========================================================================

@login_required
@axentra_gate_enforcer(AppIdentifier.SECURITY, required_fine_permission="can_configure_tenant")
def matrix_capabilities_view(request):
    """Master de Capacidades Regionales: Muestra qué dependencias consumen qué apps."""
    app_slug = request.GET.get('app_slug', 'accounts').strip().lower()
    app_activa = get_object_or_404(AppModule, slug=app_slug)
    
    # Delegación total de lógica de negocio y reflexión al Selector corporativo
    context = CapabilitySelectors.obtener_matriz_capacidades_contexto(app_activa)
    
    context.update({
        'apps': AppModule.objects.filter(is_active=True),
        'app_activa': app_activa,
        'modulo_actual': 'security'
    })

    return render(request, 'security/matrix_capabilities.html', context)


@login_required
@axentra_gate_enforcer(AppIdentifier.SECURITY, required_fine_permission="can_configure_tenant")
@require_POST
def add_capability_node_view(request, app_id):
    """Vincula una nueva dependencia al mapa relacional de capacidades de la App."""
    app_obj = get_object_or_404(AppModule, id=app_id)
    dependencia_id = request.POST.get('dependencia_id')
    
    if not dependencia_id:
        return HttpResponse('⚠️ Seleccione una dependencia válida.', status=400)
        
    dep_obj = get_object_or_404(Dependencia, id=dependencia_id)
    AppDependencyCapability.objects.get_or_create(
        app=app_obj, dependencia=dep_obj, defaults={'flag_alfa': False, 'flag_beta': False}
    )

    # Disparamos refresh nativo a HTMX para recalibrar los listados de la pantalla
    response = HttpResponse(status=200)
    response['HX-Refresh'] = 'true'
    return response


@login_required
@axentra_gate_enforcer(AppIdentifier.SECURITY, required_fine_permission="can_configure_tenant")
@require_POST
def toggle_capability_ajax_view(request, dep_id, app_id):
    """Interruptor AJAX universal para prender/apagar capacidades organizacionales por módulo."""
    app_obj = get_object_or_404(AppModule, id=app_id)
    dep_obj = get_object_or_404(Dependencia, id=dep_id)
    field = request.POST.get('field')
    
    if field not in ['flag_alfa', 'flag_beta']:
        return HttpResponse('❌ Campo operativo inválido', status=400)

    # Persistencia atómica de la bandera en la base de datos
    capacidad, _ = AppDependencyCapability.objects.get_or_create(app=app_obj, dependencia=dep_obj)
    nuevo_estado = not getattr(capacidad, field)
    setattr(capacidad, field, nuevo_estado)
    capacidad.save()

    # 🛰️ RECOLECCIÓN EN CALIENTE: Extrae las etiquetas reales del manifiesto de la App activa
    labels_manifiesto = CapabilitySelectors.obtener_labels_manifiesto(app_obj.slug)
    config_campo = labels_manifiesto.get(field, {})
    help_text_dinamico = config_campo.get('help_text', 'Configuración de capacidad guardada con éxito.')

    # Calibración de color según la bandera que se esté mutando
    bg_active_class = "bg-blue-600 justify-end" if field == "flag_alfa" else "bg-indigo-600 justify-end"
    bg_class = bg_active_class if nuevo_estado else "bg-gray-200 justify-start"
    
    next_url = f"/app/security/platform/capabilities/toggle/{dep_obj.id}/{app_obj.id}/"
    
    # 🚀 RESPUESTA PREMIUM DE DOMINIO: Renderiza manteniendo la semántica del manifiesto local
    return render(request, 'security/htmx/capability_switch_partial.html', {
        'next_url': next_url,
        'bg_class': bg_class,
        'help_text': help_text_dinamico
    })

# =========================================================================
# 🎛️ 
# =========================================================================
@login_required
@axentra_gate_enforcer(AppIdentifier.SECURITY, required_fine_permission="can_modify_matrix")
@require_POST
def toggle_user_modulo_active_ajax_view(request, user_id, app_id):
    """
    🔄 SWITCH PERIMETRAL CORE: Conmuta el estado activo/suspendido de un funcionario.
    Consume el parcial existente mapeando las variables idénticas del ecosistema.
    """
    app_module = get_object_or_404(AppModule, id=app_id)
    target_user = get_object_or_404(User, id=user_id)
    
    # Cortafuegos para prevenir auto-suspensión o alteración de rangos protegidos
    if target_user.is_manager or str(target_user.id) == str(request.user.id):
        return HttpResponse(status=403, content="Operación denegada sobre rangos protegidos.")
        
    rol_instancia = get_object_or_404(UserAppRole, user=target_user, app=app_module)
    rol_instancia.is_active = not rol_instancia.is_active
    rol_instancia.save()
    
    logger.warning(f"🚨 CIBERSEGURIDAD: Estado de {target_user.email} conmutado a [Activo={rol_instancia.is_active}] en App [{app_module.slug.upper()}].")
    
    # 🚀 ALINEACIÓN DE CONTEXTO: Emparejado al milímetro con las variables de tu plantilla
    return render(request, 'security/htmx/matrix_user_actions_partial.html', {
        'app': app_module,
        'item': {
            'usuario': target_user,
        },
        'rol_active': rol_instancia.is_active,  # Evalúa el booleano para los colores de Tailwind
    })


@login_required
@require_POST
def expulsar_usuario_modulo_total_ajax_view(request, user_id, app_id):
    """
    💥 KILL-SWITCH ABSOLUTO: Destrucción total de la membresía en la base de datos.
    🛡️ ADUANA CRÍTICA: Solo el mánager raíz o superuser global pasa esta línea.
    """
    if not (getattr(request.user, 'is_manager', False) or getattr(request.user, 'is_superuser', False)):
        return HttpResponse(status=403, content="Acceso denegado: Requiere nivel Mánager Supremo.")
        
    app_module = get_object_or_404(AppModule, id=app_id)
    target_user = get_object_or_404(User, id=user_id)
    
    if target_user.is_manager or str(target_user.id) == str(request.user.id):
        return HttpResponse(status=403, content="Operación denegada sobre rangos protegidos.")
        
    UserAppRole.objects.filter(user=target_user, app=app_module).delete()
    
    logger.warning(f"🚨 EXPULSIÓN SUPREMA: {request.user.email} ELIMINÓ a {target_user.email} de la App [{app_module.slug.upper()}].")
    return HttpResponse(status=200, content="")

# =========================================================================
# 🎛️ 
# =========================================================================