# apps/security/views/security_views.py
import json
import uuid
import logging
import traceback
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.http import HttpResponse, HttpResponseForbidden
from django.contrib import messages
from django.views.decorators.http import require_POST

from apps.security.models.organigrama import AreaOperativa, Dependencia, Sede
from apps.shared.apps_config import AppIdentifier
from apps.security.decorators import axentra_gate_enforcer
from apps.security.models import AppModule, UserAppRole, TenantConfig, SecurityAuditLog
from apps.security.forms import TenantConfigForm
from apps.security.selectors.permission_selectors import PermissionSelectors
from apps.security.selectors.security_selectors import CapabilitySelectors, SecurityDashboardSelectors
from apps.security.services.security_services import PermissionService
from apps.security.utils.forensic_auditor import ForensicAuditor

User = get_user_model()
logger = logging.getLogger(__name__)


@login_required
@axentra_gate_enforcer(AppIdentifier.SECURITY, required_fine_permission="has_access_module")
def security_control_panel_view(request):
    """Estación base ligera para el monitoreo táctico y accesos rápidos Core."""
    context = SecurityDashboardSelectors.obtener_metricas_firewall()
    return render(request, 'security/control_panel.html', context)


@login_required
@axentra_gate_enforcer(AppIdentifier.SECURITY, required_fine_permission="can_view_analytics")
def security_dashboard_view(request):
    """
    Consola Central de Ciberseguridad: Audita densidad de llaves JSONField y logs.
    🪐 FILTRADO FORENSE EN CALIENTE: Lee parámetros GET para búsquedas e inspecciones.
    """
    # 🔍 Recolección de parámetros de la URL
    filtros = {
        'app_namespace': request.GET.get('app_namespace', '').strip().lower() or None,
        'action_type': request.GET.get('action_type', '').strip().upper() or None,
        'level_status': request.GET.get('level_status', '').strip().upper() or None,
        'search_target': request.GET.get('search_target', '').strip() or None,
        'operador': request.GET.get('operador', '').strip().lower() or None,
        'fecha_inicio': request.GET.get('fecha_inicio', '').strip() or None,
        'fecha_fin': request.GET.get('fecha_fin', '').strip() or None,
    }

    context = SecurityDashboardSelectors.obtener_metricas_firewall()
    
    # Pasamos el mapa de filtros al buffer analítico
    context['recents_audits'] = SecurityDashboardSelectors.obtener_buffer_auditoria(limite=50, filtros=filtros)
    
    # Inyectamos catálogos y estados actuales al contexto para pintar los formularios HTML
    context.update({
        'apps_sistema': [choice[0] for choice in AppIdentifier.get_choices()],
        'tipos_accion': SecurityAuditLog.ActionTypes.choices,
        'niveles_status': SecurityAuditLog.Levels.choices,
        'filtros_actuales': filtros
    })
    
    return render(request, 'security/dashboard/security_dashboard.html', context)


@login_required
@axentra_gate_enforcer(AppIdentifier.SECURITY, required_fine_permission="can_configure_tenant")
def tenant_config_view(request):
    """SINGLETON IDENTITY ENFORCER: Gobernanza central de marca institucional."""
    config_instancia, _ = TenantConfig.objects.get_or_create(
        id=1, defaults={'app_name': "Axentra OS", 'entidad_nombre': "H. Ayuntamiento Constitucional", 'siglas': "AXN"}
    )
    if request.method == 'POST':
        form = TenantConfigForm(request.POST, request.FILES, instance=config_instancia)
        if form.is_valid():
            form.save()
            
            # 🪐 AUDITORÍA NORMALIZADA PARA ACTUALIZACIÓN DE MARCA INSTITUCIONAL
            ForensicAuditor.registrar_evento(
                request=request,
                action_type=SecurityAuditLog.ActionTypes.UPDATE,
                module_component="IDENTIDAD_GLOBAL",
                action_name="RECONFIGURACION_TENANT_CORE",
                target_scope=f"Modificación de logotipos, colores o RFC legal de la entidad.",
                level=SecurityAuditLog.Levels.CRITICAL,
                search_target=config_instancia.siglas
            )
            messages.success(request, "Los activos de marca de la institución se reconfiguraron correctamente.")
            return redirect('security:control_panel')
    else:
        form = TenantConfigForm(instance=config_instancia)
    return render(request, 'security/forms/tenant_form.html', {'form': form, 'config': config_instancia})


