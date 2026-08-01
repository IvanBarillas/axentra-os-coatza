from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class ModuleKind(StrEnum):
    CORE = "CORE"
    SATELLITE = "SATELLITE"


class ModuleHealth(StrEnum):
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    UNAVAILABLE = "UNAVAILABLE"
    DISABLED = "DISABLED"


@dataclass(frozen=True, slots=True)
class ExternalAssetActivity:
    """Evento de otro módulo vinculado a un activo mediante UUID."""

    source_app: str
    reference_id: UUID
    activity_type: str
    activity_label: str
    folio: str
    title: str
    status: str
    status_label: str
    occurred_at: datetime | None = None
    due_at: datetime | None = None
    detail_url: str = ""
    summary: str = ""
    blocks_asset_operations: bool = False


@dataclass(frozen=True, slots=True)
class ExternalAssetActivityCollection:
    """Resultado seguro de una integración opcional de expediente."""

    integration_available: bool = False
    items: tuple[ExternalAssetActivity, ...] = field(default_factory=tuple)
    message: str = ""

    @property
    def blocking_items(self) -> tuple[ExternalAssetActivity, ...]:
        return tuple(item for item in self.items if item.blocks_asset_operations)

    @property
    def has_blocking_activity(self) -> bool:
        return bool(self.blocking_items)


@dataclass(frozen=True, slots=True)
class ModuleManifest:
    code: str
    name: str
    description: str
    entry_url: str
    urlconf: str = ""
    url_prefix: str = ""
    version: str = "1.0.0"
    icon: str = "blocks"
    kind: ModuleKind = ModuleKind.SATELLITE
    dependencies: tuple[str, ...] = field(default_factory=tuple)
    optional_integrations: tuple[str, ...] = field(default_factory=tuple)
    default_enabled: bool = False
    can_disable: bool = True

    def __post_init__(self):
        code = str(self.code).strip().lower()
        if not code or not code.replace("_", "").replace("-", "").isalnum():
            raise ValueError("El módulo requiere un código técnico válido.")
        if code in self.dependencies:
            raise ValueError("Un módulo no puede depender de sí mismo.")
        object.__setattr__(self, "code", code)
        object.__setattr__(
            self,
            "dependencies",
            tuple(str(item).strip().lower() for item in self.dependencies),
        )
        object.__setattr__(
            self,
            "optional_integrations",
            tuple(str(item).strip().lower() for item in self.optional_integrations),
        )


@dataclass(frozen=True, slots=True)
class ModuleRuntimeStatus:
    manifest: ModuleManifest
    installed: bool
    enabled: bool
    health: ModuleHealth
    message: str = ""
    missing_dependencies: tuple[str, ...] = field(default_factory=tuple)

    @property
    def available(self):
        return self.installed and self.enabled and self.health == ModuleHealth.HEALTHY


__all__ = [
    "ExternalAssetActivity",
    "ExternalAssetActivityCollection",
    "ModuleHealth",
    "ModuleKind",
    "ModuleManifest",
    "ModuleRuntimeStatus",
]
