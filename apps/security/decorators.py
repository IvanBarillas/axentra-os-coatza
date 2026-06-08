# apps/security/decorators.py
from functools import wraps
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from apps.shared.manifest_registry import AxentraOSRegistry

def axentra_module_gate(module_identifier: str):
    """
    El Guardián Funcional Autónomo de Axentra OS.
    Reemplaza a ModulePermissionsMixin y ModuleAccessRequiredMixin para FBVs.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # 1. Recuperar el perfil del usuario autenticado
            profile = getattr(request.user, 'axentra_profile', None)
            if not profile:
                return redirect('admin:login') # Fallback de seguridad

            is_root = profile.is_root_admin

            # 2. Control de Acceso Perimetral (¿Puede dar clic a la App?)
            allowed_apps_slugs = [app.identifier for app in profile.allowed_apps.all()]
            if not is_root and module_identifier not in allowed_apps_slugs:
                if request.headers.get('HX-Request'):
                    return HttpResponseForbidden("Cambio de contexto o aplicación no autorizada.")
                return redirect('launcher_home')

            # 3. Hidratación Dinámica del Diccionario de Permisos Locales
            user_permissions_list = profile.permissions_matrix.get(module_identifier, [])
            
            # Construimos el mapa de permisos del request para evaluar en Python o en Templates
            request.axentra_permissions = {perm: True for perm in user_permissions_list}
            request.axentra_is_root = is_root

            # 4. Composición del Sidebar Dinámico Basado en Manifiesto
            # Buscamos el manifiesto de la aplicación activa actual
            all_manifests = AxentraOSRegistry.get_all_manifests()
            active_manifest = all_manifests.get(module_identifier)
            
            computed_sidebar = []
            if active_manifest and hasattr(active_manifest, 'SIDEBAR_MENU'):
                for item in active_manifest.SIDEBAR_MENU:
                    icon, name_visual, url_name, order, required_perm = item
                    
                    # El enlace pasa al sidebar si el usuario tiene el permiso o es Root
                    if is_root or request.axentra_permissions.get(required_perm, False):
                        computed_sidebar.append({
                            "icon": icon,
                            "name": name_visual,
                            "url": url_name,
                            "order": order
                        })
                # Ordenamos el menú según la prioridad declarada en el manifiesto
                computed_sidebar.sort(key=lambda x: x['order'])

            # Inyectamos el menú calculado en la request para que los partials lo pinten solo
            request.axentra_sidebar_menu = computed_sidebar
            request.axentra_active_module = module_identifier

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator