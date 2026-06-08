# apps/shared/context_processors.py
import logging
import traceback
from django.utils import timezone

# Conectamos con el Singleton, la matriz en BD y el Manifiesto Maestro de Gobernanza
from apps.security.models import TenantConfig, UserAppRole
from apps.security.permissions import SecurityPermissions
from apps.shared.apps_config import AppIdentifier

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
    Determina de forma automática el sub-módulo en el que navega el operador,
    extrae el sub-menú del Manifiesto de Gobernanza Desacoplado y filtra las opciones
    en caliente comparándolas contra las llaves JSON de la base de datos.
    """
    context = {'menu_actual': [], 'modulo_actual': 'launcher'}
    ahora = timezone.now().strftime('%Y-%m-%d %H:%M:%S')

    if not request.user.is_authenticated or not request.resolver_match:
        return context

    modulo_activo = request.resolver_match.namespace
    
    if not modulo_activo:
        return context

    # 🟢 CORRECCIÓN MÁXIMA: Invocamos al Registry para traer el manifiesto desacoplado del módulo activo
    from apps.shared.manifest_registry import AxentraOSRegistry
    manifiesto_modulo = AxentraOSRegistry.get_manifest_by_slug(modulo_activo)
    
    if not manifiesto_modulo or not hasattr(manifiesto_modulo, 'SIDEBAR_MENU'):
        return context

    menu_maestro_crudo = manifiesto_modulo.SIDEBAR_MENU
    es_root = request.user.is_superuser or getattr(request.user, 'is_manager', False)
    menu_filtrado = []
    
    if es_root:
        for icono, nombre, url_name, orden, permiso_req in menu_maestro_crudo:
            menu_filtrado.append({
                'icon': icono,
                'name': nombre,
                'url': url_name,
                'order': orden
            })
    else:
        try:
            rol_modulo = UserAppRole.objects.get(
                user=request.user,
                app__slug=modulo_activo,
                is_active=True,
                app__is_active=True
            )
            llaves_usuario = rol_modulo.permissions_list
        except UserAppRole.DoesNotExist:
            llaves_usuario = []

        for icono, nombre, url_name, orden, permiso_req in menu_maestro_crudo:
            if permiso_req in llaves_usuario:
                menu_filtrado.append({
                    'icon': icono,
                    'name': nombre,
                    'url': url_name,
                    'order': orden
                })

    menu_filtrado.sort(key=lambda x: x['order'])

    print("\n🖥️  " + "═"*76)
    print(f"🛸  [FUNC: menu_dinamico_processor] -> MAESTRO DE NAVEGACIÓN DESACOPLADO")
    print(f"⏰ Telemetría:       {ahora}")
    print(f"📍 Módulo Namespace: {modulo_activo.upper()}")
    print(f"🎬 Enlaces Visibles: {len(menu_filtrado)} de {len(menu_maestro_crudo)} configurados.")
    print("═"*80 + "\n")

    return {
        'menu_actual': menu_filtrado,
        'modulo_actual': modulo_activo
    }