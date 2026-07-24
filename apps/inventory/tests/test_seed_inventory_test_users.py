from django.test import SimpleTestCase

from apps.inventory.management.commands.seed_inventory_test_users import (
    ROLE_FIXTURES,
)
from apps.inventory.permissions import InventoryPermissions


class InventoryTestUserSeedTests(SimpleTestCase):
    def test_there_is_one_fixture_for_every_inventory_role(self):
        fixture_roles = [fixture.role for fixture in ROLE_FIXTURES]
        self.assertEqual(len(fixture_roles), len(set(fixture_roles)))
        self.assertEqual(
            set(fixture_roles),
            set(InventoryPermissions.ROLE_MAPPING),
        )

    def test_every_test_identity_has_a_unique_email(self):
        emails = [fixture.email for fixture in ROLE_FIXTURES]
        self.assertEqual(len(emails), len(set(emails)))
        self.assertTrue(
            all(email.endswith("@axentra.com.mx") for email in emails)
        )
        self.assertTrue(all(".test" not in email for email in emails))

    def test_every_role_uses_a_declared_permission_snapshot(self):
        for fixture in ROLE_FIXTURES:
            self.assertIn(
                fixture.role,
                InventoryPermissions.ROLE_MAPPING,
            )
