# apps/security/views/__init__.py
from .dashboard_views import security_dashboard_view, accounts_dashboard_view
from .accounts_views import (
    funcionario_list_view, funcionario_create_view, 
    funcionario_editar_view, funcionario_cambiar_password_view, funcionario_soft_delete_view
)
from .organigrama_views import (
    estructura_list_view, sede_list_view, sede_create_view, 
    dependencia_create_view, area_create_view, sede_toggle_status_view, 
    cargar_areas_htmx_view, vincular_areas_ajax_view
)
from .matrix_views import dynamic_permission_matrix_view

__all__ = [
    'security_dashboard_view', 'accounts_dashboard_view',
    'funcionario_list_view', 'funcionario_create_view', 'funcionario_editar_view', 
    'funcionario_cambiar_password_view', 'funcionario_soft_delete_view',
    'estructura_list_view', 'sede_list_view', 'sede_create_view', 
    'dependencia_create_view', 'area_create_view', 'sede_toggle_status_view', 
    'cargar_areas_htmx_view', 'vincular_areas_ajax_view',
    'dynamic_permission_matrix_view'
]