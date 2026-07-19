"""API pública de la capa de servicios de Inventory.

Las vistas y demás consumidores del módulo deben importar las operaciones
desde este paquete. Las funciones auxiliares privadas permanecen dentro de
cada archivo de servicio.
"""

from .asset_service import (
    correct_asset,
    delete_asset,
    update_asset_condition,
)
from .audit_service import (
    build_audit_request_context,
    log_bypass_event,
    log_inventory_event,
    log_model_change,
    model_snapshot,
)
from .folio_service import (
    generate_inventory_folio,
    get_effective_folio_policy,
    preview_inventory_folio,
)
from .intake_service import (
    approve_patrimony_intake,
    cancel_intake,
    classify_capitalization,
    create_intake_draft,
    decide_department_intake,
    observe_patrimony_intake,
    register_approved_intake,
    send_to_patrimony,
    submit_intake,
)
from .movement_service import create_movement


__all__ = [
    # Activos
    "correct_asset",
    "delete_asset",
    "update_asset_condition",

    # Auditoría interna
    "build_audit_request_context",
    "log_bypass_event",
    "log_inventory_event",
    "log_model_change",
    "model_snapshot",

    # Folios
    "generate_inventory_folio",
    "get_effective_folio_policy",
    "preview_inventory_folio",

    # Solicitudes de alta
    "approve_patrimony_intake",
    "cancel_intake",
    "classify_capitalization",
    "create_intake_draft",
    "decide_department_intake",
    "observe_patrimony_intake",
    "register_approved_intake",
    "send_to_patrimony",
    "submit_intake",

    # Movimientos
    "create_movement",
]

