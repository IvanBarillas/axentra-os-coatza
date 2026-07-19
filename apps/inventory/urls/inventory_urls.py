# apps/inventory/urls/inventory_urls.py

from django.urls import path
from apps.inventory.views import (
    asset_condition_view,
    asset_correct_view,
    asset_detail_view,
    asset_list_view,
    custody_detail_view,
    custody_list_view,
    disposal_detail_view,
    disposal_list_view,
    document_list_view,
    financial_dashboard_view,
    intake_approve_view,
    intake_cancel_view,
    intake_create_view,
    intake_department_decision_view,
    intake_directory_areas_view,
    intake_directory_departments_view,
    intake_directory_users_view,
    intake_detail_view,
    intake_list_view,
    intake_observe_view,
    intake_register_view,
    intake_send_to_patrimony_view,
    intake_submit_view,
    inventory_dashboard_view,
    loan_detail_view,
    loan_list_view,
    movement_detail_view,
    movement_list_view,
    physical_audit_detail_view,
    physical_audit_list_view,
)

app_name = "inventory"

urlpatterns = [
    # Panel principal
    path("", inventory_dashboard_view, name="dashboard"),

    # Activos patrimoniales
    path("assets/", asset_list_view, name="asset_list"),
    path("assets/<uuid:asset_id>/", asset_detail_view, name="asset_detail"),
    path("assets/<uuid:asset_id>/correct/", asset_correct_view, name="asset_correct"),
    path("assets/<uuid:asset_id>/condition/", asset_condition_view, name="asset_condition"),

    # Solicitudes de alta (Intakes)
    path("intakes/", intake_list_view, name="intake_list"),
    path("intakes/new/", intake_create_view, name="intake_create"),
    path("intakes/directory/departments/", intake_directory_departments_view, name="intake_directory_departments"),
    path("intakes/directory/areas/", intake_directory_areas_view, name="intake_directory_areas"),
    path("intakes/directory/users/", intake_directory_users_view, name="intake_directory_users"),
    path("intakes/<uuid:intake_id>/", intake_detail_view, name="intake_detail"),
    path("intakes/<uuid:intake_id>/submit/", intake_submit_view, name="intake_submit"),
    path("intakes/<uuid:intake_id>/department-decision/", intake_department_decision_view, name="intake_department_decision"),
    path("intakes/<uuid:intake_id>/send-to-patrimony/", intake_send_to_patrimony_view, name="intake_send_to_patrimony"),
    path("intakes/<uuid:intake_id>/observe/", intake_observe_view, name="intake_observe"),
    path("intakes/<uuid:intake_id>/approve/", intake_approve_view, name="intake_approve"),
    path("intakes/<uuid:intake_id>/register/", intake_register_view, name="intake_register"),
    path("intakes/<uuid:intake_id>/cancel/", intake_cancel_view, name="intake_cancel"),

    # Resguardos
    path("custodies/", custody_list_view, name="custody_list"),
    path("custodies/<uuid:custody_id>/", custody_detail_view, name="custody_detail"),

    # Movimientos patrimoniales
    path("movements/", movement_list_view, name="movement_list"),
    path("movements/<uuid:movement_id>/", movement_detail_view, name="movement_detail"),

    # Préstamos
    path("loans/", loan_list_view, name="loan_list"),
    path("loans/<uuid:loan_id>/", loan_detail_view, name="loan_detail"),

    # Bajas patrimoniales
    path("disposals/", disposal_list_view, name="disposal_list"),
    path("disposals/<uuid:disposal_id>/", disposal_detail_view, name="disposal_detail"),

    # Documentos y evidencias
    path("documents/", document_list_view, name="document_list"),

    # Auditoría física
    path("physical-audits/", physical_audit_list_view, name="physical_audit_list"),
    path("physical-audits/<uuid:session_id>/", physical_audit_detail_view, name="physical_audit_detail"),

    # Finanzas y conciliación
    path("financials/", financial_dashboard_view, name="financial_dashboard"),
]
