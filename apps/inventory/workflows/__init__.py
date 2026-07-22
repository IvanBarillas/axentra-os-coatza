"""Registro público e idempotente de los workflows de Inventory."""

from apps.shared.workflows import register_workflow

from .intake_workflow import INVENTORY_INTAKE_WORKFLOW
from .operational_workflows import OPERATIONAL_WORKFLOWS


INVENTORY_WORKFLOWS = (INVENTORY_INTAKE_WORKFLOW, *OPERATIONAL_WORKFLOWS)


def register_inventory_workflows():
    for definition in INVENTORY_WORKFLOWS:
        register_workflow(definition, replace=True)


register_inventory_workflows()


__all__ = [
    "INVENTORY_INTAKE_WORKFLOW",
    "INVENTORY_WORKFLOWS",
    "register_inventory_workflows",
]
