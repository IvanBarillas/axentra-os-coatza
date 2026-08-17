from django.conf import settings
from django.test import SimpleTestCase

from core.settings import base as core_base


class CoatzaCompositionTests(SimpleTestCase):
    def test_core_does_not_install_inventory(self):
        self.assertNotIn(
            "apps.inventory.apps.InventoryConfig",
            core_base.INSTALLED_APPS,
        )

    def test_coatza_installs_inventory(self):
        self.assertIn(
            "apps.inventory.apps.InventoryConfig",
            settings.INSTALLED_APPS,
        )

    def test_coatza_owns_root_urlconf(self):
        self.assertEqual(settings.ROOT_URLCONF, "coatza.urls")
