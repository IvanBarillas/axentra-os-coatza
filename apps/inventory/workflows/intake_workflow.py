"""Guía visual del alta controlada de bienes patrimoniales."""

from apps.shared.workflows import (
    WorkflowActor,
    WorkflowDefinition,
    WorkflowStep,
    WorkflowTransition,
)


INVENTORY_INTAKE_WORKFLOW = WorkflowDefinition(
    code="inventory.asset_intake",
    name="¿Cómo ingresa un bien al inventario?",
    description=(
        "Explica quién captura la solicitud, quién confirma que el bien llegó "
        "a la dependencia y cuándo Control Patrimonial genera el folio oficial."
    ),
    version="1.0",
    actors=(
        WorkflowActor(
            "requester",
            "Patrimonio o Adquisiciones",
            "Captura los datos del bien y reúne la evidencia inicial.",
            "clipboard-plus",
        ),
        WorkflowActor(
            "department",
            "Director de la dependencia",
            "Confirma que el bien corresponde a su dependencia y que fue recibido.",
            "building-2",
        ),
        WorkflowActor(
            "patrimony",
            "Control Patrimonial",
            "Revisa la clasificación, el expediente y los datos contables.",
            "landmark",
        ),
        WorkflowActor(
            "system",
            "Axentra Inventory",
            "Genera el folio oficial y abre el expediente patrimonial.",
            "badge-check",
        ),
        WorkflowActor(
            "audit",
            "Bitácora",
            "Conserva las decisiones, observaciones y accesos especiales.",
            "scroll-text",
        ),
    ),
    steps=(
        WorkflowStep("draft", "DRAFT", "Capturar la solicitud", "requester", icon="file-pen-line"),
        WorkflowStep("submitted", "SUBMITTED", "Esperar confirmación de la dependencia", "department", icon="send"),
        WorkflowStep(
            "department_review",
            "DEPARTMENT_APPROVED",
            "Enviar el expediente a Control Patrimonial",
            "department",
            icon="building-2",
        ),
        WorkflowStep(
            "patrimony_review",
            "UNDER_PATRIMONY_REVIEW",
            "Revisar documentos y clasificación",
            "patrimony",
            icon="clipboard-check",
        ),
        WorkflowStep("observed", "OBSERVED", "Corregir lo observado", "requester", icon="message-square-warning"),
        WorkflowStep("approved", "APPROVED", "Autorizar el alta", "patrimony", icon="circle-check-big"),
        WorkflowStep("registered", "REGISTERED", "Generar folio y abrir expediente", "system", icon="badge-check", terminal=True),
        WorkflowStep("rejected", "DEPARTMENT_REJECTED", "Explicar el rechazo", "department", icon="circle-x", terminal=True),
        WorkflowStep("cancelled", "CANCELLED", "Cancelar la solicitud", "requester", icon="ban", terminal=True),
        WorkflowStep("audit", "AUDITED", "Guardar evidencia del proceso", "audit", icon="file-clock", terminal=True),
    ),
    transitions=(
        WorkflowTransition("draft", "submitted", "Enviar solicitud", permission="can_submit_asset_intake", explanation="La solicitud todavía no es un activo y no tiene folio oficial."),
        WorkflowTransition("submitted", "department_review", "Bien confirmado", "success", permission="can_approve_department_intake", explanation="La dependencia confirma que reconoce el bien y acepta su responsabilidad."),
        WorkflowTransition("submitted", "rejected", "No corresponde", "danger", permission="can_approve_department_intake", explanation="Debe indicarse claramente el motivo del rechazo."),
        WorkflowTransition("department_review", "patrimony_review", "Enviar a Patrimonio", permission="can_validate_patrimony_intake"),
        WorkflowTransition("patrimony_review", "observed", "Solicitar correcciones", "warning", permission="can_validate_patrimony_intake"),
        WorkflowTransition("observed", "submitted", "Enviar correcciones", permission="can_submit_asset_intake"),
        WorkflowTransition("patrimony_review", "approved", "Expediente correcto", "success", permission="can_validate_patrimony_intake"),
        WorkflowTransition("approved", "registered", "Registrar oficialmente", "success", permission="can_register_asset", explanation="Sólo en este momento se genera el folio oficial y nace el activo patrimonial."),
        WorkflowTransition("draft", "cancelled", "Cancelar", "danger"),
        WorkflowTransition("submitted", "cancelled", "Cancelar con motivo", "danger"),
        WorkflowTransition("rejected", "audit", "Guardar decisión", "warning"),
        WorkflowTransition("registered", "audit", "Guardar alta", "success"),
        WorkflowTransition("cancelled", "audit", "Guardar cancelación", "warning"),
    ),
    primary_path=(
        "draft",
        "submitted",
        "department_review",
        "patrimony_review",
        "approved",
        "registered",
    ),
    notes=(
        "Una solicitud no es todavía un bien patrimonial y no recibe folio oficial.",
        "El director confirma la recepción; Control Patrimonial valida y registra.",
        "Los accesos especiales de owner o manager deben conservar una justificación en la bitácora.",
    ),
)


__all__ = ["INVENTORY_INTAKE_WORKFLOW"]
