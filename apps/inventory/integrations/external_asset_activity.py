"""Puente opcional entre el expediente patrimonial y otros módulos.

Inventory no importa Helpdesk ni conoce sus modelos. El proveedor futuro de
Helpdesk se registrará como ``helpdesk.asset_activity`` en el SDK modular.
"""

import logging
from uuid import UUID

from apps.inventory.integrations.contracts import ExternalAssetActivityCollection
from apps.shared.module_sdk.integrations import integration_registry


logger = logging.getLogger(__name__)
INTEGRATION_NAME = "helpdesk.asset_activity"


def get_external_asset_activity(
    asset_id: UUID,
    *,
    actor_id: UUID | None = None,
) -> ExternalAssetActivityCollection:
    """Consulta actividad externa sin convertir Helpdesk en dependencia."""

    provider = integration_registry.resolve(INTEGRATION_NAME)
    if not provider.available:
        return ExternalAssetActivityCollection()

    try:
        result = provider.list_asset_activity(
            asset_id=asset_id,
            actor_id=actor_id,
        )
    except Exception:  # La falla de un satélite opcional no derriba Inventory.
        logger.exception(
            "No fue posible consultar actividad externa para el activo %s.",
            asset_id,
        )
        return ExternalAssetActivityCollection(
            integration_available=True,
            message="La vinculación con soporte técnico no está disponible temporalmente.",
        )

    if isinstance(result, ExternalAssetActivityCollection):
        return result

    return ExternalAssetActivityCollection(
        integration_available=True,
        items=tuple(result or ()),
    )


__all__ = ["INTEGRATION_NAME", "get_external_asset_activity"]
