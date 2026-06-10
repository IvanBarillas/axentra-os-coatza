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

# Selectores y Servicios Remotes
from apps.security.selectors.security_selectors import SecurityDashboardSelectors
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
    """Consola Maestra de Privilegios Finos Universal con blindaje Anti-URL Tampering."""
    app_slug = request.GET.get('app_slug') or request.POST.get('app_slug')
    
    # 🛡️ Cortafuegos de URLs Desnudas: Intercepta peticiones sin contexto de app
    if not app_slug:
        logger.warning(f"🛑 [INTENTO DE BYPASS]: {request.user.email} intentó entrar a la matriz sin app_slug.")
        return render(request, 'security/errors/400_missing_context.html', {
            'error_detalle': "Bloqueo de Infraestructura: La Consola de Privilegios requiere una firma de aplicación explícita."
        }, status=400)

    app_slug = app_slug.strip().lower()
    app_module = get_object_or_404(AppModule, slug=app_slug, is_active=True)
    user_focus_id = request.GET.get('user_id')
    is_manager_global = getattr(request.user, 'is_manager', False) or request.user.axentra_profile.is_root_admin

    # ---------------------------------------------------------------------
    # INTERCEPTOR DE PETICIONES MUTACIONALES (POST METHOD)
    # ---------------------------------------------------------------------
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        action = request.POST.get('action')

        # Acción A: Modificación de Checkboxes de la Grilla JSON
        if action == "update_permissions":
            nuevo_rol_base = request.POST.get(f'role_{user_id}') or request.POST.get('role') or request.POST.get('nuevo_rol')
            llaves_encendidas = request.POST.getlist(f'user_{user_id}') or request.POST.getlist('permisos_checks') or []
            nuevo_rol_base = nuevo_rol_base.lower().strip()

            target_user = get_object_or_404(User, id=user_id)
            rol_actual_obj = UserAppRole.objects.filter(user=target_user, app=app_module).first()
            rol_actual_str = rol_actual_obj.role if rol_actual_obj else 'viewer'

            # Guardián Jerárquico de Pesos locales
            if not is_manager_global:
                rol_operador_obj = UserAppRole.objects.filter(user=request.user, app=app_module, is_active=True).first()
                rol_operador_str = rol_operador_obj.role if rol_operador_obj else 'viewer'
                
                peso_operador = ROLE_WEIGHTS.get(rol_operador_str, 0)
                peso_actual_destino = ROLE_WEIGHTS.get(rol_actual_str, 0)
                peso_nuevo_destino = ROLE_WEIGHTS.get(nuevo_rol_base, 0)

                if peso_actual_destino >= peso_operador or peso_nuevo_destino >= peso_operador:
                    messages.error(request, "🚫 Violación de Escalafón: Tus privilegios locales no tienen el peso jerárquico para alterar o declarar este rango.")
                    return redirect(f"{request.path}?app_slug={app_slug}&user_id={user_id}")

            config_app = get_app_permissions(app_slug)
            if nuevo_rol_base == "owner":
                llaves_encendidas = list(config_app.get('permissions', {}).keys())

            if 'has_access_module' not in llaves_encendidas:
                llaves_encendidas.append('has_access_module')

            if PermissionService.save_matrix_permissions(target_user, app_module, nuevo_rol_base, llaves_encendidas):
                messages.success(request, f"🔒 Matriz de configuración actualizada para {target_user.full_name}.")
            else:
                messages.error(request, "❌ Error de consistencia al procesar la mutación en PostgreSQL.")
                
            return redirect(f"{request.path}?app_slug={app_slug}&user_id={user_id}")

        # Acción B: Incorporación de Funcionario Nuevo al aplicativo satélite
        elif action == "authorize_entry":
            if not is_manager_global:
                messages.error(request, "🚫 Acceso Denegado: La inyección perimetral de personal es exclusiva del Master central.")
                return redirect(f"{request.path}?app_slug={app_slug}")

            nuevo_usuario_id = request.POST.get('new_user_id')
            rol_a_inyectar = request.POST.get('initial_role', 'viewer').lower().strip()
            target_user = get_object_or_404(User, id=nuevo_usuario_id)

            if PermissionService.authorize_new_user_entry(app_module, str(target_user.id), rol_a_inyectar):
                messages.success(request, f"🟢 Funcionario {target_user.email} inyectado con éxito como [{rol_a_inyectar.upper()}].")
            else:
                messages.warning(request, "⚠️ Operación cancelada: El funcionario ya cuenta con membresía activa o el proceso falló.")
                
            return redirect(f"{request.path}?app_slug={app_slug}&user_id={target_user.id}")

    # ---------------------------------------------------------------------
    # RESOLUCIÓN DE INTERFAZ Y RENDERIZADO (GET METHOD)
    # ---------------------------------------------------------------------
    roles_activos = UserAppRole.objects.filter(app=app_module).select_related('user').exclude(user__is_manager=True).order_by('user__first_name')
    
    config_app = get_app_permissions(app_slug)
    catalogo_permisos = config_app.get('permissions', {})
    role_mapping = config_app.get('roles', {})
    
    personal_list = []
    usuario_enfocado_data = None
    
    for r in roles_activos:
        es_el_seleccionado = str(r.user.id) == str(user_focus_id)
        personal_list.append({
            'usuario': r.user,
            'rol_actual': r.role.upper(),
            'es_el_seleccionado': es_el_seleccionado,
            'is_suspended': not r.is_active
        })
        
        if es_el_seleccionado:
            permisos_raw = r.permissions_list or []
            permisos_usuario_lista = [p for p in permisos_raw if p in catalogo_permisos]
            
            permisos_permitidos_por_rol = role_mapping.get(r.role, [])
            payload_llaves = []
            for code, desc in catalogo_permisos.items():
                if code not in permisos_permitidos_por_rol:
                    continue
                obligatorio_by_role = (code == 'has_access_module') or (r.role == 'owner')
                payload_llaves.append({
                    'llave': code,
                    'descripcion': desc,
                    'concedido_total': (code in permisos_usuario_lista) or obligatorio_by_role,
                    'obligatorio_by_role': obligatorio_by_role
                })
            
            # Cálculo semántico de bloqueos visuales
            bloqueo_visual = False
            motivo_bloqueo = "none"

            if not is_manager_global:
                rol_operador_obj = UserAppRole.objects.filter(user=request.user, app=app_module, is_active=True).first()
                rol_operador_str = rol_operador_obj.role if rol_operador_obj else 'viewer'
                
                peso_operador = ROLE_WEIGHTS.get(rol_operador_str, 0)
                peso_destino = ROLE_WEIGHTS.get(r.role, 0)

                if str(r.user.id) == str(request.user.id):
                    bloqueo_visual = True
                    motivo_bloqueo = "auto_lock"
                elif r.role == 'owner':
                    bloqueo_visual = True
                    motivo_bloqueo = "owner_lock"
                elif peso_destino >= peso_operador:
                    bloqueo_visual = True
                    motivo_bloqueo = "weight_lock"

            usuario_enfocado_data = {
                'usuario': r.user,
                'rol_actual': r.role,
                'permisos': payload_llaves,
                'bloqueo_visual': bloqueo_visual or (not r.is_active),
                'motivo_bloqueo': "suspended_lock" if not r.is_active else motivo_bloqueo
            }

    if is_manager_global:
        usuarios_ya_asignados = UserAppRole.objects.filter(app=app_module).values_list('user_id', flat=True)
        usuarios_potenciales = User.objects.filter(is_active=True, is_superuser=False, is_manager=False).exclude(id__in=usuarios_ya_asignados).order_by('first_name')
        mostrar_buscador = True
    else:
        usuarios_potenciales = None
        mostrar_buscador = False

    roles_grilla = [(val, etiqueta) for val, etiqueta in UserAppRole.Roles.choices if val != 'owner' or is_manager_global]

    return render(request, 'security/matrix_dynamic.html', {
        'app': app_module,
        'app_slug_actual': app_module.slug,
        'modulo_actual': app_slug,
        'personal_list': personal_list,
        'usuario_enfocado': usuario_enfocado_data,
        'roles_choices': roles_grilla,
        'roles_buscador': list(UserAppRole.Roles.choices),
        'role_mapping': role_mapping,
        'mostrar_buscador': mostrar_buscador,
        'usuarios_potenciales': usuarios_potenciales
    })
    
    
