# apps/security/views/security_views.py
import uuid
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.contrib import messages
from django.views.decorators.http import require_POST

from apps.security.models.organigrama import AppDependencyCapability, Dependencia
from apps.security.selectors.permission_selectors import PermissionSelectors
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
)

from apps.security.services.security_services import PermissionService

User = get_user_model()
logger = logging.getLogger(__name__)

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
# 📊 PILAR 2: CABINA DE MANDO ANALÍTICA (FORENSIC LAYER)
# =========================================================================
@login_required
@axentra_gate_enforcer(AppIdentifier.SECURITY, required_fine_permission="can_view_analytics")
def security_dashboard_view(request):
    """Consola Central de Ciberseguridad: Audita densidad de llaves JSONField y logs."""
    context = SecurityDashboardSelectors.obtener_metricas_firewall()
    context['recents_audits'] = SecurityDashboardSelectors.obtener_buffer_auditoria(limite=50)
    return render(request, 'security/dashboard/security_dashboard.html', context)


# =========================================================================
# 🏢 PILAR 3: CONFIGURACIÓN GLOBAL INSTITUCIONAL (TENANT CONFIG MASTER)
# =========================================================================
@login_required
@axentra_gate_enforcer(AppIdentifier.SECURITY, required_fine_permission="can_configure_tenant")
def tenant_config_view(request):
    """SINGLETON IDENTITY ENFORCER: Gobernanza central de marca institucional."""
    config_instancia = TenantConfig.objects.first()
    if not config_instancia:
        config_instancia = TenantConfig.objects.create(
            app_name="Axentra OS", entidad_nombre="H. Ayuntamiento Constitucional", siglas="AXN"
        )
    if request.method == 'POST':
        form = TenantConfigForm(request.POST, request.FILES, instance=config_instancia)
        if form.is_valid():
            form.save()
            messages.success(request, "Los activos de marca de la institución se reconfiguraron correctamente de forma global.")
            return redirect('security:control_panel')
    else:
        form = TenantConfigForm(instance=config_instancia)
    return render(request, 'security/forms/tenant_form.html', {'form': form, 'config': config_instancia})


# =========================================================================
# 🪐 PILAR 4: CONSOLE MASTER DE PRIVILEGIOS FINOS (UNIVERSAL MATRIX)
# =========================================================================
@login_required
@axentra_gate_enforcer(AppIdentifier.SECURITY, required_fine_permission="can_view_matrix")
def dynamic_permission_matrix_view(request):
    """CONTROLADOR DE LECTURA PURO (GET): Despacha el estado de la matriz."""
    app_slug = request.GET.get('app_slug')
    if not app_slug:
        logger.warning(f"🛑 [INTENTO DE BYPASS]: {request.user.email} intentó entrar a la matriz sin app_slug.")
        return render(request, 'security/errors/400_missing_context.html', {
            'error_detalle': "Bloqueo de Infraestructura: La Consola de Privilegios requiere una firma de aplicación explícita."
        }, status=400)

    app_slug = app_slug.strip().lower()
    app_module = get_object_or_404(AppModule, slug=app_slug, is_active=True)
    user_focus_id = request.GET.get('user_id')
    is_manager_global = getattr(request.user, 'is_manager', False) or (hasattr(request.user, 'axentra_profile') and request.user.axentra_profile.is_root_admin)

    context = PermissionSelectors.get_secured_matrix_data(
        app_module=app_module, user_focus_id=user_focus_id, request_user=request.user, is_manager_global=is_manager_global
    )
    
    context.update({
        'app': app_module,
        'app_slug_actual': app_module.slug,
        'modulo_actual': app_slug,
        'roles_buscador': [rol[0] for rol in context.get('roles_choices', [])],
    })
    return render(request, 'security/matrix_dynamic.html', context)


@login_required
@axentra_gate_enforcer(AppIdentifier.SECURITY, required_fine_permission="can_modify_matrix")
@require_POST
def guardar_llaves_json_view(request, app_id, user_id):
    """Compila la grilla de checkboxes y actualiza el JSONField en Postgres validando escalafón dinámico."""
    app_module = get_object_or_404(AppModule, id=app_id, is_active=True)
    target_user = get_object_or_404(User, id=user_id)
    is_manager_global = getattr(request.user, 'is_manager', False) or (hasattr(request.user, 'axentra_profile') and request.user.axentra_profile.is_root_admin)

    nuevo_rol_base = request.POST.get(f'role_{user_id}') or request.POST.get('role') or request.POST.get('nuevo_rol')
    llaves_encendidas = request.POST.getlist(f'user_{user_id}') or request.POST.getlist('permisos_checks') or []
    nuevo_rol_base = str(nuevo_rol_base).lower().strip()

    rol_actual_obj = UserAppRole.objects.filter(user=target_user, app=app_module).first()
    rol_actual_str = rol_actual_obj.role if rol_actual_obj else 'viewer'

    # 🛰️ CORTAFUEGOS JERÁRQUICO SOBERANO: Extrae el mapa de autoridad específico de la app
    config_app = get_app_permissions(app_module.slug)
    weights_map = config_app.get('weights', {})

    if not is_manager_global:
        rol_operador_obj = UserAppRole.objects.filter(user=request.user, app=app_module, is_active=True).first()
        rol_operador_str = rol_operador_obj.role if rol_operador_obj else 'viewer'
        
        # Validación de pesos contra el manifiesto de la aplicación activa
        peso_operador = weights_map.get(str(rol_operador_str).lower().strip(), 0)
        peso_actual_destino = weights_map.get(str(rol_actual_str).lower().strip(), 0)
        peso_nuevo_destino = weights_map.get(str(nuevo_rol_base).lower().strip(), 0)

        if peso_actual_destino >= peso_operador or peso_nuevo_destino >= peso_operador:
            messages.error(request, "🚫 Violación de Escalafón: Tus privilegios locales en este módulo no tienen el peso jerárquico para alterar o declarar este rango.")
            return redirect(f"/app/security/matriz/?app_slug={app_module.slug}&user_id={target_user.id}")

    if nuevo_rol_base == "owner":
        llaves_encendidas = list(config_app.get('permissions', {}).keys())

    if 'has_access_module' not in llaves_encendidas:
        llaves_encendidas.append('has_access_module')

    if PermissionService.save_matrix_permissions(target_user, app_module, nuevo_rol_base, llaves_encendidas):
        messages.success(request, f"🔒 Matriz de configuración actualizada para {target_user.get_full_name() or target_user.username}.")
    else:
        messages.error(request, "❌ Error de consistencia al procesar la mutación en PostgreSQL.")
        
    return redirect(f"/app/security/matriz/?app_slug={app_module.slug}&user_id={target_user.id}")


