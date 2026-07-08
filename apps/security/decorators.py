# apps/security/decorators.py
import sys
from functools import wraps
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.contrib import messages
from django.utils import timezone

from apps.shared.manifest_registry import AxentraOSRegistry
from apps.security.services.permission_loader import get_user_permissions_for_app
from apps.shared.utils.telemetry import AxentraRadar

def axentra_module_gate(module_identifier: str, required_fine_permission: str = None):
    """
    🚧 EL GUARDIÁN FUNCIONAL AUTÓNOMO DE AXENTRA OS:
    Intercepta las peticiones inyectando la telemetría del Radar en Caliente.
    Calcula, filtra e inyecta el SIDEBAR_MENU mandando los paquetes al despachador universal.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # 1. Compuerta de Autenticación Base
            if not request.user.is_authenticated:
                return redirect('accounts:login')

            profile = getattr(request.user, 'axentra_profile', None)
            is_root = getattr(profile, 'is_root_admin', False) or getattr(request.user, 'is_manager', False) or request.user.is_superuser

            # 2. RADAR EN CALIENTE: Forzamos la carga sin importar el ROL para auditoría profunda
            permisos = get_user_permissions_for_app(request.user, module_identifier)
            lista_llaves_reales = permisos.get('permissions_list', [])

            # =========================================================================
            # 🛡️ SANEADO EXCLUSIVO: COMPUERTA 1 - CONTROL DE ACCESO PERIMETRAL UNIFICADO
            # =========================================================================
            tiene_acceso_modulo = permisos.get('has_access_module', False)
            
            if not tiene_acceso_modulo and not is_root:
                if request.headers.get('HX-Request'):
                    return HttpResponseForbidden("Acceso Denegado: Módulo satélite no autorizado en matriz JSON.")
                messages.error(request, f"⚠️ Acceso Denegado al módulo [{module_identifier.upper()}].")
                return redirect('index_hub')

            # 4. COMPUERTA 2: Validación de Credencial Fina (Si la vista exige un token específico)
            if required_fine_permission and not is_root:
                llave_compuesta_req = f"{module_identifier}__{required_fine_permission}"
                if required_fine_permission not in lista_llaves_reales and llave_compuesta_req not in lista_llaves_reales and not permisos.get(required_fine_permission, False) and not permisos.get(llave_compuesta_req, False):
                    if request.headers.get('HX-Request'):
                        return HttpResponseForbidden(f"Acceso Denegado: Requiere la credencial [{required_fine_permission}].")
                    messages.error(request, f"⚠️ Restricción perimetral: Requiere el token [{required_fine_permission}].")
                    return redirect('index_hub')

            # Sembrado atómico en el Request para consumo de controladores y vistas de plantillas secundarias
            request.axentra_permissions = permisos
            request.axentra_permissions_list = lista_llaves_reales
            request.axentra_is_root = is_root
            request.axentra_active_module = module_identifier

            # 5. COMPOSICIÓN REFLECTIVA DEL SIDEBAR_MENU
            all_manifests = AxentraOSRegistry.get_all_manifests()
            active_manifest = all_manifests.get(module_identifier)
            
            computed_sidebar = []
            if active_manifest and hasattr(active_manifest, 'SIDEBAR_MENU'):
                for item in active_manifest.SIDEBAR_MENU:
                    icon, name_visual, url_name, order, required_perm = item
                    
                    llave_item_compuesta = f"{module_identifier}__{required_perm}"
                    tiene_llave_permiso = permisos.get(required_perm, False) or permisos.get(llave_item_compuesta, False) or required_perm in lista_llaves_reales or llave_item_compuesta in lista_llaves_reales
                    
                    if is_root or tiene_llave_permiso:
                        computed_sidebar.append({
                            "icon": icon, "name": name_visual, "url": url_name, "order": order
                        })
                computed_sidebar.sort(key=lambda x: x['order'])

            # Sembramos el menú en la RAM del hilo actual para el context processor
            request.axentra_sidebar_menu = computed_sidebar

            # =========================================================================
            # 🔮 REFRACTORIZACIÓN INTEGRADA: LLAMADA AL DESPACHADOR DE TELEMETRÍA GLOBAL
            # =========================================================================
            try:
                llamado_desde = f"{view_func.__module__} -> {view_func.__name__}()"
            except Exception:
                llamado_desde = "Vista FBV Anónima"

            llaves_vivas = [k for k, v in permisos.items() if v is True and k not in ['has_access', 'has_access_module', 'llaves', 'permissions_list']]

            # Despachamos todos los metadatos al impresor universal controlado por settings.py
            AxentraRadar.imprimir_auditoria(
                componente="DECORATOR_GATE",
                request=request,
                titulo="Inspector de Aduana de Ruta",
                icono="🛡️",
                extra_data={
                    "Módulo Target": module_identifier.upper(),
                    "Despachando Vista": llamado_desde,
                    "Token Fino Exigido": required_fine_permission or 'NINGUNO (ACCESO LIBRE)',
                    "Enlaces al Sidebar": len(computed_sidebar),
                    "Rango Jerárquico": "👑 MASTER BYPASS ACTIVO" if is_root else "OPERADOR ESTÁNDAR",
                    "Pool Matriz JSON (BD)": llaves_vivas,
                    "Pool Token String (BD)": lista_llaves_reales if lista_llaves_reales else "Sin llaves físicas"
                }
            )
            # =========================================================================

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

# 👑 ALIAS DE EXPORTACIÓN MAESTRO: Mantiene compatibilidad total con tus views de herencia anteriores
axentra_gate_enforcer = axentra_module_gate