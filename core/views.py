# core/views.py (O apps/security/views/dashboard_views.py según tu estructura)
from django.shortcuts import render, redirect
from apps.security.models import UserAppRole
from apps.shared.apps_config import AppIdentifier
from apps.shared.manifest_registry import AxentraOSRegistry

def launcher_home_view(request):
    """
    Renderiza el conmutador general de aplicaciones (index.html) de forma dinámica,
    hidratando únicamente las cards de las aplicaciones autorizadas en la tabla UserAppRole.
    Separa de forma atómica los módulos en bloques Core y Satélites.
    """
    # Protección perimetral básica: Si no ha iniciado sesión, directo a la compuerta externa
    if not request.user.is_authenticated:
        return redirect('intro_portal')

    # 1. Inicializadores de contingencia
    allowed_apps_identifiers = []
    is_manager = getattr(request.user, 'is_manager', False)
    profile = getattr(request.user, 'axentra_profile', None)
    is_root = getattr(profile, 'is_root_admin', False) or is_manager or request.user.is_superuser

    if is_root:
        # Si es administrador Root, le abrimos la compuerta para ver absolutamente todo el ecosistema
        allowed_apps_identifiers = [choice[0] for choice in AppIdentifier.get_choices()]
    else:
        # 📡 FLUJO MAESTRO: Extraemos los identificadores de texto de la tabla relacional de roles activos
        allowed_apps_identifiers = list(
            UserAppRole.objects.filter(
                user=request.user,
                is_active=True,
                app__is_active=True
            ).values_list('app__slug', flat=True)
        )

    # 2. El motor dinámico genera las tarjetas segmentadas en un diccionario {'core_apps': [], 'satellite_apps': []}
    launcher_data = AxentraOSRegistry.get_launcher_cards(
        allowed_app_identifiers=allowed_apps_identifiers,
        is_root=is_root
    )

    # ============================================================================
    # 🛰️ BITÁCORA DE INTROSPECCIÓN EN VIVO (MESA DE TELEMETRÍA PURIFICADA)
    # ============================================================================
    print("\n🔮 " + "═"*76)
    print("🖥️  INSPECTOR DE RENDERIZADO DEL LAUNCHER VIEWER (SEGMENTADO)")
    print(f"👤 Servidor Público: {request.user.email}")
    print(f"👑 ¿Es Root/Bypass?:  {is_root}")
    print(f"🎯 Slugs Extraídos de UserAppRole: {allowed_apps_identifiers}")
    print(f"🏛️  Módulos Core Hidratados: {len(launcher_data.get('core_apps', []))}")
    print(f"🛰️  Módulos Satélites Hidratados: {len(launcher_data.get('satellite_apps', []))}")
    print("═"*80 + "\n")
    # ============================================================================

    # 🟢 ENVIAMOS EL CONTEXTO: Pasamos launcher_data que contiene las dos listas internas
    return render(request, "index.html", {"launcher_data": launcher_data})


def intro_portal_view(request):
    """
    Renderiza la compuerta externa de bienvenida (Landing Portal) de Axentra OS,
    desplegando los marcos normativos de control interno y los disparadores de sesión.
    """
    # Si ya está autenticado, lo redirigimos directo al selector de apps para evitar doble login
    if request.user.is_authenticated:
        return redirect('launcher_home')
        
    # El singleton del tenant lo inyecta de forma automática tu context processor
    return render(request, "intro.html")