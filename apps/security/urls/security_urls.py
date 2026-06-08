from django.urls import path
from apps.security.views import security_dashboard_view, dynamic_permission_matrix_view

urls_security = [
    # Cabina de Mando de Ciberseguridad Central
    path('dashboard/', security_dashboard_view, name='dashboard'),
    path('matriz/', dynamic_permission_matrix_view, name='dynamic_matrix'),
    path('identidad/', security_dashboard_view, name='tenant_config'), 
]