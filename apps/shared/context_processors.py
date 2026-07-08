# apps/shared/context_processors.py
import logging
from django.utils import timezone

# Conectamos con el Singleton, la matriz en BD y el Manifiesto Maestro de Gobernanza
from apps.security.models import TenantConfig, UserAppRole
from apps.security.permissions import SecurityPermissions
from apps.shared.apps_config import AppIdentifier
from apps.shared.manifest_registry import AxentraOSRegistry
from apps.security.services.permission_loader import get_user_permissions_for_app
from apps.shared.utils.telemetry import AxentraRadar  

logger = logging.getLogger(__name__)

def global_tenant_settings(request):
    """
    Inyecta los activos de marca e identidad legal del Ayuntamiento 
    a absolutamente todos los HTML del ecosistema web.
    """
    try:
        config = TenantConfig.objects.first()
        if not config:
            # Inicializador seguro de contingencia (Pattern Singleton Blinder)
            config = TenantConfig.objects.create(
                app_name='Axentra OS',
                entidad_nombre='Axentra Infraestructure',
                siglas='AXN'
            )
        return {'tenant': config}
    except Exception as e:
        logger.error(f"Error en global_tenant_settings: {e}")
        return {'tenant': None}


def user_module_permissions(request):
    """
    Calcula, inyecta y audita las aplicaciones autorizadas 
    del funcionario para alimentar las tarjetas dinámicas del Launcher.
    """
    context = {'allowed_modules': [], 'is_global_admin': False}
    
    if not request.user.is_authenticated:
        return context
        
    is_manager = getattr(request.user, 'is_manager', False)
    profile = getattr(request.user, 'axentra_profile', None)
    is_root = getattr(profile, 'is_root_admin', False) if profile else False
    
    # 👑 COMPUERTA A: CAPA ADMINISTRADORA DE CONTINGENCIA (BYPASS SUPREMO)
    if is_manager or is_root or request.user.is_superuser:
        slugs_totales = [choice[0] for choice in AppIdentifier.get_choices()]
        
        # ✨ TELEMETRÍA EN 1 LÍNEA: Bypass de nivel supremo administrado
        AxentraRadar.imprimir_auditoria(
            componente="user_module_permissions",
            request=request,
            titulo="Bypass de Nivel Maestro Detectado",
            icono="👑",
            extra_data={
                "Estado Privilegios": f"SUPERUSER={request.user.is_superuser} | MANAGER={is_manager} | ROOT_ADMIN={is_root}",
                "Módulos Forzados Globales": slugs_totales
            }
        )
        
        return {
            'is_global_admin': True, 
            'allowed_modules': slugs_totales
        }

    # 📡 COMPUERTA B: FLUJO ORDINARIO (CONSULTA DE MATRIZ DE PERMISOS EN POSTGRES)
    roles_activos = UserAppRole.objects.filter(
        user=request.user,
        is_active=True,
        app__is_active=True
    ).select_related('app')
    
    allowed_slugs = [role.app.slug for role in roles_activos]

    # ✨ TELEMETRÍA EN 1 LÍNEA: Análisis de extracción y lectura JSONField
    AxentraRadar.imprimir_auditoria(
        componente="user_module_permissions",
        request=request,
        titulo="Radar Perimetral de Launcher",
        icono="🔍",
        extra_data={
            "Celdas Localizadas en BD": len(roles_activos),
            "Slugs Despachados al DOM": allowed_slugs,
            "Análisis de Permisos": [f"App: '{r.app.slug}' | Rol: '{r.role}' | Llaves: {r.permissions_list}" for r in roles_activos] if roles_activos.exists() else "⚠️ ADVERTENCIA: 0 aplicativos para este ID."
        }
    )

    return {
        'is_global_admin': False,
        'allowed_modules': allowed_slugs
    }


def menu_dinamico_processor(request):
    """
    🧠 PROCESADOR DE ENTORNO CONTEXTUAL (HYPER-REACTIVE SIDEBAR)
    Sincroniza y expone las variables calculadas por el decorador hacia el motor del DOM.
    Determina automáticamente si se debe pintar el Sidebar 2 (sidebar_secundario).
    """
    # 1. Estado base por defecto: sin menú y sidebar secundario apagado (False)
    context = {
        'menu_actual': [], 
        'modulo_actual': 'launcher', 
        'sidebar_menu': [],
        'sidebar_secundario': False  
    }

    if not request.user.is_authenticated:
        return context

    # 📡 EXTRACTOR DE METADATOS DEL DECORATOR GATE
    modulo_activo = getattr(request, 'axentra_active_module', None)
    
    if not modulo_activo and request.resolver_match:
        modulo_activo = request.resolver_match.namespace

    if not modulo_activo or modulo_activo == 'launcher':
        return context

    context['modulo_actual'] = modulo_activo

    # 🟢 CASO A: DESACOPLADO DESDE RAM (EL DECORADOR YA FILTRÓ EL MENÚ)
    if hasattr(request, 'axentra_sidebar_menu'):
        menu_final = request.axentra_sidebar_menu
        context['menu_actual'] = menu_final
        context['sidebar_menu'] = menu_final
        
        # Si el menú calculado en RAM tiene items, encendemos el sidebar secundario
        context['sidebar_secundario'] = len(menu_final) > 0 # ◄── Cálculo automático
        return context

    # 🛰️ CASO B: FALLBACK LAYER (F5 o ingreso por URL limpia sin pasar por el decorador)
    manifesto_modulo = AxentraOSRegistry.get_manifest_by_slug(modulo_activo)
    if not manifesto_modulo or not hasattr(manifesto_modulo, 'SIDEBAR_MENU'):
        return context

    menu_maestro_crudo = manifesto_modulo.SIDEBAR_MENU
    es_root = (
        request.user.is_superuser or 
        getattr(request.user, 'is_manager', False) or 
        getattr(getattr(request.user, 'axentra_profile', None), 'is_root_admin', False)
    )
    menu_filtrado = []
    
    if es_root:
        for icono, nombre, url_name, orden, permiso_req in menu_maestro_crudo:
            menu_filtrado.append({
                'icon': icono, 'name': nombre, 'url': url_name, 'order': orden
            })
    else:
        permisos = get_user_permissions_for_app(request.user, modulo_activo)
        lista_llaves_reales = permisos.get('permissions_list', [])

        for icono, nombre, url_name, orden, permiso_req in menu_maestro_crudo:
            llave_compuesta = f"{modulo_activo}__{permiso_req}"
            if permisos.get(permiso_req, False) or permisos.get(llave_compuesta, False) or permiso_req in lista_llaves_reales or llave_compuesta in lista_llaves_reales:
                menu_filtrado.append({
                    'icon': icono, 'name': nombre, 'url': url_name, 'order': orden
                })

    menu_filtrado.sort(key=lambda x: x['order'])
    
    context['menu_actual'] = menu_filtrado
    context['sidebar_menu'] = menu_filtrado
    
    # Si el fallback reconstruyó un menú con elementos, activamos el sidebar secundario
    context['sidebar_secundario'] = len(menu_filtrado) > 0 # ◄── Cálculo automático
    return context