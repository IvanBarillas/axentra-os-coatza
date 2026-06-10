# apps/shared/context_processors.py
import logging
import traceback
from django.utils import timezone

# Conectamos con el Singleton, la matriz en BD y el Manifiesto Maestro de Gobernanza
from apps.security.models import TenantConfig, UserAppRole
from apps.security.permissions import SecurityPermissions
from apps.shared.apps_config import AppIdentifier
from apps.shared.manifest_registry import AxentraOSRegistry
from apps.security.services.permission_loader import get_user_permissions_for_app

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
                entidad_nombre='H. Ayuntamiento de Coatzacoalcos',
                siglas='COATZA'
            )
        return {'tenant': config}
    except Exception as e:
        logger.error(f"Error en global_tenant_settings: {e}")
        return {'tenant': None}


def user_module_permissions(request):
    """
    Calcula, inyecta y audita en consola las aplicaciones autorizadas 
    del funcionario para alimentar las tarjetas dinámicas del Launcher.
    """
    context = {'allowed_modules': [], 'is_global_admin': False}
    ahora = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
    
    if not request.user.is_authenticated:
        return context
        
    is_manager = getattr(request.user, 'is_manager', False)
    profile = getattr(request.user, 'axentra_profile', None)
    is_root = getattr(profile, 'is_root_admin', False) if profile else False
    
    # 👑 CAPA ADMINISTRADORA DE CONTINGENCIA (BYPASS SUPREMO)
    if is_manager or is_root or request.user.is_superuser:
        slugs_totales = [choice[0] for choice in AppIdentifier.get_choices()]
        
        print("\n👑 " + "="*76)
        print(f"🛰️   [FUNC: user_module_permissions] -> BYPASS DE NIVEL MAESTRO DETECTADO")
        print(f"⏰ Telemetría:  {ahora}")
        print(f"📧 Funcionario: {request.user.email}")
        print(f"🔑 Privilegios: SUPERUSER={request.user.is_superuser} | MANAGER={is_manager} | ROOT_ADMIN={is_root}")
        print(f"📦 Módulos Forzados de Forma Global: {slugs_totales}")
        print("="*80 + "\n")
        
        return {
            'is_global_admin': True, 
            'allowed_modules': slugs_totales
        }

    # 📡 FLUJO ORDINARIO: CONSULTA DE MATRIZ DE PERMISOS EN POSTGRES
    roles_activos = UserAppRole.objects.filter(
        user=request.user,
        is_active=True,
        app__is_active=True
    ).select_related('app')
    
    allowed_slugs = [role.app.slug for role in roles_activos]

    # ============================================================================
    # 📊 AUDITORÍA DE TRANSMISIÓN DE CONTEXTO (EL HACK DEL RADAR)
    # ============================================================================
    print("\n🔍 " + "═"*76)
    print(f"🛰️   [FUNC: user_module_permissions] -> RADAR PERIMETRAL DE LAUNCHER")
    print(f"⏰ Telemetría:       {ahora}")
    print(f"👤 Operador Activo:  {request.user.email}")
    print(f"📍 URL Impactada:    {request.path}")
    print(f"🗂️  Registros en BD:  {len(roles_activos)} celdas de rol localizadas.")
    
    if roles_activos.exists():
        print("-" * 80)
        print("📋 ANÁLISIS DE EXTRACCIÓN DE LLAVES DE MEMORIA (JSONFIELD):")
        for idx, r in enumerate(roles_activos, start=1):
            print(f"   {idx}. [App Slug: '{r.app.slug}']")
            print(f"      🔹 Rol Asignado: '{r.role}'")
            print(f"      🔹 Llaves JSON:  {r.permissions_list}")
    else:
        print("   ⚠️ ADVERTENCIA SEGURIDAD: La consulta devolvió 0 aplicativos para este ID.")
        
    print(f"🚀 Slugs despachados al DOM (allowed_modules): {allowed_slugs}")
    print("═"*80 + "\n")
    # ============================================================================

    return {
        'is_global_admin': False,
        'allowed_modules': allowed_slugs
    }


