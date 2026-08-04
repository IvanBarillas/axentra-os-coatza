from django.test import SimpleTestCase

from apps.inventory.forms import (
    AssetLocationChangeForm,
    AssetReassignmentForm,
    AssetTransferForm,
)


class MovementFormStructureTests(SimpleTestCase):
    def test_location_change_keeps_department_out_of_user_input(self):
        form = AssetLocationChangeForm()

        self.assertIn("site_id", form.fields)
        self.assertIn("area_id", form.fields)
        self.assertNotIn("department_id", form.fields)
        self.assertNotIn("user_id", form.fields)

    def test_reassignment_only_requests_asset_and_new_custodian(self):
        form = AssetReassignmentForm()

        self.assertIn("asset_id", form.fields)
        self.assertIn("user_id", form.fields)
        self.assertNotIn("site_id", form.fields)
        self.assertNotIn("department_id", form.fields)
        self.assertNotIn("area_id", form.fields)

    def test_transfer_keeps_complete_destination_context(self):
        form = AssetTransferForm()

        self.assertIn("destination_site_id", form.fields)
        self.assertIn("destination_department_id", form.fields)
        self.assertIn("destination_area_id", form.fields)
        self.assertIn("destination_custodian_id", form.fields)
        self.assertTrue(form.fields["destination_department_id"].required)
        self.assertFalse(form.fields["destination_area_id"].required)
        self.assertFalse(form.fields["destination_custodian_id"].required)
