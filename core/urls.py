# core/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from decouple import config  # Importamos decouple para leer el .env seguro

#from core.api import api
from core.views import launcher_home_view

# ==========================================================================
# 🛡️ PROTECCIÓN DEL PANEL DE ADMINISTRACIÓN (PATH SECRETO)
# ==========================================================================
# Leemos un path alfanumérico complejo desde tus archivos .env.dev, .env.docker o .env.prod
# Ejemplo en tu .env: ADMIN_SECRET_PATH=axentra-os-backend-dashboard-2026/
ADMIN_PATH = config('ADMIN_SECRET_PATH', default='axentra-core-secret-portal-manager-wsl/')

urlpatterns = [
    # 1. Panel de Administración Ofuscado/Secreto
    path(ADMIN_PATH, admin.site.urls),

    # 2. Instancia Global de Django Ninja (Para endpoints JSON cuando se requieran)
    #path('api/v1/', api.urls),
    
    # 3. CONEXIÓN DEL CHASIS UNIFICADO DE CIBERSEGURIDAD e IDENTIDAD (Shared Bus)
    path('', include('apps.security.urls')),

    # 3. Launcher Principal de Aplicaciones (Raíz del Sistema Operativo)
    path('', launcher_home_view, name='launcher_home'),
]

# ==========================================================================
# 👑 MANEJADORES DE ERRORES GLOBALES
# ==========================================================================
# Django buscará automáticamente '404.html', '500.html' y '403.html' en tu raíz de templates
# handler404 = 'django.views.defaults.page_not_found'
# handler500 = 'django.views.defaults.server_error'
# handler403 = 'django.views.defaults.permission_denied'

# ==========================================================================
# SERVIDORES DE ASSETS EN DESARROLLO (LOCAL)
# ==========================================================================
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)