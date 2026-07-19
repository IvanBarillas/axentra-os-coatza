"""Guía visual del ciclo de vida de funcionarios y cuentas."""

from apps.shared.workflows import (
    WorkflowActor,
    WorkflowDefinition,
    WorkflowStep,
    WorkflowTransition,
)


ACCOUNTS_LIFECYCLE_WORKFLOW = WorkflowDefinition(
    code="accounts.user_lifecycle",
    name="¿Cómo se habilita una cuenta institucional?",
    description=(
        "Muestra qué debe ocurrir desde que ingresa un funcionario hasta que "
        "puede trabajar en Axentra, y qué pasa cuando cambia o deja el cargo."
    ),
    version="1.0",
    actors=(
        WorkflowActor("rh", "Recursos Humanos", "Crea y mantiene la identidad laboral.", "users-round"),
        WorkflowActor("directory", "Directorio institucional", "Indica dónde y para qué área trabaja la persona.", "contact-round"),
        WorkflowActor("security", "Seguridad", "Define a qué módulos puede entrar y prepara su acceso.", "shield-check"),
        WorkflowActor("user", "Funcionario", "Utiliza la cuenta y actualiza su contraseña cuando corresponde.", "user-round-check"),
        WorkflowActor("audit", "Bitácora", "Guarda evidencia de los cambios importantes.", "scroll-text"),
    ),
    steps=(
        WorkflowStep("create", "USER_CREATED", "Registrar al funcionario", "rh", icon="user-plus"),
        WorkflowStep("profile", "PROFILE_CREATED", "Completar su expediente laboral", "directory", icon="contact"),
        WorkflowStep("assignment", "ORGANIZATIONAL_ASSIGNMENT", "Indicar dónde trabaja", "directory", icon="network"),
        WorkflowStep("roles", "ROLES_ASSIGNED", "Definir los módulos que necesita", "security", icon="shield-keyhole"),
        WorkflowStep("credentials", "CREDENTIALS_DELIVERED", "Entregar el acceso inicial", "security", icon="key-round"),
        WorkflowStep("password", "PASSWORD_CHANGED", "Crear su contraseña personal", "user", icon="lock-keyhole"),
        WorkflowStep("active", "ACTIVE", "Cuenta lista para trabajar", "user", icon="badge-check", terminal=True),
        WorkflowStep("suspended", "SUSPENDED", "Suspender temporalmente", "security", icon="user-round-x", terminal=True),
        WorkflowStep("deleted", "LOGICALLY_DELETED", "Registrar la baja", "rh", icon="archive-x", terminal=True),
        WorkflowStep("audit", "AUDITED", "Guardar evidencia", "audit", icon="file-clock", terminal=True),
    ),
    transitions=(
        WorkflowTransition("create", "profile", "Completar datos", permission="can_create_user"),
        WorkflowTransition("profile", "assignment", "Asignar ubicación y área", permission="can_edit_user"),
        WorkflowTransition("assignment", "roles", "Seleccionar herramientas", explanation="Sólo se habilitan los módulos necesarios para su trabajo."),
        WorkflowTransition("roles", "credentials", "Preparar acceso", permission="can_change_password"),
        WorkflowTransition("credentials", "password", "Primer ingreso"),
        WorkflowTransition("password", "active", "Contraseña lista", "success"),
        WorkflowTransition("active", "suspended", "Suspender", "warning", permission="can_edit_user"),
        WorkflowTransition("suspended", "active", "Reactivar", "success", permission="can_edit_user"),
        WorkflowTransition("active", "deleted", "Registrar baja", "danger", permission="can_delete_user"),
        WorkflowTransition("suspended", "deleted", "Confirmar baja", "danger", permission="can_delete_user"),
        WorkflowTransition("roles", "audit", "Guardar asignaciones"),
        WorkflowTransition("credentials", "audit", "Guardar entrega de acceso", "warning"),
        WorkflowTransition("deleted", "audit", "Guardar baja", "warning"),
    ),
    primary_path=("create", "profile", "assignment", "roles", "credentials", "password", "active"),
    notes=(
        "La baja conserva el historial laboral y las acciones realizadas por el funcionario.",
        "La ubicación de trabajo y los módulos autorizados se administran por separado.",
        "Ningún administrador puede ver la contraseña personal del funcionario.",
    ),
)


__all__ = ["ACCOUNTS_LIFECYCLE_WORKFLOW"]
