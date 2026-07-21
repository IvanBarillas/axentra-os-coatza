from .asset_views import (
    asset_audits_view,
    asset_condition_view,
    asset_correct_view,
    asset_custodies_view,
    asset_detail_view,
    asset_disposals_view,
    asset_documents_view,
    asset_extended_record_view,
    asset_financials_view,
    asset_history_view,
    asset_list_view,
    asset_loan_create_view,
    asset_loans_view,
    asset_movements_view,
    asset_photos_view,
    asset_technical_view,
    asset_technical_sheet_view,
)
from .dashboard_views import inventory_dashboard_view
from .help_views import inventory_help_detail_view, inventory_help_view
from .intake_views import (
    intake_approve_view, intake_cancel_view, intake_create_view,
    intake_directory_areas_view, intake_directory_departments_view,
    intake_directory_users_view,
    intake_department_decision_view, intake_detail_view, intake_list_view,
    intake_observe_view, intake_register_view, intake_send_to_patrimony_view,
    intake_submit_view,
)
from .registry_views import (
    custody_accept_view, custody_authorize_view, custody_cancel_view,
    custody_complete_return_view, custody_create_view, custody_deliver_view,
    custody_directory_areas_view, custody_directory_departments_view,
    custody_directory_users_view,
    custody_detail_view, custody_list_view, custody_reject_view,
    custody_request_return_view, custody_submit_view, disposal_detail_view,
    disposal_list_view, document_list_view, financial_dashboard_view,
    loan_authorize_view, loan_cancel_view, loan_create_view,
    loan_deliver_view, loan_department_decision_view, loan_detail_view,
    loan_directory_areas_view, loan_directory_assets_view,
    loan_directory_departments_view, loan_directory_users_view,
    loan_list_view, loan_request_return_view, loan_return_view,
    loan_submit_view, movement_detail_view, movement_list_view,
    physical_audit_detail_view, physical_audit_list_view,
)

__all__ = [name for name in globals() if name.endswith("_view")]
