"""Conversión segura de definiciones a Mermaid y contextos de interfaz."""

import re

from .contracts import WorkflowDefinition


def _text(value: str) -> str:
    normalized = re.sub(r"\s+", " ", str(value or "").strip())
    return (
        normalized
        .replace("&", "y")
        .replace('"', "'")
        .replace("<", "")
        .replace(">", "")
    )


def build_mermaid_source(
    definition: WorkflowDefinition,
    *,
    current_status: str = "",
) -> str:
    actor_map = definition.actor_map
    current_step = definition.status_map.get(current_status)
    node_ids = {
        step.code: f"S{index}"
        for index, step in enumerate(definition.steps)
    }

    lines = ["flowchart TD"]
    for step in definition.steps:
        actor = actor_map[step.actor_code]
        label = f"{_text(step.name)} - {_text(actor.name)}"
        lines.append(f'    {node_ids[step.code]}["{label}"]')

    for transition in definition.transitions:
        source = node_ids[transition.source]
        target = node_ids[transition.target]
        label = _text(transition.label)
        if transition.style == "bypass":
            lines.append(f'    {source} -. "{label}" .-> {target}')
        else:
            lines.append(f'    {source} -->|"{label}"| {target}')

    lines.extend(
        [
            "    classDef current fill:#dbeafe,stroke:#2563eb,stroke-width:3px,color:#0f172a",
            "    classDef terminal fill:#dcfce7,stroke:#16a34a,stroke-width:2px,color:#14532d",
        ]
    )

    terminal_nodes = [
        node_ids[step.code]
        for step in definition.steps
        if step.terminal
    ]
    if terminal_nodes:
        lines.append(f"    class {','.join(terminal_nodes)} terminal")
    if current_step:
        lines.append(f"    class {node_ids[current_step.code]} current")

    return "\n".join(lines)


def build_stepper(
    definition: WorkflowDefinition,
    *,
    current_status: str = "",
):
    step_map = definition.step_map
    current_step = definition.status_map.get(current_status)
    current_code = current_step.code if current_step else ""
    current_index = (
        definition.primary_path.index(current_code)
        if current_code in definition.primary_path
        else -1
    )

    result = []
    for index, code in enumerate(definition.primary_path):
        step = step_map[code]
        if current_index < 0:
            state = "guide"
        elif index < current_index:
            state = "completed"
        elif index == current_index:
            state = "current"
        else:
            state = "pending"
        result.append({"step": step, "state": state})

    if current_step and current_step.code not in definition.primary_path:
        result.append({"step": current_step, "state": "current"})
    return tuple(result)


def build_workflow_context(
    definition: WorkflowDefinition,
    *,
    current_status: str = "",
):
    return {
        "workflow": definition,
        "workflow_current_status": current_status,
        "workflow_mermaid": build_mermaid_source(
            definition,
            current_status=current_status,
        ),
        "workflow_stepper_items": build_stepper(
            definition,
            current_status=current_status,
        ),
    }


__all__ = [
    "build_mermaid_source",
    "build_stepper",
    "build_workflow_context",
]