@login_required
@axentra_gate_enforcer(AppIdentifier.SECURITY, required_fine_permission="can_view_matrix")
def dynamic_permission_matrix_view(request):
    """CONTROLADOR DE LECTURA PURO (GET): Despacha el estado de la matriz."""
    app_slug = request.GET.get('app_slug', '').strip().lower()
    if not app_slug:
        return render(request, 'security/errors/400_missing_context.html', {
            'error_detalle': "Bloqueo de Infraestructura: La Consola requiere una firma de aplicación explícita."
        }, status=400)

    app_module = get_object_or_404(AppModule, slug=app_slug, is_active=True)
    user_focus_id = request.GET.get('user_id')
    is_manager_global = getattr(request.user, 'is_manager', False) or (
        hasattr(request.user, 'axentra_profile') and request.user.axentra_profile.is_root_admin
    )

    context = PermissionSelectors.get_secured_matrix_data(
        app_module=app_module, user_focus_id=user_focus_id, request_user=request.user, is_manager_global=is_manager_global
    )
    
    context.update({
        'app': app_module,
        'app_slug_actual': app_module.slug,
        'modulo_actual': app_slug,
        'role_mapping_json': json.dumps(context.get('role_mapping', {})),
        'roles_buscador': [rol[0] for rol in context.get('roles_choices', [])],
    })

    if request.META.get('HTTP_HX_REQUEST'):
        return render(request, 'security/partials/matrix_form_partial.html', context)

    return render(request, 'security/matrix_dynamic.html', context)


@login_required
@axentra_gate_enforcer(AppIdentifier.SECURITY, required_fine_permission="can_modify_matrix")
@require_POST
def guardar_llaves_json_view(request, app_id, user_id):
    """ADUANA DE ENTRADA: Delega la validación de jerarquía y persistencia forense al Servicio."""
    app_module = get_object_or_404(AppModule, id=app_id, is_active=True)
    target_user = get_object_or_404(User, id=user_id)
    
    is_manager_global = getattr(request.user, 'is_manager', False) or (
        hasattr(request.user, 'axentra_profile') and request.user.axentra_profile.is_root_admin
    )

    nuevo_rol = request.POST.get('role') or request.POST.get(f'role_{user_id}') or request.POST.get('nuevo_rol')
    if not nuevo_rol:
        messages.error(request, "⚠️ No se especificó un rol válido en la petición.")
        return redirect(f"/app/security/matriz/?app_slug={app_module.slug}&user_id={target_user.id}")

    llaves_encendidas = request.POST.getlist('permisos_checks') or request.POST.getlist(f'user_{user_id}') or []

    # 👑 CAPA DE DELEGACIÓN ABSOLUTA: El servicio se encarga de calcular deltas, validar jerarquía y auditar
    exito, mensaje = PermissionService.save_matrix_permissions(
        request=request,
        target_user=target_user,
        app_module=app_module,
        nuevo_rol=nuevo_rol,
        llaves_encendidas=llaves_encendidas,
        is_manager_bypass=is_manager_global
    )

    if exito:
        messages.success(request, mensaje)
    else:
        messages.error(request, mensaje)
        
    return redirect(f"/app/security/matriz/?app_slug={app_module.slug}&user_id={target_user.id}")


@login_required
@axentra_gate_enforcer(AppIdentifier.SECURITY, required_fine_permission="can_modify_matrix")
@require_POST
def inyectar_funcionario_view(request, app_id):
    """Inyecta un funcionario al padrón de membresía delegando la auditoría al servicio."""
    app_module = get_object_or_404(AppModule, id=app_id, is_active=True)
    is_manager_global = getattr(request.user, 'is_manager', False) or (
        hasattr(request.user, 'axentra_profile') and request.user.axentra_profile.is_root_admin
    )

    if not is_manager_global:
        messages.error(request, "🚫 Acceso Denegado: Operación exclusiva del Master central.")
        return redirect(f"/app/security/matriz/?app_slug={app_module.slug}")

    nuevo_usuario_id = request.POST.get('new_user_id')
    rol_a_inyectar = request.POST.get('initial_role', 'viewer')
    target_user = get_object_or_404(User, id=nuevo_usuario_id)

    # El servicio se encarga de sembrar y auditar en frío de forma limpia
    if PermissionService.authorize_new_user_entry(request, app_module, str(target_user.id), rol_a_inyectar):
        messages.success(request, f"🟢 Funcionario {target_user.email} inyectado con éxito.")
    else:
        messages.warning(request, "⚠️ Operación cancelada: El funcionario ya cuenta con membresía activa.")
        
    return redirect(f"/app/security/matriz/?app_slug={app_module.slug}&user_id={target_user.id}")


