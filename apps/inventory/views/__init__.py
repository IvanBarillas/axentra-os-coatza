"""API pública de vistas de la aplicación Inventory."""

from .asset_views import (
    asset_condition_view,
    asset_correct_view,
    asset_detail_view,
    asset_list_view,
)
from .dashboard_views import inventory_dashboard_view
from .intake_views import (
    intake_approve_view,
    intake_cancel_view,
    intake_create_view,
    intake_department_decision_view,
    intake_detail_view,
    intake_list_view,
    intake_observe_view,
    intake_register_view,
    intake_send_to_patrimony_view,
    intake_submit_view,
)
from .registry_views import (
    custody_detail_view,
    custody_list_view,
    disposal_detail_view,
    disposal_list_view,
    document_list_view,
    financial_dashboard_view,
    loan_detail_view,
    loan_list_view,
    movement_detail_view,
    movement_list_view,
    physical_audit_detail_view,
    physical_audit_list_view,
)


__all__ = [
    # Dashboard
    "inventory_dashboard_view",

    # Activos
    "asset_condition_view",
    "asset_correct_view",
    "asset_detail_view",
    "asset_list_view",

    # Solicitudes de alta
    "intake_approve_view",
    "intake_cancel_view",
    "intake_create_view",
    "intake_department_decision_view",
    "intake_detail_view",
    "intake_list_view",
    "intake_observe_view",
    "intake_register_view",
    "intake_send_to_patrimony_view",
    "intake_submit_view",

    # Resguardos
    "custody_detail_view",
    "custody_list_view",

    # Movimientos
    "movement_detail_view",
    "movement_list_view",

    # Préstamos
    "loan_detail_view",
    "loan_list_view",

    # Bajas
    "disposal_detail_view",
    "disposal_list_view",

    # Documentos
    "document_list_view",

    # Auditoría física
    "physical_audit_detail_view",
    "physical_audit_list_view",

    # Finanzas
    "financial_dashboard_view",
]

