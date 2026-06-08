# apps/security/urls/__init__.py
from django.urls import path, include

# Importamos las listas de rutas desde nuestros sub-archivos lógicos
from .accounts_urls import urls_accounts
from .organigrama_urls import urls_organigrama
from .security_urls import urls_security

# Convertimos cada lista en una tupla válida de Django con su propio NameSpace de aislamiento
accounts_patterns = (urls_accounts, 'accounts')
organigrama_patterns = (urls_organigrama, 'organigrama')
security_patterns = (urls_security, 'security')

# Acoplamos todo en el urlpatterns que la app security expondrá al proyecto global
urlpatterns = [
    path('auth/', include(accounts_patterns)),
    path('organigrama/', include(organigrama_patterns)),
    path('security/', include(security_patterns)),
]