@login_required
@axentra_gate_enforcer(AppIdentifier.SECURITY, required_fine_permission="can_modify_matrix")
@require_POST
def inyectar_funcionario_view(request, app_id):
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
        messages.warning(request, "⚠️ Operación cancelada: El funcionario ya cuenta con membresía activa.")
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

    capacidad, _ = AppDependencyCapability.objects.get_or_create(app=app_obj, dependencia=dep_obj)
    nuevo_estado = not getattr(capacidad, field)
    setattr(capacidad, field, nuevo_estado)
    capacidad.save()

    labels_manifiesto = CapabilitySelectors.obtener_labels_manifiesto(app_obj.slug)
    config_campo = labels_manifiesto.get(field, {})
    help_text_dinamico = config_campo.get('help_text', 'Configuración de capacidad guardada con éxito.')

    bg_active_class = "bg-blue-600 justify-end" if field == "flag_alfa" else "bg-indigo-600 justify-end"
    bg_class = bg_active_class if nuevo_estado else "bg-gray-200 justify-start"
    
    next_url = f"/app/security/platform/capabilities/toggle/{dep_obj.id}/{app_obj.id}/"
    
    return render(request, 'security/htmx/capability_switch_partial.html', {
        'next_url': next_url,
        'bg_class': bg_class,
        'help_text': help_text_dinamico
    })


@login_required
@axentra_gate_enforcer(AppIdentifier.SECURITY, required_fine_permission="can_modify_matrix")
@require_POST
def toggle_user_modulo_active_ajax_view(request, user_id, app_id):
    """
    🔄 SWITCH PERIMETRAL CORE: Conmuta el estado activo/suspendido de un funcionario.
    """
    app_module = get_object_or_404(AppModule, id=app_id)
    target_user = get_object_or_404(User, id=user_id)
    
    if target_user.is_manager or str(target_user.id) == str(request.user.id):
        return HttpResponse(status=403, content="Operación denegada sobre rangos protegidos.")
        
    rol_instancia = get_object_or_404(UserAppRole, user=target_user, app=app_module)
    rol_instancia.is_active = not rol_instancia.is_active
    rol_instancia.save()
    
    logger.warning(f"🚨 CIBERSEGURIDAD: Estado de {target_user.email} conmutado a [Activo={rol_instancia.is_active}] en App [{app_module.slug.upper()}].")
    
    return render(request, 'security/htmx/matrix_user_actions_partial.html', {
        'app': app_module,
        'item': {
            'usuario': target_user,
        },
        'rol_active': rol_instancia.is_active,
    })


@login_required
@require_POST
def expulsar_usuario_modulo_total_ajax_view(request, user_id, app_id):
    """
    💥 KILL-SWITCH ABSOLUTO: Destrucción total de la membresía en la base de datos.
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


@login_required
@axentra_gate_enforcer(AppIdentifier.SECURITY, required_fine_permission="can_view_matrix")
def security_global_matrix_forensic_view(request):
    """🛡️ AUDITORÍA GLOBAL MATRIX: Escanea y diagnostica de forma masiva los tokens de acceso."""
    filtros = {
        'q': request.GET.get('q', '').strip(),
        'sede_id': request.GET.get('sede', '').strip() or None,
        'dependencia_id': request.GET.get('dependencia', '').strip() or None,
        'area_id': request.GET.get('area', '').strip() or None
    }
    
    funcionarios_liquidados = PermissionSelectors.listar_matriz_forense_global(filtros)
    
    from apps.security.models.organigrama import Dependencia, Sede, AreaOperativa
    
    context = {
        'funcionarios': funcionarios_liquidados,
        'aplicaciones_sistema': AppIdentifier.get_choices(),
        'sedes': Sede.objects.filter(is_active=True).order_by('nombre'),
        'dependencias': Dependencia.objects.filter(is_active=True, is_deleted=False).order_by('nombre'),
        'areas_operativas': AreaOperativa.objects.filter(is_active=True, is_deleted=False).order_by('nombre').distinct('nombre'),
        'current_q': filtros['q'],
        'current_sede': str(filtros['sede_id']) if filtros['sede_id'] else "",
        'current_dep': str(filtros['dependencia_id']) if filtros['dependencia_id'] else "",
        'current_area': str(filtros['area_id']) if filtros['area_id'] else "",
    }
    
    return render(request, 'security/global_matrix_forensic.html', context)