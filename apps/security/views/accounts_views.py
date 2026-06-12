# apps/security/views/accounts_views.py
import uuid
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.http import HttpResponse
from django.contrib.auth.forms import SetPasswordForm

from apps.shared.apps_config import AppIdentifier
from apps.security.decorators import axentra_gate_enforcer
from apps.security.models import User, UserProfile
from apps.security.models.organigrama import Dependencia, AreaOperativa, Sede
from apps.security.selectors.accounts_selectors import AccountsDashboardSelectors, FuncionarioSelectors
from apps.security.services.accounts_services import FuncionarioService
from apps.security.forms import (
    StaffUserCreationForm, StaffUserProfileForm, 
    StaffUserChangeForm, StaffUserProfileChangeForm, 
    AdminPasswordChangeForm
)

User = get_user_model()
logger = logging.getLogger(__name__)

@login_required
@axentra_gate_enforcer(AppIdentifier.ACCOUNTS, required_fine_permission="has_access_module")
def accounts_control_panel_view(request):
    """Panel Administrativo: Chasis ligero operativo libre de métricas gerenciales pesadas."""
    return render(request, 'accounts/control_panel.html')


@login_required
@axentra_gate_enforcer(AppIdentifier.ACCOUNTS, required_fine_permission="can_view_analytics")
def accounts_dashboard_view(request):
    """Consola Analítica: Centraliza KPIs de personal e inyecta la telemetría cronológica."""
    # 🟢 Unificamos las métricas estáticas y las dinámicas en un solo contexto analítico
    context = AccountsDashboardSelectors.obtener_metricas_plantilla()
    context['cronologia_altas'] = AccountsDashboardSelectors.obtener_cronologia_altas()
    
    return render(request, 'accounts/dashboard/accounts_dashboard.html', context)


# =========================================================================
# 👤 PILAR UNIQUE: GESTIÓN DE EXPEDIENTES Y SERVIDORES PÚBLICOS
# =========================================================================

@login_required
@axentra_gate_enforcer(AppIdentifier.ACCOUNTS, required_fine_permission="can_view_list")
def funcionario_list_view(request):
    """
    Despacha la nómina general filtrada mediante selectores optimizados de matriz.
    Mantiene el soporte híbrido HTMX aislando los retornos de fragmentos puros.
    """
    search_query = request.GET.get('q', '').strip()
    sede_id = request.GET.get('sede', '').strip()
    dependencia_id = request.GET.get('dependencia', '').strip()
    area_id = request.GET.get('area', '').strip()
    
    # Sanitización de banderas por defecto de interfaz
    if sede_id.lower() in ['all', 'none', '']: sede_id = ""
    if dependencia_id.lower() in ['all', 'none', '']: dependencia_id = ""
    if area_id.lower() in ['all', 'none', '']: area_id = ""
    
    funcionarios = FuncionarioSelectors.listar_plantilla_activa(
        search_query=search_query,
        sede_id=sede_id,
        dependencia_id=dependencia_id,
        area_id=area_id
    )
    
    context = {
        'funcionarios': funcionarios,
        'sedes': Sede.objects.filter(is_deleted=False).order_by('nombre'),
        'dependencias': Dependencia.objects.filter(is_deleted=False).order_by('nombre'),
        'areas_operativas': AreaOperativa.objects.filter(is_deleted=False).order_by('nombre'),
        'current_q': search_query,
        'current_sede': request.GET.get('sede', ''),
        'current_dep': request.GET.get('dependencia', ''),
        'current_area': request.GET.get('area', ''),
        'target_id': 'dynamic-workspace-target', # Actualizado al contenedor maestro híbrido
    }
    
    es_htmx = (
        request.headers.get('HX-Request') == 'true' or 
        request.headers.get('hx-request') == 'true' or
        request.META.get('HTTP_HX_REQUEST') == 'true'
    )
    
    if es_htmx:
        # 🟢 RETORNO HÍBRIDO: Envía la estructura adaptativa mutada sin romper el árbol jerárquico del DOM
        return render(request, 'accounts/htmx/funcionario_hibrido_partial.html', context)
        
    return render(request, 'accounts/funcionario_list.html', context)


