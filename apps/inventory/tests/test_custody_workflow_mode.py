from django.test import SimpleTestCase, override_settings

from apps.inventory.workflows.custody_workflow import (
    CUSTODY_WORKFLOW_CONTROLLED,
    CUSTODY_WORKFLOW_SIMPLE,
    get_custody_workflow_mode,
    uses_simple_custody_workflow,
)


class CustodyWorkflowModeTests(SimpleTestCase):
    def test_simple_is_the_default_mode(self):
        with override_settings(INVENTORY_CUSTODY_WORKFLOW_MODE=""):
            self.assertEqual(
                get_custody_workflow_mode(),
                CUSTODY_WORKFLOW_SIMPLE,
            )
            self.assertTrue(uses_simple_custody_workflow())

    @override_settings(INVENTORY_CUSTODY_WORKFLOW_MODE="controlled")
    def test_controlled_mode_is_supported(self):
        self.assertEqual(
            get_custody_workflow_mode(),
            CUSTODY_WORKFLOW_CONTROLLED,
        )
        self.assertFalse(uses_simple_custody_workflow())

    @override_settings(INVENTORY_CUSTODY_WORKFLOW_MODE="UNKNOWN")
    def test_unknown_mode_falls_back_to_simple(self):
        self.assertEqual(
            get_custody_workflow_mode(),
            CUSTODY_WORKFLOW_SIMPLE,
        )
