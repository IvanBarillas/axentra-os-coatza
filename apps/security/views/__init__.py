# apps/security/views/__init__.py

# 👤 PILAR 1: GESTIÓN DE EXPEDIENTES Y PERSONAL (ACCOUNTS)
from .accounts_views import (
    accounts_analytics_view,     
    funcionario_list_view, 
    funcionario_create_view, 
    funcionario_editar_view, 
    funcionario_cambiar_password_view, 
    funcionario_soft_delete_view,funcionario_detail_view,
    # ENDPOINTS DE COCHERA HTMX (SIDEBAR 2)
    funcionario_sub_identidad_view, funcionario_sub_hardware_view, funcionario_sub_telefonia_view
)

# 🏛️ PILAR 2: TOPOLOGÍA GUBERNAMENTAL (ORGANIGRAMA)
from .organigrama_views import (
    organigrama_dashboard_view,   
    estructura_list_view, 
    sede_list_view, 
    sede_create_view, 
    sede_update_view,             
    sede_soft_delete_view,        
    sede_toggle_status_view,
    
    # 🗂️ Expediente Contextual de Sede
    sede_detail_view,
    sede_sub_identidad_view,
    sede_sub_dependencias_view,
    sede_sub_areas_view,
    sede_sub_funcionarios_view,
    
    dependencia_list_view,
    dependencia_create_view, 
    dependencia_update_view,      
    dependencia_soft_delete_view, 
    dependencia_toggle_status_view, 
    
    dependencia_detail_view,
    dependencia_sub_identidad_view,
    dependencia_sub_areas_view,
    dependencia_sub_sedes_view,
    dependencia_sub_funcionarios_view,

    area_list_view,
    area_create_view, 
    area_update_view,             
    area_soft_delete_view,        
    area_toggle_status_view,
    
    area_detail_view,
    area_sub_identidad_view,
    area_sub_funcionarios_view,
          
    cargar_areas_htmx_view, 
    vincular_areas_ajax_view
)

# 🛡️ PILAR 3: CIBERSEGURIDAD CENTRAL Y GOBERNANZA (SECURITY)
# 🟢 CORRECCIÓN: Importamos desde el archivo unificado security_views.py
from .security_views import (
    security_control_panel_view,
    security_dashboard_view,
    dynamic_permission_matrix_view,
    tenant_config_view,
    guardar_llaves_json_view,
    inyectar_funcionario_view,
)

# Exposición oficial para los enrutadores de URLs de Axentra OS
__all__ = [
    # Accounts
    'accounts_analytics_view',
    'funcionario_list_view', 
    'funcionario_detail_view',
    'funcionario_create_view', 
    'funcionario_editar_view', 
    'funcionario_cambiar_password_view', 
    'funcionario_soft_delete_view',
    # ENDPOINTS DE COCHERA HTMX (SIDEBAR 2)
    'funcionario_sub_identidad_view', 'funcionario_sub_hardware_view', 'funcionario_sub_telefonia_view',
    
    # Organigrama
    'organigrama_dashboard_view',
    'estructura_list_view', 
    'sede_list_view', 
    'sede_create_view', 
    'sede_update_view',
    'sede_soft_delete_view',
    'sede_toggle_status_view',
    
    # 🗂️ Expediente Contextual de Sede
    'sede_detail_view',
    'sede_sub_identidad_view',
    'sede_sub_dependencias_view',
    'sede_sub_areas_view',
    'sede_sub_funcionarios_view',
     
    'dependencia_list_view',
    'dependencia_create_view', 
    'dependencia_update_view',
    'dependencia_soft_delete_view',
    'dependencia_toggle_status_view',
    
    'dependencia_detail_view',
    'dependencia_sub_identidad_view',
    'dependencia_sub_areas_view',
    'dependencia_sub_sedes_view',
    'dependencia_sub_funcionarios_view',
    
    'area_list_view',
    'area_create_view', 
    'area_update_view',
    'area_soft_delete_view',
    'area_toggle_status_view',
    
    'area_detail_view',
    'area_sub_identidad_view',
    'area_sub_funcionarios_view',
    
    'cargar_areas_htmx_view', 
    'vincular_areas_ajax_view',
    
    # Security
    'security_control_panel_view',
    'security_dashboard_view',
    'dynamic_permission_matrix_view',
    'guardar_llaves_json_view',
    'inyectar_funcionario_view',
    'tenant_config_view'
]