@login_required
@axentra_gate_enforcer(AppIdentifier.ACCOUNTS, required_fine_permission='can_edit_user')
def funcionario_create_view(request):
    """Orquestador transaccional e inyección de altas de nuevos servidores públicos."""
    if request.method == 'POST':
        datos_saneados = request.POST.copy()
        if 'area' in datos_saneados and not datos_saneados['area'].strip():
            datos_saneados['area'] = ''

        form = StaffUserCreationForm(datos_saneados)
        profile_form = StaffUserProfileForm(datos_saneados)

        if form.is_valid() and profile_form.is_valid():
            area_instancia = profile_form.cleaned_data.get('area')
            payload = {
                'email': form.cleaned_data.get('email'),
                'first_name': form.cleaned_data.get('first_name'),
                'last_name': form.cleaned_data.get('last_name'),
                'phone': form.cleaned_data.get('phone'),
                'area_id': area_instancia.id if area_instancia else None,
                'puesto': profile_form.cleaned_data.get('puesto'),
                'telefono_oficina': profile_form.cleaned_data.get('telefono_oficina')
            }
            
            # 🟢 CABLEADO FORENSE: Se inyecta el 'request' para heredar IP y User-Agent al log automático
            exito, usuario, errores = FuncionarioService.crear_funcionario(
                request=request, 
                post_data=payload, 
                raw_password=form.cleaned_data.get('password')
            )

            if exito and usuario:
                messages.success(request, f"El funcionario {usuario.full_name} ha sido dado de alta con éxito.")
                return redirect('accounts:funcionario_list')
            if errores:
                form.add_error(None, errores.get('server_error', ['Error de consistencia interna'])[0])
    else:
        form = StaffUserCreationForm()
        profile_form = StaffUserProfileForm()

    return render(request, 'accounts/forms/funcionario_form.html', {'form': form, 'profile_form': profile_form})


@login_required
@axentra_gate_enforcer(AppIdentifier.ACCOUNTS, required_fine_permission='can_edit_user')
def funcionario_editar_view(request, pk: uuid.UUID):
    """Modificación atómica en caliente de expedientes maestros de adscripción."""
    usuario_instance = get_object_or_404(User, id=pk)
    perfil_instance = get_object_or_404(UserProfile, user=usuario_instance)

    if request.method == 'POST':
        datos_saneados = request.POST.copy()
        if 'area' in datos_saneados and not datos_saneados['area'].strip():
            datos_saneados['area'] = ''

        form_user = StaffUserChangeForm(datos_saneados, instance=usuario_instance)
        form_profile = StaffUserProfileChangeForm(datos_saneados, instance=perfil_instance)

        if form_user.is_valid() and form_profile.is_valid():
            area_instancia = form_profile.cleaned_data.get('area')
            payload = {
                'email': form_user.cleaned_data.get('email'),
                'first_name': form_user.cleaned_data.get('first_name'),
                'last_name': form_user.cleaned_data.get('last_name'),
                'phone': form_user.cleaned_data.get('phone'),
                'area_id': area_instancia.id if area_instancia else None,
                'puesto': form_profile.cleaned_data.get('puesto'),
                'telefono_oficina': form_profile.cleaned_data.get('telefono_oficina')
            }
            
            # 🟢 CABLEADO FORENSE: Se inyecta el 'request' para calcular el delta en caliente
            exito, usuario, errores = FuncionarioService.editar_funcionario(
                request=request, 
                pk=pk, 
                post_data=payload
            )
            if exito:
                messages.success(request, f"La ficha de {usuario.full_name} se actualizó correctamente.")
                return redirect('accounts:funcionario_list')
            if errores:
                form_user.add_error(None, errores.get('server_error', ['Fallo del Servidor'])[0])
    else:
        form_user = StaffUserChangeForm(instance=usuario_instance)
        form_profile = StaffUserProfileChangeForm(instance=perfil_instance)

    return render(request, 'accounts/forms/funcionario_update_form.html', {
        'form_user': form_user, 
        'form_profile': form_profile, 
        'funcionario': usuario_instance
    })


