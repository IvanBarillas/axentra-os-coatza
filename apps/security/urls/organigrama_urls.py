# apps/security/urls/organigrama_urls.py
from django.urls import path
from apps.security.views.organigrama_views import (
    dependencia_toggle_status_view,
    organigrama_control_view,
    organigrama_dashboard_view,
    estructura_list_view, 
     
    # Sedes
    sede_list_view, 
    sede_create_view, 
    sede_update_view,
    sede_soft_delete_view,
    sede_toggle_status_view,
    
    # Dependencias
    dependencia_create_view, 
    dependencia_update_view,
    dependencia_soft_delete_view,
    
    # Áreas
    area_create_view, 
    area_update_view,
    area_soft_delete_view,
    
    # HTMX
    cargar_areas_htmx_view, 
    vincular_areas_ajax_view
)

urls_organigrama = [
    # 📊 Inteligencia Estructural y Dashboard Central
    # 🏢 La Nueva Entrada General de Alta Velocidad (Cuarto de Control)
    path('control/', organigrama_control_view, name='control_panel'), 
    
    # 📊 La Cabina de Mando Analítica (Ahora es una sub-vista restringida)
    path('analytics/', organigrama_dashboard_view, name='dashboard'),
    path('estructura/', estructura_list_view, name='estructura_list'),
    
    # 🗺️ Inmuebles y Territorio Municipal (Sedes)
    path('sedes/', sede_list_view, name='sede_list'),
    path('sedes/nueva/', sede_create_view, name='sede_create'),
    path('sedes/editar/<uuid:pk>/', sede_update_view, name='sede_update'),
    path('sedes/eliminar/<uuid:pk>/', sede_soft_delete_view, name='sede_delete'), 
    path('sedes/estado/<uuid:pk>/', sede_toggle_status_view, name='sede_toggle_status'),
    
    # 📁 Operaciones Transaccionales de Dependencias (Direcciones Generales)
    path('dependencia/nueva/', dependencia_create_view, name='dependencia_create'),
    path('dependencia/editar/<uuid:pk>/', dependencia_update_view, name='dependencia_update'),
    path('dependencia/eliminar/<uuid:pk>/', dependencia_soft_delete_view, name='dependencia_delete'),
    path('dependencia/estado/<uuid:pk>/', dependencia_toggle_status_view, name='dependencia_toggle_status'),

    # 📍 Operaciones Transaccionales de Áreas (Sub-Oficinas Internas)
    path('area/nueva/', area_create_view, name='area_create'),
    path('area/editar/<uuid:pk>/', area_update_view, name='area_update'),
    path('area/eliminar/<uuid:pk>/', area_soft_delete_view, name='area_delete'),
    
    # ⚡ Tuberías Reactivas Asíncronas (HTMX / AJAX Pipelines)
    path('ajax/cargar-areas/', cargar_areas_htmx_view, name='cargar_areas_htmx'),
    path('ajax/estructura-areas/<uuid:dep_id>/', vincular_areas_ajax_view, name='estructura_areas_ajax'),
]