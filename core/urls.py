from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),

]

# 👑 MANEJADORES DE ERRORES GLOBALES

# Django buscará automáticamente '404.html', '500.html' y '403.html' en tu raíz de templates
#handler404 = 'django.views.defaults.page_not_found'
#handler500 = 'django.views.defaults.server_error'
#handler403 = 'django.views.defaults.permission_denied'
# Servir archivos multimedia (imágenes de trámites, logos, etc.) en entorno de desarrollo (Local)

  

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)