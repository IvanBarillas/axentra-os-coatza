from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from django.test import SimpleTestCase

from apps.inventory.integrations.contracts import ExternalAssetActivity
from apps.inventory.integrations.external_asset_activity import (
    get_external_asset_activity,
)


class _Provider:
    available = True

    def list_asset_activity(self, *, asset_id, actor_id=None):
        return [
            ExternalAssetActivity(
                source_app="helpdesk",
                reference_id=uuid4(),
                activity_type="TECHNICAL_LOAN",
                activity_label="Préstamo técnico",
                folio="VPT-STI-TM001-26",
                title="Equipo temporal por reparación",
                status="ACTIVE",
                status_label="Pendiente de devolución",
                occurred_at=datetime(2026, 7, 31, 10, 0),
                blocks_asset_operations=True,
            )
        ]


class ExternalAssetActivityTests(SimpleTestCase):
    @patch(
        "apps.inventory.integrations.external_asset_activity.integration_registry.resolve",
        return_value=SimpleNamespace(available=False),
    )
    def test_inventory_funciona_sin_helpdesk(self, _resolve):
        result = get_external_asset_activity(uuid4(), actor_id=uuid4())

        self.assertFalse(result.integration_available)
        self.assertEqual(result.items, ())

    @patch(
        "apps.inventory.integrations.external_asset_activity.integration_registry.resolve",
        return_value=_Provider(),
    )
    def test_helpdesk_aporta_actividad_sin_crear_modelos_en_inventory(self, _resolve):
        result = get_external_asset_activity(uuid4(), actor_id=uuid4())

        self.assertTrue(result.integration_available)
        self.assertEqual(len(result.items), 1)
        self.assertTrue(result.has_blocking_activity)
        self.assertEqual(result.items[0].source_app, "helpdesk")
