# apps/security/urls/organigrama_urls.py
from django.urls import path
from apps.security.views.organigrama_views import (
    area_toggle_status_view,
    dependencia_toggle_status_view,
    organigrama_dashboard_view,
    estructura_list_view, 
    # Sedes
    sede_list_view, 
    sede_create_view, 
    sede_update_view,
    sede_soft_delete_view,
    sede_toggle_status_view,
    sede_detail_view,
    sede_sub_identidad_view,
    sede_sub_dependencias_view,
    sede_sub_areas_view,
    sede_sub_funcionarios_view,
    # Dependencias
    dependencia_list_view,
    dependencia_create_view, 
    dependencia_update_view,
    dependencia_soft_delete_view,
    dependencia_detail_view,
    dependencia_sub_identidad_view,
    dependencia_sub_areas_view,
    dependencia_sub_sedes_view,
    dependencia_sub_funcionarios_view,
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
    path('analytics/', organigrama_dashboard_view, name='dashboard'),
    path('estructura/', estructura_list_view, name='estructura_list'),
    
    # 🗺️ Inmuebles y Territorio Municipal (Sedes)
    path('sedes/', sede_list_view, name='sede_list'),
    path('sedes/nueva/', sede_create_view, name='sede_create'),
    path("sedes/editar/<uuid:pk>/", sede_update_view, name="sede_update"),
    path('sedes/eliminar/<uuid:pk>/', sede_soft_delete_view, name='sede_delete'), 
    path('sedes/estado/<uuid:pk>/', sede_toggle_status_view, name='sede_toggle_status'),
    
    # 🗂️ Expediente Contextual de Sede
    path("sedes/<uuid:pk>/", sede_detail_view, name="sede_detail"),
    path("sedes/<uuid:pk>/identidad/", sede_sub_identidad_view, name="sede_sub_identidad"),
    path("sedes/<uuid:pk>/dependencias/", sede_sub_dependencias_view, name="sede_sub_dependencias"),
    path("sedes/<uuid:pk>/areas/", sede_sub_areas_view, name="sede_sub_areas"),
    path("sedes/<uuid:pk>/funcionarios/", sede_sub_funcionarios_view, name="sede_sub_funcionarios"),

    # Operaciones Transaccionales de Dependencias (Direcciones Generales)
    path("dependencias/", dependencia_list_view, name="dependencia_list"),
    path('dependencia/nueva/', dependencia_create_view, name='dependencia_create'),
    path('dependencia/editar/<uuid:pk>/', dependencia_update_view, name='dependencia_update'),
    path('dependencia/eliminar/<uuid:pk>/', dependencia_soft_delete_view, name='dependencia_delete'),
    path('dependencia/estado/<uuid:pk>/', dependencia_toggle_status_view, name='dependencia_toggle_status'),
    
    # 🗂️ Expediente Contextual de Dependencia
    path("dependencias/<uuid:pk>/", dependencia_detail_view, name="dependencia_detail"),
    path("dependencias/<uuid:pk>/identidad/", dependencia_sub_identidad_view, name="dependencia_sub_identidad"),
    path("dependencias/<uuid:pk>/areas/", dependencia_sub_areas_view, name="dependencia_sub_areas"),
    path("dependencias/<uuid:pk>/sedes/", dependencia_sub_sedes_view, name="dependencia_sub_sedes"),
    path("dependencias/<uuid:pk>/funcionarios/", dependencia_sub_funcionarios_view, name="dependencia_sub_funcionarios"),
        
    # 📍 Operaciones Transaccionales de Áreas (Sub-Oficinas Internas)
    path('area/nueva/', area_create_view, name='area_create'),
    path('area/editar/<uuid:pk>/', area_update_view, name='area_update'),
    path('area/eliminar/<uuid:pk>/', area_soft_delete_view, name='area_delete'),
    path('area/estado/<uuid:pk>/', area_toggle_status_view, name='area_toggle_status'),
    
    # ⚡ Tuberías Reactivas Asíncronas (HTMX / AJAX Pipelines)
    path('ajax/cargar-areas/', cargar_areas_htmx_view, name='cargar_areas_htmx'),
    path('ajax/estructura-areas/<uuid:dep_id>/', vincular_areas_ajax_view, name='estructura_areas_ajax'),
]