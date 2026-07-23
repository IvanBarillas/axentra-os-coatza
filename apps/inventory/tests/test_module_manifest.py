from django.test import SimpleTestCase
from django.urls import reverse

from apps.inventory.module_manifest import MODULE_MANIFEST
from apps.shared.module_sdk.contracts import ModuleKind
from apps.shared.module_sdk.registry import module_registry


class InventoryModuleManifestTests(SimpleTestCase):
    def test_inventory_declares_native_sdk_manifest(self):
        self.assertEqual(MODULE_MANIFEST.code, "inventory")
        self.assertEqual(MODULE_MANIFEST.kind, ModuleKind.SATELLITE)
        self.assertEqual(
            MODULE_MANIFEST.entry_url,
            "inventory:dashboard",
        )
        self.assertEqual(
            MODULE_MANIFEST.urlconf,
            "apps.inventory.urls.inventory_urls",
        )
        self.assertEqual(
            MODULE_MANIFEST.url_prefix,
            "app/inventory/",
        )
        self.assertEqual(
            MODULE_MANIFEST.dependencies,
            ("security", "accounts", "organigrama"),
        )
        self.assertTrue(MODULE_MANIFEST.can_disable)

    def test_inventory_is_discovered_by_sdk(self):
        module_registry.discover(force=True)

        manifest = module_registry.get("inventory")

        self.assertIsNotNone(manifest)
        self.assertEqual(manifest, MODULE_MANIFEST)
        self.assertEqual(
            reverse(manifest.entry_url),
            "/app/inventory/",
        )