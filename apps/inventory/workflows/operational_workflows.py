"""Diagramas funcionales de los procesos principales de Inventory."""

from apps.shared.workflows import (
    WorkflowActor,
    WorkflowDefinition,
    WorkflowStep,
    WorkflowTransition,
)


def actor(code, name, description=""):
    return WorkflowActor(code, name, description)


CUSTODY_WORKFLOW = WorkflowDefinition(
    code="inventory.custody", name="Asignación de resguardo",
    description="Responsabilidad permanente de un servidor público sobre un bien.",
    actors=(actor("patrimony", "Control Patrimonial"), actor("director", "Titular de la dependencia"), actor("custodian", "Resguardatario")),
    steps=(
        WorkflowStep("draft", "DRAFT", "Preparar vale", "patrimony"),
        WorkflowStep("submitted", "SUBMITTED", "Revisar asignación", "director"),
        WorkflowStep("authorized", "AUTHORIZED", "Autorizar resguardo", "director"),
        WorkflowStep("delivered", "PENDING_ACCEPTANCE", "Entregar el bien", "patrimony"),
        WorkflowStep("active", "ACTIVE", "Aceptar y firmar", "custodian", terminal=True),
        WorkflowStep("rejected", "REJECTED", "Rechazar con motivo", "custodian", terminal=True),
    ),
    transitions=(
        WorkflowTransition("draft", "submitted", "Enviar", permission="can_manage_custody"),
        WorkflowTransition("submitted", "authorized", "Autorizar", "success", permission="can_manage_custody"),
        WorkflowTransition("authorized", "delivered", "Registrar entrega", permission="can_manage_custody"),
        WorkflowTransition("delivered", "active", "Aceptar", "success", permission="can_accept_custody"),
        WorkflowTransition("delivered", "rejected", "No aceptar", "danger", permission="can_accept_custody"),
    ),
    primary_path=("draft", "submitted", "authorized", "delivered", "active"),
    notes=("El resguardo no es un préstamo.", "El servidor público debe aceptar su propio vale."),
)


LOAN_WORKFLOW = WorkflowDefinition(
    code="inventory.loan", name="Préstamo temporal",
    description="Entrega temporal sin cambiar la adscripción permanente del activo.",
    actors=(actor("origin", "Dependencia propietaria"), actor("destination", "Dependencia receptora"), actor("patrimony", "Control Patrimonial")),
    steps=(
        WorkflowStep("draft", "DRAFT", "Proponer préstamo", "origin"),
        WorkflowStep("reception", "PENDING_DEPARTMENT_ACCEPTANCE", "Aceptar recepción", "destination"),
        WorkflowStep("authorization", "PENDING_AUTHORIZATION", "Autorizar salida", "patrimony"),
        WorkflowStep("delivery", "AUTHORIZED", "Entregar con evidencia", "origin"),
        WorkflowStep("active", "ACTIVE", "Usar temporalmente", "destination"),
        WorkflowStep("return", "RETURN_REQUESTED", "Solicitar devolución", "origin"),
        WorkflowStep("closed", "RETURNED", "Recibir y cerrar", "origin", terminal=True),
        WorkflowStep("rejected", "REJECTED", "Rechazar solicitud", "destination", terminal=True),
    ),
    transitions=(
        WorkflowTransition("draft", "reception", "Enviar", permission="can_request_loans"),
        WorkflowTransition("reception", "authorization", "Aceptar", "success", permission="can_authorize_loans"),
        WorkflowTransition("reception", "rejected", "Rechazar", "danger", permission="can_authorize_loans"),
        WorkflowTransition("authorization", "delivery", "Autorizar", "success", permission="can_manage_loans"),
        WorkflowTransition("delivery", "active", "Entregar", permission="can_manage_loans"),
        WorkflowTransition("active", "return", "Pedir devolución", permission="can_manage_loans"),
        WorkflowTransition("return", "closed", "Recibir", "success", permission="can_manage_loans"),
    ),
    primary_path=("draft", "reception", "authorization", "delivery", "active", "return", "closed"),
    notes=("El bien sigue perteneciendo a la dependencia de origen.", "La devolución registra la condición final."),
)


