# apps/security/urls/accounts_urls.py (o donde manejes tus rutas de accounts)
from django.urls import path
from django.contrib.auth import views as auth_views
from django.views.generic import TemplateView

from apps.security.views.accounts_views import (
    accounts_analytics_view, funcionario_list_view, funcionario_detail_view,
    funcionario_create_view, funcionario_editar_view, funcionario_cambiar_password_view,funcionario_soft_delete_view, funcionario_toggle_status_view,
    funcionario_sub_identidad_view, funcionario_sub_hardware_view, funcionario_sub_telefonia_view
    )


urls_accounts = [
    # Autenticación Oficial de Axentra OS
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html', redirect_authenticated_user=True), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='accounts:login'), name='logout'),
    path('acceso-denegado/', TemplateView.as_view(template_name='errors/403.html'), name='access_denied'),
    
    path('analytics/', accounts_analytics_view, name='analytics'),
    
    path('funcionarios/lista/', funcionario_list_view, name='funcionario_list'),
    path('funcionarios/detalle/<uuid:pk>/', funcionario_detail_view, name='funcionario_detail'),
    
    path('funcionarios/nuevo/', funcionario_create_view, name='funcionario_create'),    
    path('funcionarios/editar/<uuid:pk>/', funcionario_editar_view, name='funcionario_update'),
    path('funcionarios/password/<uuid:pk>/', funcionario_cambiar_password_view, name='funcionario_password'),
    path('funcionarios/baja/<uuid:pk>/', funcionario_soft_delete_view, name='funcionario_delete'),
    path('funcionarios/estado/<uuid:pk>/', funcionario_toggle_status_view, name='funcionario_toggle_status'),
    
    # ENDPOINTS DE COCHERA HTMX (SIDEBAR 2)
    path('funcionarios/sub/identidad/<uuid:pk>/', funcionario_sub_identidad_view, name='funcionario_sub_identidad'),
    path('funcionarios/sub/hardware/<uuid:pk>/', funcionario_sub_hardware_view, name='funcionario_sub_hardware'),
    path('funcionarios/sub/telefonia/<uuid:pk>/', funcionario_sub_telefonia_view, name='funcionario_sub_telefonia'),
]