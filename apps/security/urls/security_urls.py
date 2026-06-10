# apps/security/urls/security_urls.py
from django.urls import path
from apps.security.views.security_views import (
    security_control_panel_view,
    security_dashboard_view,
    dynamic_permission_matrix_view,
    tenant_config_view
)

urls_security = [
    path('control/', security_control_panel_view, name='control_panel'),
    path('dashboard/', security_dashboard_view, name='dashboard'),
    path('matriz/', dynamic_permission_matrix_view, name='dynamic_matrix'),
    path('identidad/', tenant_config_view, name='tenant_config'), 
]