MOVEMENT_WORKFLOW = WorkflowDefinition(
    code="inventory.movement", name="Movimiento patrimonial",
    description="Cambio permanente de ubicación, área, responsable o dependencia.",
    actors=(actor("origin", "Responsable de origen"), actor("destination", "Responsable de destino"), actor("patrimony", "Control Patrimonial")),
    steps=(
        WorkflowStep("draft", "DRAFT", "Solicitar movimiento", "origin"),
        WorkflowStep("origin", "PENDING_ORIGIN_APPROVAL", "Autorizar salida", "origin"),
        WorkflowStep("destination", "PENDING_DESTINATION_APPROVAL", "Aceptar destino", "destination"),
        WorkflowStep("approved", "APPROVED", "Validar expediente", "patrimony"),
        WorkflowStep("executed", "EXECUTED", "Actualizar adscripción", "patrimony", terminal=True),
        WorkflowStep("rejected", "REJECTED", "Rechazar con motivo", "destination", terminal=True),
    ),
    transitions=(
        WorkflowTransition("draft", "origin", "Enviar", permission="can_manage_movements"),
        WorkflowTransition("origin", "destination", "Origen autoriza", "success", permission="can_authorize_movements"),
        WorkflowTransition("destination", "approved", "Destino acepta", "success", permission="can_authorize_movements"),
        WorkflowTransition("destination", "rejected", "Destino rechaza", "danger", permission="can_authorize_movements"),
        WorkflowTransition("approved", "executed", "Ejecutar", "success", permission="can_manage_movements"),
    ),
    primary_path=("draft", "origin", "destination", "approved", "executed"),
    notes=("Una transferencia sí cambia la adscripción.", "Origen y destino dejan evidencia de su decisión."),
)


DISPOSAL_WORKFLOW = WorkflowDefinition(
    code="inventory.disposal", name="Baja patrimonial",
    description="Desincorporación formal sustentada con documentos y autorizaciones.",
    actors=(actor("department", "Dependencia solicitante"), actor("reviewer", "Revisor técnico o administrativo"), actor("patrimony", "Control Patrimonial")),
    steps=(
        WorkflowStep("draft", "DRAFT", "Integrar solicitud", "department"),
        WorkflowStep("review", "UNDER_REVIEW", "Revisar expediente", "reviewer"),
        WorkflowStep("evidence", "PENDING_EVIDENCE", "Agregar evidencia requerida", "department"),
        WorkflowStep("approved", "APPROVED", "Autorizar baja", "patrimony"),
        WorkflowStep("executed", "EXECUTED", "Ejecutar desincorporación", "patrimony", terminal=True),
        WorkflowStep("rejected", "REJECTED", "Rechazar con fundamento", "patrimony", terminal=True),
    ),
    transitions=(
        WorkflowTransition("draft", "review", "Enviar", permission="can_request_disposals"),
        WorkflowTransition("review", "evidence", "Solicitar documento", "warning", permission="can_manage_disposals"),
        WorkflowTransition("evidence", "review", "Completar expediente", permission="can_manage_documents"),
        WorkflowTransition("review", "approved", "Autorizar", "success", permission="can_authorize_disposals"),
        WorkflowTransition("review", "rejected", "Rechazar", "danger", permission="can_authorize_disposals"),
        WorkflowTransition("approved", "executed", "Ejecutar", "success", permission="can_execute_disposals"),
    ),
    primary_path=("draft", "review", "approved", "executed"),
    notes=("El dictamen técnico puede provenir de Helpdesk; Inventory conserva el documento final.", "Nunca se elimina físicamente el expediente del bien."),
)


AUDIT_WORKFLOW = WorkflowDefinition(
    code="inventory.physical_audit", name="Auditoría física",
    description="Levantamiento para comprobar existencia, ubicación y condición.",
    actors=(actor("patrimony", "Control Patrimonial"), actor("auditor", "Equipo auditor"), actor("department", "Dependencia revisada")),
    steps=(
        WorkflowStep("draft", "DRAFT", "Definir alcance", "patrimony"),
        WorkflowStep("frozen", "FROZEN", "Congelar población esperada", "patrimony"),
        WorkflowStep("active", "IN_PROGRESS", "Escanear bienes", "auditor"),
        WorkflowStep("reconciliation", "RECONCILIATION", "Aclarar diferencias", "department"),
        WorkflowStep("closed", "CLOSED", "Cerrar y emitir acta", "patrimony", terminal=True),
        WorkflowStep("cancelled", "CANCELLED", "Cancelar con motivo", "patrimony", terminal=True),
    ),
    transitions=(
        WorkflowTransition("draft", "frozen", "Generar fotografía", permission="can_manage_physical_audits"),
        WorkflowTransition("frozen", "active", "Iniciar", permission="can_manage_physical_audits"),
        WorkflowTransition("active", "reconciliation", "Terminar lecturas", permission="can_scan_physical_audits"),
        WorkflowTransition("reconciliation", "closed", "Conciliar y cerrar", "success", permission="can_manage_physical_audits"),
        WorkflowTransition("draft", "cancelled", "Cancelar", "danger", permission="can_manage_physical_audits"),
    ),
    primary_path=("draft", "frozen", "active", "reconciliation", "closed"),
    notes=("Sólo se auditan sedes y dependencias con bienes.", "Las diferencias generan acciones; no cambian datos silenciosamente."),
)


