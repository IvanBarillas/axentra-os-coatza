# apps/security/urls/accounts_urls.py (o donde manejes tus rutas de accounts)
from django.urls import path
from django.contrib.auth import views as auth_views
from django.views.generic import TemplateView

from apps.security.views.accounts_views import accounts_control_panel_view, accounts_dashboard_view, funcionario_cambiar_password_view, funcionario_create_view, funcionario_editar_view, funcionario_list_view, funcionario_soft_delete_view, funcionario_toggle_status_view


urls_accounts = [
    # Autenticación Oficial de Axentra OS
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html', redirect_authenticated_user=True), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='accounts:login'), name='logout'),
    path('acceso-denegado/', TemplateView.as_view(template_name='errors/403.html'), name='access_denied'),

    # 🟢 Panel Administrativo: Chasis ligero general (Opción 1 del SIDEBAR_MENU)
    path('control/', accounts_control_panel_view, name='control_panel'),

    # 📊 Consola Analítica: Dashboard pesado de KPIs (Opción 4 del SIDEBAR_MENU)
    path('dashboard/', accounts_dashboard_view, name='dashboard'),
    
    # 👥 Padrón Operativo (🟢 Saneado el name a 'funcionario_list' para hacer match)
    path('funcionarios/lista/', funcionario_list_view, name='funcionario_list'),
    path('funcionarios/nuevo/', funcionario_create_view, name='funcionario_create'),
    
    # Mutaciones transaccionales de fichas
    path('funcionarios/editar/<uuid:pk>/', funcionario_editar_view, name='funcionario_update'),
    path('funcionarios/password/<uuid:pk>/', funcionario_cambiar_password_view, name='funcionario_password'),
    path('funcionarios/baja/<uuid:pk>/', funcionario_soft_delete_view, name='funcionario_delete'),
    
    path('funcionarios/estado/<uuid:pk>/', funcionario_toggle_status_view, name='funcionario_toggle_status'),
]