@login_required
@axentra_gate_enforcer(AppIdentifier.SECURITY, required_fine_permission="can_modify_matrix")
@require_POST
def toggle_user_modulo_active_ajax_view(request, user_id, app_id):
    """Conmuta el estado activo/suspendido de un funcionario e inyecta la bitácora."""
    app_module = get_object_or_404(AppModule, id=app_id)
    target_user = get_object_or_404(User, id=user_id)
    is_manager_global = getattr(request.user, 'is_manager', False) or getattr(request.user, 'is_superuser', False)
    
    if str(target_user.id) == str(request.user.id):
        return HttpResponseForbidden("Operación denegada: No puedes auto-suspender tu perfil.")
        
    rol_instancia = get_object_or_404(UserAppRole, user=target_user, app=app_module)
    if rol_instancia.role.lower() == 'owner' and not is_manager_global:
        return HttpResponseForbidden("Acceso denegado: Rango protegido por jerarquía superior.")

    rol_instancia.is_active = not rol_instancia.is_active
    rol_instancia.save()
    
    # 🪐 AUDITORÍA NORMALIZADA: Conmutador de estado perimetral (Verbo RESET debido al Lockdown)
    ForensicAuditor.registrar_evento(
        request=request,
        action_type=SecurityAuditLog.ActionTypes.RESET,
        module_component="ESTADO_MEMBRESIA",
        action_name="TOGGLE_SUSPENSION_MODULO",
        target_scope=f"Conmutación de membresía para {target_user.email} en {app_module.name} (Estado: {rol_instancia.is_active}).",
        level=SecurityAuditLog.Levels.INFO if rol_instancia.is_active else SecurityAuditLog.Levels.CRITICAL,
        target_user=target_user,
        search_target=target_user.id,
        payload={'is_active_final': rol_instancia.is_active, 'app_slug': app_module.slug}
    )
    
    response = HttpResponse(status=200, content="")
    response['HX-Refresh'] = 'true'
    return response


@login_required
@require_POST
def expulsar_usuario_modulo_total_ajax_view(request, user_id, app_id):
    """💥 KILL-SWITCH ABSOLUTO: Remueve la membresía de la base de datos."""
    is_manager_global = getattr(request.user, 'is_manager', False) or getattr(request.user, 'is_superuser', False)
    if not is_manager_global:
        return HttpResponseForbidden("Acceso denegado: Requiere nivel Mánager Supremo.")
        
    app_module = get_object_or_404(AppModule, id=app_id)
    target_user = get_object_or_404(User, id=user_id)
    
    if str(target_user.id) == str(request.user.id):
        return HttpResponseForbidden("Operación denegada: Auto-purga bloqueada por estabilidad.")
        
    rol_instancia = UserAppRole.objects.filter(user=target_user, app=app_module).first()
    if rol_instancia:
        # 🪐 AUDITORÍA NORMALIZADA: Purga total física de credenciales (Verbo DELETE)
        ForensicAuditor.registrar_evento(
            request=request,
            action_type=SecurityAuditLog.ActionTypes.DELETE,
            module_component="ELIMINACION_MEMBRESIA",
            action_name="PURGA_TOTAL_CREDENCIONALES",
            target_scope=f"Destrucción total física de los privilegios de {target_user.email} en {app_module.name}",
            level=SecurityAuditLog.Levels.CRITICAL,
            target_user=target_user,
            search_target=target_user.id,
            payload={'deleted_role': rol_instancia.role}
        )
        rol_instancia.delete()
    
    response = HttpResponse(status=200, content="")
    response['HX-Refresh'] = 'true'
    return response


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
    from apps.security.models.organigrama import AppDependencyCapability
    
    capacidad, created = AppDependencyCapability.objects.get_or_create(
        app=app_obj, dependencia=dep_obj, defaults={'flag_alfa': False, 'flag_beta': False}
    )

    if created:
        # 🪐 AUDITORÍA NORMALIZADA: Vinculación de nodos organizacionales (Verbo CREATE)
        ForensicAuditor.registrar_evento(
            request=request,
            action_type=SecurityAuditLog.ActionTypes.CREATE,
            module_component="MAPA_CAPACIDADES",
            action_name="VINCULACION_NODO_CAPACIDAD",
            target_scope=f"Asignación de derecho de consumo de {app_obj.name} a la dependencia {dep_obj.nombre}.",
            level=SecurityAuditLog.Levels.INFO,
            search_target=str(dep_obj.id)
        )

    response = HttpResponse(status=200)
    response['HX-Refresh'] = 'true'
    return response


