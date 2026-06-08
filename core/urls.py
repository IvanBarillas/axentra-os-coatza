# core/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from decouple import config

from core.views import intro_portal_view, launcher_home_view

ADMIN_PATH = config('ADMIN_SECRET_PATH', default='axentra-core-secret-portal-manager-wsl/')

urlpatterns = [
    # ──► 1. Panel de Administración Ofuscado
    path(ADMIN_PATH, admin.site.urls),

    # ──► 2. Compuerta Externa de Bienvenida (La raíz real de Axentra OS)
    path('', intro_portal_view, name='intro_portal'),

    # ──► 3. Selector Autónomo de Aplicaciones (El Launcher)
    path('launcher/', launcher_home_view, name='launcher_home'),

    # ==========================================================================
    # 📡 INTERCONEXIÓN DEL PAQUETE MODULAR DE RUTAS (UN SOLA APP EN DISCO)
    # ==========================================================================
    path('app/', include('apps.security.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)