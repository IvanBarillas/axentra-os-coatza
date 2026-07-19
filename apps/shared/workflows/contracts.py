"""Contratos inmutables para documentar flujos operativos de Axentra OS."""

from dataclasses import dataclass, field


WORKFLOW_STYLES = {
    "normal",
    "success",
    "warning",
    "danger",
    "bypass",
}


@dataclass(frozen=True, slots=True)
class WorkflowActor:
    code: str
    name: str
    description: str = ""
    icon: str = "user-round"


@dataclass(frozen=True, slots=True)
class WorkflowStep:
    code: str
    status: str
    name: str
    actor_code: str
    description: str = ""
    icon: str = "circle"
    terminal: bool = False


@dataclass(frozen=True, slots=True)
class WorkflowTransition:
    source: str
    target: str
    label: str
    style: str = "normal"
    permission: str = ""
    explanation: str = ""

    def __post_init__(self):
        if self.style not in WORKFLOW_STYLES:
            raise ValueError(f"Estilo de transición no válido: {self.style}")


@dataclass(frozen=True, slots=True)
class WorkflowDefinition:
    code: str
    name: str
    description: str
    actors: tuple[WorkflowActor, ...]
    steps: tuple[WorkflowStep, ...]
    transitions: tuple[WorkflowTransition, ...]
    primary_path: tuple[str, ...]
    version: str = "1.0"
    notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self):
        normalized_code = self.code.strip().lower()
        if not normalized_code:
            raise ValueError("El flujo debe tener un código.")
        object.__setattr__(self, "code", normalized_code)

        actor_codes = [actor.code for actor in self.actors]
        step_codes = [step.code for step in self.steps]
        statuses = [step.status for step in self.steps]

        if len(actor_codes) != len(set(actor_codes)):
            raise ValueError(f"El flujo {self.code} tiene actores duplicados.")
        if len(step_codes) != len(set(step_codes)):
            raise ValueError(f"El flujo {self.code} tiene pasos duplicados.")
        if len(statuses) != len(set(statuses)):
            raise ValueError(f"El flujo {self.code} tiene estados duplicados.")

        actor_set = set(actor_codes)
        step_set = set(step_codes)

        for step in self.steps:
            if step.actor_code not in actor_set:
                raise ValueError(
                    f"El paso {step.code} referencia un actor inexistente."
                )

        for transition in self.transitions:
            if transition.source not in step_set:
                raise ValueError(
                    f"La transición inicia en un paso inexistente: {transition.source}."
                )
            if transition.target not in step_set:
                raise ValueError(
                    f"La transición termina en un paso inexistente: {transition.target}."
                )

        if not self.primary_path:
            raise ValueError("El flujo requiere una ruta principal.")
        if not set(self.primary_path).issubset(step_set):
            raise ValueError("La ruta principal contiene pasos inexistentes.")

    @property
    def actor_map(self):
        return {actor.code: actor for actor in self.actors}

    @property
    def step_map(self):
        return {step.code: step for step in self.steps}

    @property
    def status_map(self):
        return {step.status: step for step in self.steps}


__all__ = [
    "WorkflowActor",
    "WorkflowDefinition",
    "WorkflowStep",
    "WorkflowTransition",
]
