from django.urls import path
from apps.security.views import (
    estructura_list_view, sede_list_view, sede_create_view, 
    dependencia_create_view, area_create_view, sede_toggle_status_view, 
    cargar_areas_htmx_view, vincular_areas_ajax_view, funcionario_soft_delete_view
)

urls_organigrama = [
    # Inteligencia Estructural del Ayuntamiento
    path('dashboard/', estructura_list_view, name='dashboard'), 
    path('estructura/', estructura_list_view, name='estructura_list'),
    
    # Inmuebles y Territorio Municipal
    path('sedes/', sede_list_view, name='sede_list'),
    path('sedes/nueva/', sede_create_view, name='sede_create'),
    path('sedes/eliminar/<uuid:pk>/', funcionario_soft_delete_view, name='sede_delete'), 
    
    # Altas Transaccionales
    path('dependencia/nueva/', dependencia_create_view, name='dependencia_create'),
    path('area/nueva/', area_create_view, name='area_create'),
    
    # Tuberías Reactivas de HTMX y AJAX
    path('sedes/<uuid:pk>/toggle/', sede_toggle_status_view, name='sede_toggle'),
    path('ajax/cargar-areas/', cargar_areas_htmx_view, name='cargar_areas_htmx'),
    path('ajax/estructura-areas/<uuid:dep_id>/', vincular_areas_ajax_view, name='estructura_areas_ajax'),
]