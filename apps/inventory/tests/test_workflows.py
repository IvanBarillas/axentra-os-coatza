from django.template.loader import get_template
from django.test import SimpleTestCase

from apps.shared.workflows import get_workflow


class InventoryWorkflowTests(SimpleTestCase):
    def test_inventory_workflows_are_registered(self):
        expected = {
            "inventory.asset_intake",
            "inventory.custody",
            "inventory.loan",
            "inventory.movement",
            "inventory.disposal",
            "inventory.physical_audit",
            "inventory.documents",
            "inventory.financial",
            "inventory.catalogs",
        }
        registered = {get_workflow(code).code for code in expected}
        self.assertEqual(registered, expected)

    def test_inventory_dashboard_compiles(self):
        template = get_template(
            "inventory/content/inventory_dashboard_content.html"
        )
        self.assertIsNotNone(template)

    def test_inventory_help_templates_compile(self):
        self.assertIsNotNone(
            get_template("inventory/content/help_content.html")
        )
        self.assertIsNotNone(
            get_template("inventory/content/help_detail_content.html")
        )
