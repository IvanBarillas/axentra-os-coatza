# apps/shared/context_processors.py
import logging
import traceback
from django.conf import settings

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
    Inyecta de forma global las aplicaciones autorizadas para armar
    dinámicamente las tarjetas (Cards) del Launcher principal (Index Matrix).
    """
    if not request.user.is_authenticated:
        return {'allowed_modules': [], 'is_global_admin': False}
        
    is_manager = getattr(request.user, 'is_manager', False)
    profile = getattr(request.user, 'axentra_profile', None)
    is_root = getattr(profile, 'is_root_admin', False) or is_manager
    
    # Si es Superusuario o Manager Supremo, goza de bypass y ve todo el ecosistema
    if is_root or request.user.is_superuser:
        slugs_totales = [choice[0] for choice in AppIdentifier.get_choices()]
        return {
            'is_global_admin': True, 
            'allowed_modules': slugs_totales
        }

    # Flujo Ordinario: Consultamos las celdas activas en la tabla de ciberseguridad
    allowed_slugs = UserAppRole.objects.filter(
        user=request.user,
        is_active=True,
        app__is_active=True
    ).values_list('app__slug', flat=True)

    return {
        'is_global_admin': False,
        'allowed_modules': list(allowed_slugs)
    }


def menu_dinamico_processor(request):
    """
    Consume el menú lateral dinámico precalculado por el decorador en RAM.
    Actúa como fallback inteligente si la vista actual no cuenta con compuerta perimetral.
    """
    # Si el decorador ya calculó y sembró el sidebar dinámico en la request, lo pasamos directo
    if hasattr(request, 'axentra_sidebar_menu'):
        return {'menu_actual': request.axentra_sidebar_menu}

    context = {'menu_actual': []}

    if not request.user.is_authenticated or not request.resolver_match:
        return context

    url_app_name = request.resolver_match.app_name
    view_name = request.resolver_match.view_name

    if not url_app_name or url_app_name == 'security':
        # Evitamos loops redundantes o introspecciones en rutas desnudas del Core
        return context

    # ============================================================================
    # 🛰️ CONSOLA DE AUDITORÍA DE FRONTEND - AXENTRA OS (FALLBACK COMPONENT)
    # ============================================================================
    print("\n🔮 " + "="*76)
    print("🖥️  INSPECTOR DE SIDEBAR (FALLBACK LAYER - SHARED PROCESSOR)")
    print(f"📍 URL Solicitada:    {request.path}")
    print(f"🎬 Vista Destino:     {view_name}")
    print(f"📦 Módulo URL (Slug): {url_app_name}")
    print(f"ℹ️  Detalle Técnico:   Consumido de forma directa o mitigado sin decorador duro.")
    print("-" * 80)
    print("📋 RASTREO SIMPLIFICADO DE PILA DE RENDERIZADO (BACKTRACE):")
    for line in traceback.format_stack()[-4:-1]:
        print(f"   {line.strip()}")
    print("="*80 + "\n")
    # ============================================================================

    return context