# =========================================================================
# 🎛️ PILAR 5: CONSOLA DE CAPACIDADES REGIONALES POR DEPENDENCIAS (HTMX)
# =========================================================================
@login_required
@axentra_gate_enforcer(AppIdentifier.SECURITY, required_fine_permission="can_configure_tenant")
def matrix_capabilities_view(request):
    """Master de Capacidades Regionales: Muestra qué dependencias consumen qué apps."""
    app_slug = request.GET.get('app_slug', 'accounts')
    app_activa = get_object_or_404(AppModule, slug=app_slug)
    
    labels_config = {
        'flag_alfa': {'label': "Capacidad Primaria (Alfa)", 'help_text': "Activar rol primario institucional."},
        'flag_beta': {'label': "Capacidad Secundaria (Beta)", 'help_text': "Activar rol secundario de soporte."}
    }
    
    try:
        modulo_permissions = importlib.import_module(f"apps.security.permissions")
        for attr_name in dir(modulo_permissions):
            if attr_name.endswith("Permissions") and attr_name.lower().startswith(app_slug):
                clase_permisos = getattr(modulo_permissions, attr_name)
                if hasattr(clase_permisos, 'CAPABILITIES'):
                    labels_config = clase_permisos.CAPABILITIES
                break
    except Exception:
        pass

    capacidades_reales = AppDependencyCapability.objects.filter(app=app_activa).select_related('dependencia')
    deps_ya_vinculadas = capacidades_reales.values_list('dependencia_id', flat=True)
    dependencias_disponibles = Dependencia.objects.filter(is_active=True, is_deleted=False).exclude(id__in=deps_ya_vinculadas).order_by('nombre')

    return render(request, 'security/matrix_capabilities.html', {
        'apps': AppModule.objects.filter(is_active=True),
        'app_activa': app_activa,
        'matriz': capacidades_reales,
        'dependencias_disponibles': dependencias_disponibles,
        'labels': labels_config,
        'modulo_actual': 'security'
    })


