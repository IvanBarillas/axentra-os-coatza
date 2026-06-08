# apps/security/views/matrix_views.py
import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from apps.shared.apps_config import AppIdentifier
from apps.security.decorators import axentra_gate_enforcer
from apps.security.models import AppModule, User
from apps.security.selectors import PermissionSelectors
from apps.security.services import PermissionService

# Escalafón Universal Inmutable (Regla de Oro de tu bitácora)
ROLE_WEIGHTS = {'owner': 100, 'admin': 80, 'editor': 60, 'reviewer': 40, 'viewer': 20}

@login_required
@axentra_gate_enforcer(AppIdentifier.SECURITY, required_fine_permission='can_assign_roles')
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
                rol_operador_str = request.axentra_permissions.get('role', 'viewer')
                rol_destino_str = target_user.app_roles.filter(app=app_module, is_active=True).values_list('role', flat=True).first() or 'viewer'
                
                if ROLE_WEIGHTS.get(rol_destino_str, 0) >= ROLE_WEIGHTS.get(rol_operador_str, 0) or ROLE_WEIGHTS.get(nuevo_rol_base, 0) >= ROLE_WEIGHTS.get(rol_operador_str, 0):
                    messages.error(request, "🚫 Violación de Escalafón: Tus privilegios locales no tienen el peso jerárquico para alterar este rango.")
                    return redirect(f"{request.path}?app_slug={app_slug}&user_id={user_id}")

            if PermissionService.save_matrix_permissions(target_user, app_module, nuevo_rol_base, llaves_encendidas):
                messages.success(request, f"🔒 Matriz de configuración modificada para {target_user.email}.")
            return redirect(f"{request.path}?app_slug={app_slug}&user_id={user_id}")

        # 🛡️ OPERACIÓN CRÍTICA 2: SEMBRAR/INYECTAR FUNCIONARIO NUEVO A LA APP
        elif action == "authorize_entry" and request.user.axentra_profile.is_root_admin:
            nuevo_usuario_id = request.POST.get('new_user_id')
            rol_a_inyectar = request.POST.get('initial_role', 'viewer').lower().strip()
            target_user = get_object_or_404(User, id=nuevo_usuario_id)

            if PermissionService.authorize_new_user_entry(app_module, str(target_user.id)):
                messages.success(request, "🟢 Funcionario incorporado al módulo con éxito.")
            return redirect(f"{request.path}?app_slug={app_slug}&user_id={target_user.id}")

    # Método GET ordinario: Resolvemos la matriz en memoria RAM desde el Selector
    context = PermissionSelectors.get_secured_matrix_data(app_module, user_focus_id=user_focus_id, request_user=request.user)
    context['app'] = app_module
    context['modulo_actual'] = app_slug
    return render(request, 'security/matrix_dynamic.html', context)