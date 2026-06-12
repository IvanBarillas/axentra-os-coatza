# core/views.py (O apps/security/views/dashboard_views.py según tu estructura)
from django.shortcuts import render, redirect
from apps.security.models import UserAppRole
from apps.shared.apps_config import AppIdentifier
from apps.shared.manifest_registry import AxentraOSRegistry
from apps.shared.utils.telemetry import AxentraRadar

def launcher_home_view(request):
    """
    Renderiza el conmutador general de aplicaciones (launcher_app.html) de forma dinámica,
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
    # 🔮 REFRACTORIZACIÓN INTEGRADA: LLAMADA AL DESPACHADOR DE TELEMETRÍA GLOBAL
    # ============================================================================
    AxentraRadar.imprimir_auditoria(
        componente="launcher_home_view",
        request=request,
        titulo="Inspector de Renderizado del Launcher Viewer",
        icono="🔮",
        extra_data={
            "¿Es Root/Bypass?": "SÍ (Acceso Total Abierto)" if is_root else "NO (Flujo Restringido por ORM)",
            "Slugs Extraídos (BD/Choices)": allowed_apps_identifiers,
            "Módulos Core Hidratados": len(launcher_data.get('core_apps', [])),
            "Módulos Satélites Hidratados": len(launcher_data.get('satellite_apps', []))
        }
    )
    # ============================================================================

    # 🟢 ENVIAMOS EL CONTEXTO: Pasamos launcher_data que contiene las dos listas internas
    return render(request, "launcher_app.html", {"launcher_data": launcher_data})


def intro_portal_view(request):
    """
    Renderiza la compuerta externa de bienvenida (Landing Portal) de Axentra OS.
    """
    # Si el operador ya tiene una sesión activa en el navegador,
    # lo saltamos de forma automática al launcher interno.
    if request.user.is_authenticated:
        return redirect('launcher_home')
        
    return render(request, "index.html")