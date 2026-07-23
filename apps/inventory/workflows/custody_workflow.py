"""Configuración desacoplada del flujo municipal de resguardos."""

import os

from django.conf import settings


CUSTODY_WORKFLOW_SIMPLE = "SIMPLE"
CUSTODY_WORKFLOW_CONTROLLED = "CONTROLLED"
VALID_CUSTODY_WORKFLOWS = {
    CUSTODY_WORKFLOW_SIMPLE,
    CUSTODY_WORKFLOW_CONTROLLED,
}


def get_custody_workflow_mode():
    value = str(
        getattr(
            settings,
            "INVENTORY_CUSTODY_WORKFLOW_MODE",
            os.getenv(
                "INVENTORY_CUSTODY_WORKFLOW_MODE",
                CUSTODY_WORKFLOW_SIMPLE,
            ),
        )
    ).strip().upper()
    if value not in VALID_CUSTODY_WORKFLOWS:
        return CUSTODY_WORKFLOW_SIMPLE
    return value


def uses_simple_custody_workflow():
    return get_custody_workflow_mode() == CUSTODY_WORKFLOW_SIMPLE


__all__ = [
    "CUSTODY_WORKFLOW_CONTROLLED",
    "CUSTODY_WORKFLOW_SIMPLE",
    "get_custody_workflow_mode",
    "uses_simple_custody_workflow",
]
