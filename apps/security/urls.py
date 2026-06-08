# apps/security/urls.py
from django.urls import path, include

# Importación atómica de todos los controladores basados en funciones
from apps.security.views import (
    security_dashboard_view, accounts_dashboard_view,
    funcionario_list_view, funcionario_create_view, funcionario_editar_view,
    funcionario_cambiar_password_view, funcionario_soft_delete_view,
    estructura_list_view, sede_list_view, sede_create_view, 
    dependencia_create_view, area_create_view, sede_toggle_status_view, 
    cargar_areas_htmx_view, vincular_areas_ajax_view,
    dynamic_permission_matrix_view
)

# Fallbacks estructurales mínimos para flujos fijos (se integrarán en el auth service luego)
from django.contrib.auth import views as auth_views
from django.views.generic import TemplateView

# =========================================================================
# 👤 SUB-RUTAS: ACCOUNTS (Identidad y Padrón de Personal)
# =========================================================================
accounts_patterns = ([
    # Autenticación Básica (Adaptada a tu esquema funcional)
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html', redirect_authenticated_user=True), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='accounts:login'), name='logout'),
    path('acceso-denegado/', TemplateView.as_view(template_name='errors/403.html'), name='access_denied'),

    # Cabina y Padrón Operativo
    path('dashboard/', accounts_dashboard_view, name='dashboard'),
    path('funcionarios/lista/', funcionario_list_view, name='funcionario_list_table'),
    path('funcionarios/nuevo/', funcionario_create_view, name='funcionario_create'),
    
    # Mutaciones de Fichas e Historiales Críticos
    path('funcionarios/editar/<uuid:pk>/', funcionario_editar_view, name='funcionario_update'),
    path('funcionarios/password/<uuid:pk>/', funcionario_cambiar_password_view, name='funcionario_password'),
    path('funcionarios/baja/<uuid:pk>/', funcionario_soft_delete_view, name='funcionario_delete'),
], 'accounts')

# =========================================================================
# 🏛️ SUB-RUTAS: ORGANIGRAMA (Topología Fisco-Jerárquica)
# =========================================================================
organigrama_patterns = ([
    # Cabina de Inteligencia Institucional
    path('dashboard/', estructura_list_view, name='dashboard'), # Apunta temporalmente a estructura hasta fusionar dashboard_content
    
    # Territorio: Complejos e Inmuebles
    path('sedes/', list_view := sede_list_view, name='sede_list'),
    path('sedes/nueva/', sede_create_view, name='sede_create'),
    path('sedes/eliminar/<uuid:pk>/', funcionario_soft_delete_view, name='sede_delete'), # Delega la baja temporal
    
    # Altas Transaccionales
    path('dependencia/nueva/', dependencia_create_view, name='dependencia_create'),
    path('area/nueva/', area_create_view, name='area_create'),
    path('estructura/', estructura_list_view, name='estructura_list'),
    
    # Tuberías Reactivas Asíncronas (HTMX)
    path('sedes/<uuid:pk>/toggle/', sede_toggle_status_view, name='sede_toggle'),
    path('ajax/cargar-areas/', cargar_areas_htmx_view, name='cargar_areas_htmx'),
    path('ajax/estructura-areas/<uuid:dep_id>/', vincular_areas_ajax_view, name='estructura_areas_ajax'),
], 'organigrama')

# =========================================================================
# 🛡️ SUB-RUTAS: SECURITY (Ciberseguridad y Consola de Checkboxes)
# =========================================================================
security_patterns = ([
    # Cabina de Mando Central
    path('dashboard/', security_dashboard_view, name='dashboard'),
    
    # Cápsula Dinámica Anti-URL Tampering
    path('matriz/', dynamic_permission_matrix_view, name='dynamic_matrix'),
    
    # Singleton de Identidad Corporativa y Marca
    path('identidad/', security_dashboard_view, name='tenant_config'), # Redirección segura temporal
], 'security')


# =========================================================================
# 🚀 PATRÓN DE ENRUTAMIENTO GENERAL (EXPOSICIÓN AL CORE OS)
# =========================================================================
# Encapsulamos las sub-rutas mediante include() directo, manteniendo intactos los namespaces
urlpatterns = [
    path('app/auth/', include(accounts_patterns)),
    path('app/organigrama/', include(organigrama_patterns)),
    path('app/security/', include(security_patterns)),
]