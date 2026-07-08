# core/views.py (O apps/security/views/dashboard_views.py según tu estructura)
from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model

from apps.security.models import UserAppRole
from apps.shared.apps_config import AppIdentifier
from apps.shared.manifest_registry import AxentraOSRegistry
from apps.shared.utils.telemetry import AxentraRadar

User = get_user_model()

def index_hub_view(request):
    """
    AXENTRA OS - NODO CENTRAL DE BIENVENIDA (INDEX HUB)

    Punto de aterrizaje perimetral post-autenticación.
    No pertenece a un módulo operativo específico.
    No usa sidebar secundario.
    """
    if not request.user.is_authenticated:
        return redirect('accounts:login')

    is_manager = getattr(request.user, 'is_manager', False)
    profile = getattr(request.user, 'axentra_profile', None)

    is_root = (
        getattr(profile, 'is_root_admin', False)
        or is_manager
        or request.user.is_superuser
    )

    AxentraRadar.imprimir_auditoria(
        componente="index_hub_view",
        request=request,
        titulo="Acceso a Nodo Central de Bienvenida",
        icono="🏛️",
        extra_data={
            "Jurisdicción": "MASTER_BYPASS" if is_root else "OPERADOR_ESTÁNDAR",
            "Identidad": request.user.email,
        },
    )

    return render(
        request,
        "index_hub.html",
        {
            "is_root": is_root,
            "show_module_sidebar": False,
            "modulo_actual": "launcher",
        },
    )

def intro_portal_view(request):
    """
    Renderiza la compuerta externa de bienvenida (Landing Portal) de Axentra OS.
    """
    # Si el operador ya tiene una sesión activa en el navegador,
    # lo saltamos de forma automática al launcher interno.
    if request.user.is_authenticated:
        return redirect('index_hub')
        
    return render(request, "index.html")