@login_required
@axentra_gate_enforcer(AppIdentifier.SECURITY, required_fine_permission="can_configure_tenant")
def add_capability_node_view(request, app_id):
    """Vincula una nueva dependencia al mapa relacional de capacidades de la App."""
    if request.method == 'POST':
        app_obj = get_object_or_404(AppModule, id=app_id)
        dependencia_id = request.POST.get('dependencia_id')
        
        if not dependencia_id:
            return HttpResponse('⚠️ Seleccione una dependencia válida.', status=400)
            
        dep_obj = get_object_or_404(Dependencia, id=dependencia_id)
        AppDependencyCapability.objects.get_or_create(
            app=app_obj, dependencia=dep_obj, defaults={'flag_alfa': False, 'flag_beta': False}
        )

        response = HttpResponse()
        response['HX-Refresh'] = 'true'
        return response
    return HttpResponseBadRequest("Método no permitido.")


@login_required
@axentra_gate_enforcer(AppIdentifier.SECURITY, required_fine_permission="can_configure_tenant")
def toggle_capability_ajax_view(request, dep_id, app_id):
    """Interruptor AJAX ultrarrápido para prender/apagar capacidades organizacionales."""
    if request.method != 'POST':
        return HttpResponseBadRequest("Método inválido.")
        
    app_obj = get_object_or_404(AppModule, id=app_id)
    dep_obj = get_object_or_404(Dependencia, id=dep_id)
    field = request.POST.get('field')
    
    if field not in ['flag_alfa', 'flag_beta']:
        return HttpResponse('❌ Campo inválido', status=400)

    capacidad, _ = AppDependencyCapability.objects.get_or_create(app=app_obj, dependencia=dep_obj)
    nuevo_estado = not getattr(capacidad, field)
    setattr(capacidad, field, nuevo_estado)
    capacidad.save()

    bg_active_class = "bg-blue-600 justify-end" if field == "flag_alfa" else "bg-indigo-600 justify-end"
    bg_class = bg_active_class if nuevo_estado else "bg-slate-200 justify-start"
    next_url = f"/app/security/platform/capabilities/toggle/{dep_obj.id}/{app_obj.id}/"
    
    return HttpResponse(f"""
        <div hx-post="{next_url}"
             hx-trigger="click"
             hx-target="this"
             hx-swap="outerHTML"
             hx-include="closest form"
             class="w-11 h-6 flex items-center {bg_class} rounded-full p-1 cursor-pointer transition-all duration-300">
            <div class="w-4 h-4 bg-white rounded-full shadow"></div>
        </div>
    """)


