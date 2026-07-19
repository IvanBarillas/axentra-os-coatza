"""Registro en memoria de definiciones de workflow."""

from threading import RLock

from .contracts import WorkflowDefinition


class WorkflowAlreadyRegistered(RuntimeError):
    pass


class WorkflowNotRegistered(LookupError):
    pass


class WorkflowRegistry:
    def __init__(self):
        self._definitions: dict[str, WorkflowDefinition] = {}
        self._lock = RLock()

    @staticmethod
    def normalize_code(code: str) -> str:
        return str(code or "").strip().lower()

    def register(
        self,
        definition: WorkflowDefinition,
        *,
        replace: bool = False,
    ) -> WorkflowDefinition:
        code = self.normalize_code(definition.code)
        with self._lock:
            if code in self._definitions and not replace:
                raise WorkflowAlreadyRegistered(
                    f"El workflow [{code}] ya fue registrado."
                )
            self._definitions[code] = definition
        return definition

    def get(self, code: str) -> WorkflowDefinition:
        normalized = self.normalize_code(code)
        try:
            return self._definitions[normalized]
        except KeyError as exc:
            raise WorkflowNotRegistered(
                f"El workflow [{normalized}] no está registrado."
            ) from exc

    def all(self) -> tuple[WorkflowDefinition, ...]:
        return tuple(
            self._definitions[key]
            for key in sorted(self._definitions)
        )

    def unregister(self, code: str) -> None:
        with self._lock:
            self._definitions.pop(self.normalize_code(code), None)

    def clear(self) -> None:
        with self._lock:
            self._definitions.clear()


workflow_registry = WorkflowRegistry()


def register_workflow(
    definition: WorkflowDefinition,
    *,
    replace: bool = False,
) -> WorkflowDefinition:
    return workflow_registry.register(definition, replace=replace)


def get_workflow(code: str) -> WorkflowDefinition:
    return workflow_registry.get(code)


__all__ = [
    "WorkflowAlreadyRegistered",
    "WorkflowNotRegistered",
    "WorkflowRegistry",
    "get_workflow",
    "register_workflow",
    "workflow_registry",
]