@login_required
@axentra_gate_enforcer(AppIdentifier.ACCOUNTS, required_fine_permission='can_change_password')
def funcionario_cambiar_password_view(request, pk: uuid.UUID):
    """Cifrado administrativo forzado de contraseñas con inyección perimetral de logs de auditoría."""
    usuario_instance = get_object_or_404(get_user_model(), id=pk)
    
    if request.method == 'POST':
        form = SetPasswordForm(user=usuario_instance, data=request.POST)
        if form.is_valid():
            nueva_password = form.cleaned_data.get('new_password1')
            
            # 🟢 REFACTOR CRÍTICO: En lugar de guardar desde el formulario plano, invocamos 
            # el método del servicio para que la mutación criptográfica caiga directo en la bitácora
            success = FuncionarioService.forzar_reseteo_password(
                request=request, 
                pk=pk, 
                nueva_password=nueva_password
            )
            
            if success:
                messages.success(request, f"🔒 Credenciales restablecidas con éxito para {usuario_instance.full_name}.")
            else:
                messages.error(request, "❌ No se pudo restablecer la credencial en el Core.")
                
            return redirect('accounts:funcionario_list')
    else:
        form = SetPasswordForm(user=usuario_instance)

    return render(request, 'accounts/forms/funcionario_password_form.html', {'form': form, 'funcionario': usuario_instance})


@require_POST
@login_required
@axentra_gate_enforcer(AppIdentifier.ACCOUNTS, required_fine_permission='can_delete_user')
def funcionario_soft_delete_view(request, pk: uuid.UUID):
    """Baja lógica forense (Soft-Delete) adaptada a desvanecimiento reactivo HTMX."""
    if str(pk) == str(request.user.id):
        if request.headers.get('HX-Request'):
            return HttpResponse(status=403, content="Operación denegada sobre su propia sesión.")
        messages.error(request, "Operación denegada: No puede aplicar una baja sobre su propia sesión.")
        return redirect('accounts:funcionario_list')

    # 🟢 CABLEADO FORENSE: Pasamos el 'request' como primer parámetro
    exito, mensaje = FuncionarioService.tramitar_baja_institucional(
        request=request, 
        pk=pk, 
        operador_email=request.user.email
    )
    
    if request.headers.get('HX-Request') or request.headers.get('hx-request'):
        return HttpResponse(status=200, content="")

    if exito:
        messages.warning(request, mensaje)
    else:
        messages.error(request, mensaje)
    return redirect('accounts:funcionario_list')


@require_POST
@login_required
@axentra_gate_enforcer(AppIdentifier.ACCOUNTS, required_fine_permission='can_edit_user')
def funcionario_toggle_status_view(request, pk: uuid.UUID):
    """Alternador AJAX de estatus operativo (is_active) con inyector forense manual."""
    if str(pk) == str(request.user.id):
        return HttpResponse(status=403, content="Bloqueo de seguridad: Auto-congelación denegada.")
        
    funcionario = get_object_or_404(User, id=pk)
    
    # Previene mutación de cuentas lógicamente borradas
    if funcionario.is_deleted:
        return HttpResponse(status=400, content="No se puede conmutar el estatus de un usuario dado de baja.")
        
    estado_anterior = funcionario.is_active
    funcionario.is_active = not funcionario.is_active
    funcionario.save()
    
    # 🪐 LOG MANUAL EN CALIENTE DESDE LA VISTA AUXILIAR
    from apps.security.utils.forensic_auditor import ForensicAuditor
    from apps.security.models.audit import SecurityAuditLog
    
    ForensicAuditor.registrar_evento(
        request=request,
        action_type=SecurityAuditLog.ActionTypes.UPDATE,
        module_component="MATRIZ_PERMISOS",
        action_name="TOGGLE_STATUS_FUNCIONARIO",
        target_scope=f"Conmutación de estatus de cuenta para {funcionario.email} (Estado final: {funcionario.is_active}).",
        level=SecurityAuditLog.Levels.INFO if funcionario.is_active else SecurityAuditLog.Levels.CRITICAL,
        target_user=funcionario,
        search_target=funcionario.id,
        payload={'is_active_before': estado_anterior, 'is_active_after': funcionario.is_active}
    )
    
    # 🟢 CORRECCIÓN DE INTERFAZ: Si es HTMX, mandamos un disparador para actualizar la celda o re-renderizamos el badge
    if request.headers.get('HX-Request') or request.headers.get('hx-request'):
        # Retorna el componente del Badge con el nuevo estado sin tumbar la tabla
        return render(request, 'common/tags/badge_toggle_activo_inactivo.html', {
            'is_active': funcionario.is_active,
            'toggle_url': reverse('accounts:funcionario_toggle_status', args=[funcionario.id])
        })
        
    return redirect('accounts:funcionario_list')