DOCUMENT_WORKFLOW = WorkflowDefinition(
    code="inventory.documents", name="Documentos y fotografías",
    description="Evidencia vinculada con el expediente o evento que la originó.",
    actors=(actor("operator", "Usuario autorizado"), actor("reviewer", "Validador documental")),
    steps=(
        WorkflowStep("select", "SELECT_OWNER", "Elegir expediente", "operator"),
        WorkflowStep("upload", "UPLOADED", "Cargar y describir archivo", "operator"),
        WorkflowStep("pending", "PENDING", "Esperar validación", "reviewer"),
        WorkflowStep("validated", "VALIDATED", "Validar evidencia", "reviewer", terminal=True),
        WorkflowStep("observed", "OBSERVED", "Corregir observación", "operator"),
        WorkflowStep("rejected", "REJECTED", "Rechazar archivo", "reviewer", terminal=True),
    ),
    transitions=(
        WorkflowTransition("select", "upload", "Seleccionar tipo", permission="can_manage_documents"),
        WorkflowTransition("upload", "pending", "Guardar", permission="can_manage_documents"),
        WorkflowTransition("pending", "validated", "Validar", "success", permission="can_validate_documents"),
        WorkflowTransition("pending", "observed", "Observar", "warning", permission="can_validate_documents"),
        WorkflowTransition("observed", "upload", "Reemplazar", permission="can_manage_documents"),
        WorkflowTransition("pending", "rejected", "Rechazar", "danger", permission="can_validate_documents"),
    ),
    primary_path=("select", "upload", "pending", "validated"),
    notes=("Cada archivo debe pertenecer al expediente correcto.", "La validación no sustituye la autorización del proceso."),
)


FINANCIAL_WORKFLOW = WorkflowDefinition(
    code="inventory.financial", name="Depreciación y conciliación",
    description="Cálculo, revisión contable, conciliación y exportación institucional.",
    actors=(actor("accounting", "Contabilidad"), actor("patrimony", "Control Patrimonial"), actor("system", "Axentra Inventory")),
    steps=(
        WorkflowStep("policy", "POLICY", "Configurar políticas", "accounting"),
        WorkflowStep("calculation", "CALCULATED", "Calcular periodo", "system"),
        WorkflowStep("review", "REVIEWED", "Revisar resultados", "accounting"),
        WorkflowStep("posting", "POSTED", "Cerrar depreciación", "accounting"),
        WorkflowStep("reconciliation", "RECONCILED", "Conciliar saldos", "patrimony"),
        WorkflowStep("export", "EXPORTED", "Generar reporte", "system", terminal=True),
    ),
    transitions=(
        WorkflowTransition("policy", "calculation", "Ejecutar", permission="can_run_depreciation"),
        WorkflowTransition("calculation", "review", "Presentar resultados", permission="can_view_financials"),
        WorkflowTransition("review", "posting", "Contabilizar", "success", permission="can_post_depreciation"),
        WorkflowTransition("posting", "reconciliation", "Comparar", permission="can_manage_reconciliation"),
        WorkflowTransition("reconciliation", "export", "Cerrar y exportar", "success", permission="can_export_reports"),
    ),
    primary_path=("policy", "calculation", "review", "posting", "reconciliation", "export"),
    notes=("Los periodos cerrados forman parte del histórico.", "Las diferencias deben resolverse antes del cierre."),
)


CATALOG_WORKFLOW = WorkflowDefinition(
    code="inventory.catalogs", name="Administración de catálogos",
    description="Configuración controlada de clasificaciones usadas en nuevas capturas.",
    actors=(actor("admin", "Administrador de Patrimonio"), actor("system", "Axentra Inventory")),
    steps=(
        WorkflowStep("review", "REVIEW", "Revisar necesidad", "admin"),
        WorkflowStep("create", "CREATE", "Capturar catálogo", "admin"),
        WorkflowStep("validate", "VALIDATE", "Validar relaciones", "system"),
        WorkflowStep("active", "ACTIVE", "Publicar para captura", "system", terminal=True),
        WorkflowStep("inactive", "INACTIVE", "Desactivar sin borrar", "admin", terminal=True),
    ),
    transitions=(
        WorkflowTransition("review", "create", "Autorizar captura", permission="can_manage_catalogs"),
        WorkflowTransition("create", "validate", "Guardar", permission="can_manage_catalogs"),
        WorkflowTransition("validate", "active", "Datos correctos", "success"),
        WorkflowTransition("active", "inactive", "Dejar de utilizar", "warning", permission="can_manage_catalogs"),
    ),
    primary_path=("review", "create", "validate", "active"),
    notes=("Desactivar conserva los expedientes históricos.", "Sólo Patrimonio y administradores gestionan catálogos."),
)


OPERATIONAL_WORKFLOWS = (
    CUSTODY_WORKFLOW, LOAN_WORKFLOW, MOVEMENT_WORKFLOW, DISPOSAL_WORKFLOW,
    AUDIT_WORKFLOW, DOCUMENT_WORKFLOW, FINANCIAL_WORKFLOW, CATALOG_WORKFLOW,
)

__all__ = ["OPERATIONAL_WORKFLOWS"]
