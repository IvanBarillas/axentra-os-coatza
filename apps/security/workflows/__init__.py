"""Registro público e idempotente de las guías del Core."""

from apps.shared.workflows import register_workflow

from .accounts_workflow import ACCOUNTS_LIFECYCLE_WORKFLOW
from .organization_workflow import ORGANIZATION_STRUCTURE_WORKFLOW
from .security_workflow import SECURITY_ACCESS_WORKFLOW


CORE_WORKFLOWS = (
    SECURITY_ACCESS_WORKFLOW,
    ACCOUNTS_LIFECYCLE_WORKFLOW,
    ORGANIZATION_STRUCTURE_WORKFLOW,
)


def register_core_workflows():
    """Garantiza que todas las guías estén presentes en el registro en memoria."""

    for definition in CORE_WORKFLOWS:
        register_workflow(definition, replace=True)


register_core_workflows()


__all__ = [
    "ACCOUNTS_LIFECYCLE_WORKFLOW",
    "CORE_WORKFLOWS",
    "ORGANIZATION_STRUCTURE_WORKFLOW",
    "SECURITY_ACCESS_WORKFLOW",
    "register_core_workflows",
]
