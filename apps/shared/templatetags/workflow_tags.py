"""Tags reutilizables para diagramas y seguimiento de workflows."""

from django import template

from apps.shared.workflows import (
    WorkflowNotRegistered,
    build_workflow_context,
    get_workflow,
)


register = template.Library()


def _context(code, current_status=""):
    try:
        definition = get_workflow(code)
    except WorkflowNotRegistered as exc:
        return {
            "workflow_error": str(exc),
            "workflow_code": code,
        }

    return build_workflow_context(
        definition,
        current_status=str(current_status or ""),
    )


@register.inclusion_tag(
    "shared/workflows/overview.html",
    takes_context=True,
)
def workflow_overview(context, code, current_status="", compact=False):
    result = _context(code, current_status)
    result.update(
        {
            "request": context.get("request"),
            "workflow_compact": bool(compact),
        }
    )
    return result


@register.inclusion_tag(
    "shared/workflows/button.html",
    takes_context=True,
)
def workflow_button(context, code, current_status=""):
    result = _context(code, current_status)
    result["request"] = context.get("request")
    return result


@register.inclusion_tag("shared/workflows/diagram.html")
def workflow_diagram(code, current_status=""):
    return _context(code, current_status)


@register.inclusion_tag("shared/workflows/stepper.html")
def workflow_stepper(code, current_status=""):
    return _context(code, current_status)


@register.inclusion_tag("shared/workflows/help_drawer.html")
def workflow_help(code, current_status=""):
    return _context(code, current_status)


__all__ = [
    "workflow_button",
    "workflow_diagram",
    "workflow_help",
    "workflow_overview",
    "workflow_stepper",
]
