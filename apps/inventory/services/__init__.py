"""API pública de la capa de servicios de Inventory."""

from .asset_service import correct_asset, delete_asset, update_asset_condition
from .audit_service import (
    build_audit_request_context, log_bypass_event, log_inventory_event,
    log_model_change, model_snapshot,
)
from .folio_service import generate_inventory_folio, preview_inventory_folio
from .intake_service import (
    approve_patrimony_intake, cancel_intake, classify_capitalization,
    create_and_submit_intake, create_intake_draft,
    create_intake_from_external_source, decide_department_intake,
    observe_patrimony_intake,
    register_approved_intake, send_to_patrimony, submit_intake,
)
from .movement_service import (
    accept_movement_destination,
    approve_movement_origin,
    create_movement_request,
    create_movement,
    execute_location_change,
    execute_reassignment,
    execute_transfer,
    execute_approved_movement,
)
from .photo_service import upload_asset_photo
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
from .disposal_service import (
    cancel_disposal,
    create_disposal_request,
    execute_disposal,
    finalize_disposal_approval,
    resolve_disposal_stage,
    submit_disposal_request,
)
from .document_service import (
    resolve_inventory_document,
    upload_disposal_stage_document,
    upload_inventory_document,
)
from .physical_audit_service import (
    begin_physical_audit_reconciliation,
    cancel_physical_audit,
    close_physical_audit,
    create_physical_audit,
    freeze_physical_audit,
    mark_audit_item_not_found,
    mark_pending_audit_items_not_found,
    reconcile_physical_audit_item,
    register_unlisted_audit_item,
    scan_physical_audit_item,
    start_physical_audit,
)
from .physical_audit_evidence_service import (
    upload_physical_audit_document,
    upload_physical_audit_photo,
)

__all__ = [name for name in globals() if not name.startswith("_")]
