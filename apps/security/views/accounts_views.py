# apps/security/views/accounts_views.py
import uuid
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.http import HttpResponse
from django.contrib.auth import get_user_model

from apps.shared.apps_config import AppIdentifier
from apps.security.decorators import axentra_gate_enforcer
from apps.security.models import User, UserProfile
from apps.security.models.organigrama import Dependencia, AreaOperativa, Sede
from apps.security.selectors.accounts_selectors import FuncionarioSelectors
from apps.security.services.accounts_services import FuncionarioService  # Ajustado a tu namespace
from apps.security.forms import (
    StaffUserCreationForm, StaffUserProfileForm, 
    StaffUserChangeForm, StaffUserProfileChangeForm, 
    AdminPasswordChangeForm
)

User = get_user_model()
logger = logging.getLogger(__name__)


# =========================================================================
# 👤 PILAR UNIQUE: GESTIÓN DE EXPEDIENTES Y SERVIDORES PÚBLICOS
# =========================================================================

@login_required
@axentra_gate_enforcer(AppIdentifier.ACCOUNTS, required_fine_permission="can_view_list")
def funcionario_list_view(request):
    """
    Despacha la nómina general filtrada mediante selectores optimizados.
    Soporta renderizado completo tradicional o parches atómicos en el DOM vía HTMX.
    """
    search_query = request.GET.get('q', '').strip()
    
    context = {
        'funcionarios': FuncionarioSelectors.listar_plantilla_activa(search_query=search_query),
        'sedes': Sede.objects.filter(is_active=True, is_deleted=False).order_by('nombre'),
        'dependencias': Dependencia.objects.filter(is_active=True, is_deleted=False).order_by('nombre'),
        'areas_operativas': AreaOperativa.objects.filter(is_active=True, is_deleted=False).order_by('nombre'),
        'current_q': search_query,
    }
    
    # 🎰 PROTOCOLO HYPER-REACTIVE HTMX LAYER:
    if request.headers.get('HX-Request') or request.headers.get('hx-request'):
        return render(request, 'accounts/htmx/funcionario_table_partial.html', context)
        
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
            
            exito, usuario, errores = FuncionarioService.crear_funcionario(
                post_data=payload, raw_password=form.cleaned_data.get('password')
            )

            if exito and usuario:
                messages.success(request, f"El funcionario {usuario.full_name} ha sido dado de alta con éxito.")
                return redirect('accounts:funcionario_list')  # Estandarizado a tu namespace real
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
    # 🟢 CORRECCIÓN: Buscamos el perfil usando la clave explícita para evitar colisión de accesores inversos
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
            
            exito, usuario, errores = FuncionarioService.editar_funcionario(pk, payload)
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
        'funcionario': usuario_instance  # 🟢 CORRECCIÓN: Pasamos el objeto directo para evitar llamadas a métodos inexistentes
    })


@login_required
@axentra_gate_enforcer(AppIdentifier.ACCOUNTS, required_fine_permission='can_change_password')
def funcionario_cambiar_password_view(request, pk: uuid.UUID):
    """Cifrado administrativo forzado de contraseñas y llaves operativas."""
    usuario_instance = get_object_or_404(User, id=pk)
    if request.method == 'POST':
        form = AdminPasswordChangeForm(request.POST)
        if form.is_valid():
            if FuncionarioService.forzar_reseteo_password(pk, form.cleaned_data['password']):
                messages.success(request, f"Credenciales restablecidas con éxito para {usuario_instance.full_name}.")
                return redirect('accounts:funcionario_list')
    else:
        form = AdminPasswordChangeForm()

    return render(request, 'accounts/forms/funcionario_password_form.html', {'form': form, 'funcionario': usuario_instance})


@require_POST
@login_required
@axentra_gate_enforcer(AppIdentifier.ACCOUNTS, required_fine_permission='can_delete_user')
def funcionario_soft_delete_view(request, pk: uuid.UUID):
    """Baja lógica forense (Soft-Delete) que congela los accesos perimetrales."""
    if str(pk) == str(request.user.id):
        messages.error(request, "Operación denegada: No puede aplicar una baja sobre su propia sesión.")
        return redirect('accounts:funcionario_list')

    exito, mensaje = FuncionarioService.tramitar_baja_institucional(pk, request.user.email)
    if exito:
        messages.warning(request, mensaje)
    else:
        messages.error(request, mensaje)
    return redirect('accounts:funcionario_list')