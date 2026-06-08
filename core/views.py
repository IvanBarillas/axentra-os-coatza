# core/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from apps.shared.manifest_registry import AxentraOSRegistry

@login_required
def launcher_home_view(request):
    """
    Renderiza el conmutador general de aplicaciones (index.html) de forma dinámica,
    hidratando únicamente las cards de las aplicaciones que el usuario tiene autorizadas.
    """
    profile = getattr(request.user, 'axentra_profile', None)
    
    if profile:
        is_root = profile.is_root_admin
        # Extraemos los identificadores de texto de sus apps asignadas (ej: ['accounts', 'organigrama'])
        allowed_apps_identifiers = [app.identifier for app in profile.allowed_apps.all()]
    else:
        is_root = False
        allowed_apps_identifiers = []

    # El motor dinámico genera las tarjetas leyendo los manifiestos locales
    launcher_cards = AxentraOSRegistry.get_launcher_cards(
        allowed_app_identifiers=allowed_apps_identifiers,
        is_root=is_root
    )

    return render(request, "index.html", {"launcher_cards": launcher_cards})