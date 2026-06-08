from django.shortcuts import render
from apps.security.models import UserAppRole
from apps.shared.apps_config import  AppIdentifier
from apps.shared.manifest_registry import  AxentraOSRegistry

def launcher_home_view(request):
    """
    Renderiza el conmutador general de aplicaciones (index.html) de forma dinámica,
    hidratando únicamente las cards de las aplicaciones autorizadas en la tabla UserAppRole.
    """
    # 1. Inicializadores de contingencia
    allowed_apps_identifiers = []
    is_root = False

    if request.user.is_authenticated:
        is_manager = getattr(request.user, 'is_manager', False)
        profile = getattr(request.user, 'axentra_profile', None)
        is_root = getattr(profile, 'is_root_admin', False) or is_manager or request.user.is_superuser

        if is_root:
            # Si es administrador Root, le abrimos la compuerta para ver absolutamente todo el ecosistema
            allowed_apps_identifiers = [choice[0] for choice in AppIdentifier.get_choices()]
        else:
            # 📡 FLUJO MAESTRO: Extraemos los identificadores de texto de la nueva tabla relacional de roles activos
            allowed_apps_identifiers = list(
                UserAppRole.objects.filter(
                    user=request.user,
                    is_active=True,
                    app__is_active=True
                ).values_list('app__slug', flat=True)
            )

    # ============================================================================
    # 🛰️ BITÁCORA DE INTROSPECCIÓN EN VIVO (MESA DE TELEMETRÍA)
    # ============================================================================
    print("\n🔮 " + "═"*76)
    print("🖥️  INSPECTOR DE RENDERIZADO DEL LAUNCHER VIEWER")
    print(f"👤 Servidor Público: {request.user.email}")
    print(f"👑 ¿Es Root/Bypass?:  {is_root}")
    print(f"🎯 Slugs Extraídos de UserAppRole: {allowed_apps_identifiers}")
    # ============================================================================

    # 2. El motor dinámico genera las tarjetas cruzando los identificadores contra los manifiestos locales
    launcher_cards = AxentraOSRegistry.get_launcher_cards(
        allowed_app_identifiers=allowed_apps_identifiers,
        is_root=is_root
    )

    print(f"📊 Cantidad de Cards Hidratadas por el Registry: {len(launcher_cards)}")
    print("═"*80 + "\n")

    return render(request, "index.html", {"launcher_cards": launcher_cards})


def intro_portal_view(request):
    """
    Renderiza la compuerta externa de bienvenida (Landing Portal) de Axentra OS,
    desplegando los marcos normativos de control interno y los disparadores de sesión.
    """
    # El singleton del tenant lo inyecta de forma automática tu context processor
    return render(request, "intro.html")