@login_required
@axentra_gate_enforcer(AppIdentifier.SECURITY, required_fine_permission="can_modify_matrix")
@require_POST
def toggle_user_modulo_active_ajax_view(request, user_id, app_id):
    """
    🔄 SWITCH PERIMETRAL CORE (HTMX RESPUESTA): Invierte el estatus 'is_active' del usuario.
    🟢 EXTRIPACIÓN COMPLETA DE RECURSIÓN: Retorna texto HTML directo, inmune a dependencias en cadena.
    """
    app_module = get_object_or_404(AppModule, id=app_id)
    target_user = get_object_or_404(User, id=user_id)
    
    if target_user.is_manager or str(target_user.id) == str(request.user.id):
        return HttpResponse(status=403, content="Operación denegada.")
        
    rol_instancia = get_object_or_404(UserAppRole, user=target_user, app=app_module)
    rol_instancia.is_active = not rol_instancia.is_active
    rol_instancia.save()
    
    logger.warning(f"🚨 CIBERSEGURIDAD: Estado de {target_user.email} conmutado a [Activo={rol_instancia.is_active}] en App [{app_module.slug.upper()}].")
    
    # Determinamos el color dinámico del botón de encendido/congelado según Postgres
    btn_color_class = "bg-emerald-50 text-emerald-600 border-emerald-200 hover:bg-emerald-600 hover:text-white" if rol_instancia.is_active else "bg-amber-50 text-amber-600 border-amber-200 hover:bg-amber-600 hover:text-white"
    
    # 🚀 RENDERIZADO INLINE SEGURO: Rompe el bucle infinito al no usar plantillas hijas recursivas
    html_response = f"""
    <div class="absolute right-3 opacity-0 group-hover/tarjeta:opacity-100 flex items-center gap-1.5 transition-all duration-150 z-10 p-1" id="actions-wrapper-{target_user.id}">
        <button type="button"
                hx-post="/app/security/matriz/toggle-status/{target_user.id}/{app_module.id}/"
                hx-target="#actions-wrapper-{target_user.id}"
                hx-swap="outerHTML"
                class="p-1.5 rounded-lg border transition duration-150 cursor-pointer shadow-3xs {btn_color_class}">
            <i data-lucide="power" class="w-3.5 h-3.5"></i>
        </button>
    """
    
    # Inyectamos quirúrgicamente el botón de purga solo si el operador es un mánager supremo
    if getattr(request.user, 'is_manager', False) or getattr(request.user, 'is_superuser', False):
        html_response += f"""
        <button type="button"
                hx-post="/app/security/matriz/purga-total/{target_user.id}/{app_module.id}/"
                hx-target="#user-row-container-{target_user.id}"
                hx-swap="delete"
                hx-confirm="🚨 ¿EJECUTAR PURGA TOTAL? Esta acción eliminará permanentemente la membresía y todo el árbol de llaves guardado para {target_user.full_name.upper()}."
                class="p-1.5 rounded-lg bg-red-50 text-red-600 border border-red-200 hover:bg-red-600 hover:text-white transition duration-150 cursor-pointer shadow-3xs">
            <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
        </button>
        """
        
    html_response += """
    </div>
    <script>if (typeof lucide !== 'undefined') { lucide.createIcons(); }</script>
    """
    return HttpResponse(status=200, content=html_response)


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
        
    # Purga total en PostgreSQL
    UserAppRole.objects.filter(user=target_user, app=app_module).delete()
    
    logger.warning(f"🚨 EXPULSIÓN SUPREMA: {request.user.email} ELIMINÓ a {target_user.email} de la App [{app_module.slug.upper()}].")
    return HttpResponse(status=200, content="")