from django.urls import path
from django.contrib.auth import views as auth_views
from django.views.generic import TemplateView
from apps.security.views import (
    accounts_dashboard_view, funcionario_list_view, funcionario_create_view, 
    funcionario_editar_view, funcionario_cambiar_password_view, funcionario_soft_delete_view
)

# Definimos las rutas puras. El namespace se controlará en el __init__.py
urls_accounts = [
    # Autenticación Oficial de Axentra OS
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html', redirect_authenticated_user=True), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='accounts:login'), name='logout'),
    path('acceso-denegado/', TemplateView.as_view(template_name='errors/403.html'), name='access_denied'),

    # Cabina Operativa de Personal
    path('dashboard/', accounts_dashboard_view, name='dashboard'),
    path('funcionarios/lista/', funcionario_list_view, name='funcionario_list_table'),
    path('funcionarios/nuevo/', funcionario_create_view, name='funcionario_create'),
    
    # Mutaciones transaccionales de fichas
    path('funcionarios/editar/<uuid:pk>/', funcionario_editar_view, name='funcionario_update'),
    path('funcionarios/password/<uuid:pk>/', funcionario_cambiar_password_view, name='funcionario_password'),
    path('funcionarios/baja/<uuid:pk>/', funcionario_soft_delete_view, name='funcionario_delete'),
]