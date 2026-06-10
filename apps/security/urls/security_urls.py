# apps/security/urls/security_urls.py
from django.urls import path
from apps.security.views.security_views import (
    expulsar_usuario_modulo_total_ajax_view,
    guardar_llaves_json_view,
    inyectar_funcionario_view,
    security_control_panel_view,     
    security_dashboard_view,         
    dynamic_permission_matrix_view,  
    matrix_capabilities_view,        
    add_capability_node_view,        
    toggle_capability_ajax_view,     
    tenant_config_view,
    toggle_user_modulo_active_ajax_view               
)

# El namespace 'security' se amarra en el archivo raíz principal del proyecto
urls_security = [
    # 🏁 PILAR 1: CUARTO DE CONTROL TÁCTICO LIGERO (Opción 1 del SIDEBAR)
    path('control/', security_control_panel_view, name='control_panel'),

    # 📊 PILAR 2: CONSOLA ANALÍTICA FORENSE / PACKET STREAM (Opción 4 del SIDEBAR)
    path('dashboard/', security_dashboard_view, name='dashboard'),
    
    # 🪐 PILAR 3: CÁPSULA DINÁMICA UNIVERSAL (Matriz de Checkboxes JSONField)
    path('matriz/', dynamic_permission_matrix_view, name='dynamic_matrix'),
    path('matriz/guardar-llaves/<int:app_id>/<uuid:user_id>/', guardar_llaves_json_view, name='guardar_llaves'),
    path('matriz/inyectar-funcionario/<int:app_id>/', inyectar_funcionario_view, name='inyectar_funcionario'),
    
    
    # Las dos vías de contención: Toggle de suspensión y Purga total
    path('matriz/toggle-status/<uuid:user_id>/<int:app_id>/', toggle_user_modulo_active_ajax_view, name='toggle_user_modulo_active'),
    path('matriz/purga-total/<uuid:user_id>/<int:app_id>/', expulsar_usuario_modulo_total_ajax_view, name='expulsar_usuario_modulo_total'),
    
    # 🎛️ PILAR 4: GOBERNANZA DE CAPACIDADES GEOGRÁFICAS
    path('platform/capabilities/', matrix_capabilities_view, name='matrix_capabilities'),
    path('platform/capabilities/add/<int:app_id>/', add_capability_node_view, name='add_capability_node'),
    
    # 🔄 PILAR 5: ENDPOINT INTERCEPTOR ASÍNCRONO PARA INTERRUPTORES EN VIVO
    path('platform/capabilities/toggle/<uuid:dep_id>/<int:app_id>/', toggle_capability_ajax_view, name='toggle_capability'),
    
    # ⚙️ PILAR 6: CONFIGURACIÓN CORPORATIVA GLOBAL (Tenant CONFIG Singleton)
    path('identidad/', tenant_config_view, name='tenant_config'), 
] 