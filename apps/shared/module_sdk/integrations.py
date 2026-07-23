from typing import Protocol, runtime_checkable


@runtime_checkable
class OptionalIntegration(Protocol):
    """Contrato mínimo para integraciones opcionales entre satélites."""

    @property
    def available(self) -> bool: ...


class NullIntegration:
    available = False

    def __getattr__(self, name):
        def empty(*args, **kwargs):
            return None
        return empty


class IntegrationRegistry:
    def __init__(self):
        self._providers = {}

    def register(self, name, provider, *, replace=False):
        key = str(name).strip().lower()
        if key in self._providers and not replace:
            raise ValueError(f"La integración [{key}] ya tiene proveedor.")
        self._providers[key] = provider

    def resolve(self, name):
        provider = self._providers.get(str(name).strip().lower())
        if provider is None:
            return NullIntegration()
        return provider() if isinstance(provider, type) else provider


integration_registry = IntegrationRegistry()


__all__ = [
    "IntegrationRegistry",
    "NullIntegration",
    "OptionalIntegration",
    "integration_registry",
]
