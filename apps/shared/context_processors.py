# apps/shared/context_processors.py
import logging
import traceback
from django.utils import timezone

# Conectamos con el Singleton y los perfiles dinámicos de security
from apps.security.models import TenantConfig, UserAppRole
from apps.shared.apps_config import AppIdentifier

logger = logging.getLogger(__name__)

def global_tenant_settings(request):
    """
    Inyecta los activos de marca e identidad legal del Ayuntamiento 
    a absolutamente todos los HTML del ecosistema web.
    """
    config = TenantConfig.objects.first()
    if not config:
        # Inicializador seguro de contingencia (Pattern Singleton Blinder)
        config = TenantConfig.objects.create(
            app_name='Axentra OS',
            entidad_nombre='H. Ayuntamiento de Coatzacoalcos',
            siglas='COATZA'
        )
    return {'tenant': config}


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
    
    # 🪐 CAPA ADMINISTRADORA DE CONTINGENCIA (BYPASS)
    if is_manager or is_root or request.user.is_superuser:
        slugs_totales = [choice[0] for choice in AppIdentifier.get_choices()]
        
        print("\n👑 " + "="*76)
        print(f"🛰️  [FUNC: user_module_permissions] -> BYPASS DE NIVEL MAESTRO DETECTADO")
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
    print(f"🛰️  [FUNC: user_module_permissions] -> RADAR PERIMETRAL DE LAUNCHER")
    print(f"⏰ Telemetría:       {ahora}")
    print(f"👤 Operador Activo:  {request.user.email}")
    print(f"📍 URL Impactada:    {request.path}")
    print(f"🗂️  Registros en BD:  {len(roles_activos)} celdas de rol localizadas.")
    
    if roles_activos.exists():
        print("-" * 80)
        print("📋 ANÁLISIS DE EXTRACCIÓN DE LLAVES DE MEMORIA (JSONFIELD):")
        for idx, r in enumerate(roles_activos, start=1):
            print(f"   {idx}. [App Slug: '{r.app.slug}']")
            # 🟢 CORRECCIÓN: Usamos '.role' que es el campo real del modelo unificado
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
    Consume el menú lateral dinámico precalculado por el decorador en RAM.
    Actúa como fallback inteligente si la vista actual no cuenta con compuerta perimetral.
    """
    if hasattr(request, 'axentra_sidebar_menu'):
        return {'menu_actual': request.axentra_sidebar_menu}

    context = {'menu_actual': []}
    ahora = timezone.now().strftime('%Y-%m-%d %H:%M:%S')

    if not request.user.is_authenticated or not request.resolver_match:
        return context

    url_app_name = request.resolver_match.app_name
    view_name = request.resolver_match.view_name

    if not url_app_name or url_app_name == 'security':
        return context

    # ============================================================================
    # 🛰️ CONSOLA DE AUDITORÍA DE FRONTEND - FALLBACK LAYER
    # ============================================================================
    print("\n🔮 " + "="*76)
    print(f"🖥️  [FUNC: menu_dinamico_processor] -> SIDEBAR FALLBACK LAYER EN ACCIÓN")
    print(f"⏰ Telemetría:        {ahora}")
    print(f"📍 URL Solicitada:    {request.path}")
    print(f"🎬 Vista Destino:     {view_name}")
    print(f"📦 Módulo URL (Slug): {url_app_name}")
    print(f"ℹ️  Detalle Técnico:   Bypass activo. Consumido fuera de compuerta perimetral dura.")
    print("-" * 80)
    print("📋 RASTREO SIMPLIFICADO DE PILA DE RENDERIZADO (BACKTRACE):")
    for line in traceback.format_stack()[-4:-1]:
        print(f"   {line.strip()}")
    print("="*80 + "\n")
    # ============================================================================

    return context