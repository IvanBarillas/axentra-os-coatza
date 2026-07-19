from django.template.loader import get_template
from django.test import SimpleTestCase

from apps.shared.workflows import get_workflow


class InventoryWorkflowTests(SimpleTestCase):
    def test_intake_workflow_is_registered(self):
        definition = get_workflow("inventory.asset_intake")
        self.assertEqual(definition.code, "inventory.asset_intake")

    def test_inventory_dashboard_compiles(self):
        template = get_template(
            "inventory/content/inventory_dashboard_content.html"
        )
        self.assertIsNotNone(template)
