# apps/security/views/__init__.py

# 👤 PILAR 1: GESTIÓN DE EXPEDIENTES Y PERSONAL (ACCOUNTS)
from .accounts_views import (
    accounts_control_panel_view,  # 🟢 Agregado
    accounts_dashboard_view,      # 🟢 Agregado
    funcionario_list_view, 
    funcionario_create_view, 
    funcionario_editar_view, 
    funcionario_cambiar_password_view, 
    funcionario_soft_delete_view
)

# 🏛️ PILAR 2: TOPOLOGÍA GUBERNAMENTAL (ORGANIGRAMA)
from .organigrama_views import (
    organigrama_control_view,     # 🟢 Sincronizado
    organigrama_dashboard_view,   # 🟢 Sincronizado
    estructura_list_view, 
    sede_list_view, 
    sede_create_view, 
    sede_update_view,             # 🟢 Agregado
    sede_soft_delete_view,        # 🟢 Agregado
    sede_toggle_status_view, 
    dependencia_create_view, 
    dependencia_update_view,      # 🟢 Agregado
    dependencia_soft_delete_view, # 🟢 Agregado
    dependencia_toggle_status_view, # 🟢 Agregado
    area_create_view, 
    area_update_view,             # 🟢 Agregado
    area_soft_delete_view,        # 🟢 Agregado
    area_toggle_status_view,      # 🟢 Agregado
    cargar_areas_htmx_view, 
    vincular_areas_ajax_view
)

# 🛡️ PILAR 3: CIBERSEGURIDAD CENTRAL Y GOBERNANZA (SECURITY)
# 🟢 CORRECCIÓN: Importamos desde el archivo unificado security_views.py
from .security_views import (
    security_control_panel_view,
    security_dashboard_view,
    dynamic_permission_matrix_view,
    tenant_config_view
)

# Exposición oficial para los enrutadores de URLs de Axentra OS
__all__ = [
    # Accounts
    'accounts_control_panel_view',
    'accounts_dashboard_view',
    'funcionario_list_view', 
    'funcionario_create_view', 
    'funcionario_editar_view', 
    'funcionario_cambiar_password_view', 
    'funcionario_soft_delete_view',
    
    # Organigrama
    'organigrama_control_view',
    'organigrama_dashboard_view',
    'estructura_list_view', 
    'sede_list_view', 
    'sede_create_view', 
    'sede_update_view',
    'sede_soft_delete_view',
    'sede_toggle_status_view', 
    'dependencia_create_view', 
    'dependencia_update_view',
    'dependencia_soft_delete_view',
    'dependencia_toggle_status_view',
    'area_create_view', 
    'area_update_view',
    'area_soft_delete_view',
    'area_toggle_status_view',
    'cargar_areas_htmx_view', 
    'vincular_areas_ajax_view',
    
    # Security
    'security_control_panel_view',
    'security_dashboard_view',
    'dynamic_permission_matrix_view',
    'tenant_config_view'
]