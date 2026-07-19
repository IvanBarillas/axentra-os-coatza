"""Guía visual del proceso real de autorización de Axentra OS."""

from apps.shared.workflows import (
    WorkflowActor,
    WorkflowDefinition,
    WorkflowStep,
    WorkflowTransition,
)


SECURITY_ACCESS_WORKFLOW = WorkflowDefinition(
    code="security.access_resolution",
    name="¿Cómo decide Axentra si puedes realizar una acción?",
    description=(
        "Una guía sencilla para entender por qué una persona puede entrar, "
        "realizar una tarea o recibir un aviso de acceso restringido."
    ),
    version="1.0",
    actors=(
        WorkflowActor(
            "user",
            "Funcionario",
            "Persona que intenta entrar a un módulo o realizar una tarea.",
            "user-round",
        ),
        WorkflowActor(
            "identity",
            "Cuenta institucional",
            "Comprueba que la cuenta esté activa y disponible.",
            "fingerprint",
        ),
        WorkflowActor(
            "gate",
            "Control de acceso",
            "Comprueba si la persona y su dependencia pueden realizar la tarea.",
            "shield-check",
        ),
        WorkflowActor(
            "root",
            "Administrador general",
            "Puede atender casos excepcionales con una justificación.",
            "crown",
        ),
        WorkflowActor(
            "audit",
            "Bitácora",
            "Guarda evidencia de accesos, rechazos y excepciones.",
            "scroll-text",
        ),
    ),
    steps=(
        WorkflowStep("request", "ACCESS_REQUEST", "Solicitas entrar o realizar una acción", "user", icon="mouse-pointer-click"),
        WorkflowStep("identity", "IDENTITY_CHECK", "Comprueba que tu cuenta esté disponible", "identity", icon="fingerprint"),
        WorkflowStep("membership", "APP_MEMBERSHIP", "Revisa si tienes acceso al módulo", "gate", icon="badge-check"),
        WorkflowStep("permission", "FINE_PERMISSION", "Revisa si puedes realizar esa acción", "gate", icon="key-round"),
        WorkflowStep("capability", "DEPARTMENT_SCOPE", "Confirma si tu dependencia puede participar", "gate", icon="building-2"),
        WorkflowStep("bypass", "BYPASS", "Atiende una excepción justificada", "root", icon="shield-alert"),
        WorkflowStep("allowed", "ALLOWED", "Autoriza la acción", "gate", icon="check-circle-2", terminal=True),
        WorkflowStep("denied", "DENIED", "Explica por qué no puede continuar", "gate", icon="ban", terminal=True),
        WorkflowStep("audit", "AUDITED", "Guarda evidencia de lo ocurrido", "audit", icon="file-clock", terminal=True),
    ),
    transitions=(
        WorkflowTransition("request", "identity", "Revisar cuenta", explanation="Aunque ya haya iniciado sesión, Axentra confirma que la cuenta siga vigente."),
        WorkflowTransition("identity", "membership", "Cuenta activa", explanation="Se comprueba que tenga asignado el módulo que desea utilizar."),
        WorkflowTransition("identity", "denied", "Cuenta inactiva", "danger", explanation="La persona debe solicitar apoyo al administrador responsable."),
        WorkflowTransition("membership", "permission", "Acceso al módulo", explanation="Después se revisa la acción concreta que quiere realizar."),
        WorkflowTransition("membership", "denied", "Sin acceso al módulo", "danger"),
        WorkflowTransition("permission", "capability", "Acción permitida", permission="required_fine_permission"),
        WorkflowTransition("permission", "denied", "Acción no permitida", "danger"),
        WorkflowTransition("capability", "allowed", "Dependencia autorizada", "success", explanation="Algunas tareas sólo corresponden a determinadas dependencias."),
        WorkflowTransition("capability", "denied", "Fuera de su responsabilidad", "danger"),
        WorkflowTransition("identity", "bypass", "Caso excepcional", "bypass", explanation="Un administrador general puede intervenir, pero debe explicar el motivo."),
        WorkflowTransition("bypass", "allowed", "Continuar con acceso especial", "bypass"),
        WorkflowTransition("allowed", "audit", "Guardar resultado", "success"),
        WorkflowTransition("denied", "audit", "Guardar resultado", "warning"),
        WorkflowTransition("bypass", "audit", "Guardar excepción", "bypass"),
    ),
    primary_path=("request", "identity", "membership", "permission", "capability", "allowed", "audit"),
    notes=(
        "Tener acceso a un módulo no significa poder realizar todas sus acciones.",
        "Algunas acciones también dependen de la responsabilidad asignada a la dependencia.",
        "Todo acceso administrativo especial queda registrado para proteger al funcionario y a la institución.",
    ),
)


__all__ = ["SECURITY_ACCESS_WORKFLOW"]