def menu_dinamico_processor(request):
    """
    🧠 PROCESADOR DE ENTORNO CONTEXTUAL (HYPER-REACTIVE SIDEBAR)
    Sincroniza y expone las variables calculadas por el decorador hacia el motor del DOM.
    Conserva la mesa de telemetría e inspección en consola activa.
    """
    context = {'menu_actual': [], 'modulo_actual': 'launcher', 'sidebar_menu': []}
    ahora = timezone.now().strftime('%Y-%m-%d %H:%M:%S')

    if not request.user.is_authenticated or not request.resolver_match:
        return context

    modulo_activo = request.resolver_match.namespace
    if not modulo_activo:
        return context

    # 🟢 OPTIMIZACIÓN CON TELEMETRÍA (BYPASS DE MEMORIA DE ALTO RENDIMIENTO):
    if hasattr(request, 'axentra_sidebar_menu'):
        context['menu_actual'] = request.axentra_sidebar_menu
        context['sidebar_menu'] = request.axentra_sidebar_menu
        context['modulo_actual'] = modulo_activo

        # =========================================================================
        # 🔮 DEBUGGER: LOGS DE VELOCIDAD CERO DE LA RAM
        # =========================================================================
        print("\n🖥️  " + "═"*76)
        print(f"🛸  [PROCESSOR BYPASS] -> MAESTRO DE NAVEGACIÓN DESACOPLADO (RAM LAYER)")
        print(f"⏰ Telemetría:       {ahora}")
        print(f"📍 Módulo Namespace: {modulo_activo.upper()}")
        print(f"🎬 Enlaces Extraídos de la RAM: {len(context['menu_actual'])} enlaces resueltos.")
        print("⚡ Rendimiento: Consulta duplicada mitigada a velocidad cero (0 ms).")
        print("═"*80 + "\n")
        # =========================================================================
        return context

    # 🛰️ FALLBACK DE SEGURIDAD (Si ingresan a una ruta que no lleva decorador)
    manifesto_modulo = AxentraOSRegistry.get_manifest_by_slug(modulo_activo)
    if not manifesto_modulo or not hasattr(manifesto_modulo, 'SIDEBAR_MENU'):
        context['modulo_actual'] = modulo_activo
        return context

    menu_maestro_crudo = manifesto_modulo.SIDEBAR_MENU
    es_root = request.user.is_superuser or getattr(request.user, 'is_manager', False) or getattr(getattr(request.user, 'axentra_profile', None), 'is_root_admin', False)
    menu_filtrado = []
    
    if es_root:
        for icono, nombre, url_name, orden, permiso_req in menu_maestro_crudo:
            menu_filtrado.append({
                'icon': icono, 'name': nombre, 'url': url_name, 'order': orden
            })
    else:
        # Invocamos el Radar en Caliente
        permisos = get_user_permissions_for_app(request.user, modulo_activo)
        lista_llaves_reales = permisos.get('permissions_list', [])

        for icono, nombre, url_name, orden, permiso_req in menu_maestro_crudo:
            llave_compuesta = f"{modulo_activo}__{permiso_req}"
            if permisos.get(permiso_req, False) or permisos.get(llave_compuesta, False) or permiso_req in lista_llaves_reales or llave_compuesta in lista_llaves_reales:
                menu_filtrado.append({
                    'icon': icono, 'name': nombre, 'url': url_name, 'order': orden
                })

    menu_filtrado.sort(key=lambda x: x['order'])
    
    # =========================================================================
    # 🔮 DEBUGGER: LOGS DE INSERCIÓN DIRECTA DESDE EL ENGINE FALLBACK
    # =========================================================================
    print("\n🖥️  " + "═"*76)
    print(f"🛸  [PROCESSOR FALLBACK] -> MAESTRO DE NAVEGACIÓN DESACOPLADO (ORM LAYER)")
    print(f"⏰ Telemetría:       {ahora}")
    print(f"📍 Módulo Namespace: {modulo_activo.upper()}")
    print(f"🎬 Enlaces Visibles: {len(menu_filtrado)} de {len(menu_maestro_crudo)} evaluados.")
    print("═"*80 + "\n")
    # =========================================================================

    context['menu_actual'] = menu_filtrado
    context['sidebar_menu'] = menu_filtrado
    context['modulo_actual'] = modulo_activo
    return context