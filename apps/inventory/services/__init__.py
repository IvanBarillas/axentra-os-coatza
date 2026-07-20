"""API pública de la capa de servicios de Inventory."""

from .asset_service import correct_asset, delete_asset, update_asset_condition
from .audit_service import (
    build_audit_request_context, log_bypass_event, log_inventory_event,
    log_model_change, model_snapshot,
)
from .folio_service import generate_inventory_folio, preview_inventory_folio
from .intake_service import (
    approve_patrimony_intake, cancel_intake, classify_capitalization,
    create_intake_draft, decide_department_intake, observe_patrimony_intake,
    register_approved_intake, send_to_patrimony, submit_intake,
)
from .movement_service import create_movement
from .custody_service import (
    accept_custody_assignment,
    authorize_custody_assignment,
    cancel_custody_assignment,
    complete_custody_return,
    create_custody_assignment,
    deliver_custody_assignment,
    reject_custody_assignment,
    request_custody_return,
    submit_custody_assignment,
)
from .loan_service import (
    authorize_asset_loan,
    cancel_asset_loan,
    create_asset_loan,
    decide_department_loan,
    deliver_asset_loan,
    request_asset_loan_return,
    return_asset_loan,
    submit_asset_loan,
)

__all__ = [name for name in globals() if not name.startswith("_")]