@login_required
@axentra_gate_enforcer(AppIdentifier.SECURITY, required_fine_permission="can_configure_tenant")
@require_POST
def toggle_capability_ajax_view(request, dep_id, app_id):
    """Interruptor AJAX universal para prender/apagar capacidades organizacionales."""
    app_obj = get_or_404_or_redirect = get_object_or_404(AppModule, id=app_id)
    dep_obj = get_object_or_404(Dependencia, id=dep_id)
    field = request.POST.get('field')
    
    if field not in ['flag_alfa', 'flag_beta']:
        return HttpResponse('❌ Campo operativo inválido', status=400)

    from apps.security.models.organigrama import AppDependencyCapability
    capacidad, _ = AppDependencyCapability.objects.get_or_create(app=app_obj, dependencia=dep_obj)
    nuevo_estado = not getattr(capacidad, field)
    setattr(capacidad, field, nuevo_estado)
    capacidad.save()

    # 🪐 AUDITORÍA NORMALIZADA: Conmutador de banderas de comportamiento operativo (Verbo UPDATE)
    ForensicAuditor.registrar_evento(
        request=request,
        action_type=SecurityAuditLog.ActionTypes.UPDATE,
        module_component="MAPA_CAPACIDADES",
        action_name="TOGGLE_CONFIG_CAPACIDAD",
        target_scope=f"Bandera [{field}] alternada a {nuevo_estado} para {dep_obj.nombre} en {app_obj.name}.",
        level=SecurityAuditLog.Levels.INFO,
        search_target=str(dep_obj.id),
        payload={'campo_mutado': field, 'estado_final': nuevo_estado}
    )

    labels_manifiesto = CapabilitySelectors.obtener_labels_manifiesto(app_obj.slug)
    config_campo = labels_manifiesto.get(field, {})
    help_text_dinamico = config_campo.get('help_text', 'Configuración de capacidad guardada con éxito.')

    bg_active_class = "bg-blue-600 justify-end" if field == "flag_alfa" else "bg-indigo-600 justify-end"
    bg_class = bg_active_class if nuevo_estado else "bg-gray-200 justify-start"
    
    return render(request, 'security/htmx/capability_switch_partial.html', {
        'next_url': f"/app/security/platform/capabilities/toggle/{dep_obj.id}/{app_obj.id}/",
        'bg_class': bg_class,
        'help_text': help_text_dinamico
    })


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



@login_required
@axentra_gate_enforcer(AppIdentifier.SECURITY, required_fine_permission="can_view_analytics")
def descargar_auditoria_excel_view(request):
    """
    ENDPOINT DE EXTRACCIÓN: Captura la query actual de la URL
    y descarga la evidencia completa sin límites de paginación.
    """
    # 🟢 SANEADO: Extracción limpia del GET sin colisiones de asignación
    filtros = {
        'app_namespace': request.GET.get('app_namespace', '').strip().lower() or None,
        'action_type': request.GET.get('action_type', '').strip().upper() or None,
        'level_status': request.GET.get('level_status', '').strip().upper() or None,
        'search_target': request.GET.get('search_target', '').strip() or None,
        'operador': request.GET.get('operador', '').strip().lower() or None,
        'fecha_inicio': request.GET.get('fecha_inicio', '').strip() or None,
        'fecha_fin': request.GET.get('fecha_fin', '').strip() or None,
    }
    
    # Invocamos la generación física del libro de Excel pasándole el request para el contexto si es necesario
    return PermissionService.exportar_auditoria_excel(filtros)