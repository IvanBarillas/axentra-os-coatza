# apps/security/decorators.py
from functools import wraps
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.contrib import messages
from apps.shared.manifest_registry import AxentraOSRegistry
from apps.security.services.permission_loader import get_user_permissions_for_app

def axentra_module_gate(module_identifier: str, required_fine_permission: str = None):
    """
    El Guardián Funcional Autónomo de Axentra OS.
    Reemplaza por completo a los antiguos mixins para Vistas Basadas en Funciones.
    1. Ejecuta control perimetral (Bypass para is_manager / root).
    2. Realiza hidración dinámica de llaves finas mediante el Radar en Caliente.
    3. Construye el SIDEBAR_MENU en RAM leyendo el manifiesto declarativo de la app.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # 1. Recuperar el perfil del usuario autenticado o rebotar
            if not request.user.is_authenticated:
                return redirect('admin:login')

            profile = getattr(request.user, 'axentra_profile', None)
            is_root = getattr(profile, 'is_root_admin', False) or getattr(request.user, 'is_manager', False)

            # 2. RADAR EN CALIENTE: Carga y mapea las banderas booleanas de la base de datos
            # Invocamos tu servicio nativo que arroja la telemetría exacta en consola
            permisos = get_user_permissions_for_app(request.user, module_identifier)

            # 3. COMPUERTA 1: Control de Acceso Perimetral (¿Tiene permitido el módulo?)
            if not permisos.get('has_access_module') and not is_root:
                if request.headers.get('HX-Request'):
                    return HttpResponseForbidden("Acceso Denegado: Aplicación satélite no autorizada.")
                messages.error(request, f"⚠️ Acceso Denegado al módulo [{module_identifier.upper()}].")
                return redirect('launcher_home')

            # 4. COMPUERTA 2: Validación de Llave Fina Crítica (Si la vista lo exige)
            if required_fine_permission and required_fine_permission not in permisos.get('permissions_list', []) and not is_root:
                if request.headers.get('HX-Request'):
                    return HttpResponseForbidden(f"Acceso Denegado: Requiere la llave [{required_fine_permission}].")
                messages.error(request, f"⚠️ Restricción de Seguridad: Requiere la credencial [{required_fine_permission}].")
                return redirect('launcher_home')

            # Sembramos las llaves calculadas en la request para consumo ciego de los Selectors y Vistas
            request.axentra_permissions = permisos
            request.axentra_is_root = is_root
            request.axentra_active_module = module_identifier

            # 5. COMPOSICIÓN DEL SIDEBAR DINÁMICO BASADO EN MANIFIESTO
            all_manifests = AxentraOSRegistry.get_all_manifests()
            active_manifest = all_manifests.get(module_identifier)
            
            computed_sidebar = []
            if active_manifest and hasattr(active_manifest, 'SIDEBAR_MENU'):
                for item in active_manifest.SIDEBAR_MENU:
                    icon, name_visual, url_name, order, required_perm = item
                    
                    # El enlace pasa a renderizarse si el funcionario tiene la llave o es Root
                    if is_root or permisos.get(required_perm, False):
                        computed_sidebar.append({
                            "icon": icon,
                            "name": name_visual,
                            "url": url_name,
                            "order": order
                        })
                computed_sidebar.sort(key=lambda x: x['order'])

            # Inyectamos el menú calculado para el partial templates/partials/_sidebar.html
            request.axentra_sidebar_menu = computed_sidebar

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


# =========================================================================
# 🛡️ ALIAS DE COMPATIBILIDAD GLOBAL (Mapeo de Símbolo Desconocido)
# =========================================================================
# Esto garantiza que si en algún controlador importas u ocupas 'axentra_gate_enforcer',
# Python resolverá el llamado apuntando de forma transparente al mismo motor de arriba.
axentra_gate_enforcer = axentra_module_gate