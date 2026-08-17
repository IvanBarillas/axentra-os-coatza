from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings

from apps.shared.module_sdk.catalog import available_module_catalog
from apps.shared.module_sdk.services import (
    module_center_cards,
    module_center_summary,
)


CUSTOM_CATALOG = (
    {
        "code": "custom_module",
        "name": "Módulo personalizado",
        "description": "Producto institucional de prueba.",
        "distribution": "axentra-custom",
        "dependencies": ("security",),
        "install_steps": ("Instalar distribución.",),
    },
)


class ModuleCatalogTests(SimpleTestCase):
    @override_settings(AXENTRA_MODULE_CATALOG=CUSTOM_CATALOG)
    def test_settings_define_the_distribution_catalog(self):
        catalog = {entry.code: entry for entry in available_module_catalog()}

        self.assertEqual(set(catalog), {"custom_module"})
        self.assertEqual(
            catalog["custom_module"].dependencies,
            ("security",),
        )

    @override_settings(AXENTRA_MODULE_CATALOG=())
    def test_core_has_no_domain_product_catalog_by_default(self):
        self.assertEqual(available_module_catalog(), ())


class ModuleCenterTests(TestCase):
    @override_settings(AXENTRA_MODULE_CATALOG=CUSTOM_CATALOG)
    def test_center_distinguishes_installed_and_configured_products(self):
        User = get_user_model()
        owner = User.objects.create_superuser(
            email="sdk-owner@example.test",
            password="Password-Seguro-2026!",
        )

        cards = module_center_cards(owner)
        by_code = {card["code"]: card for card in cards}
        summary = module_center_summary(cards)

        self.assertTrue(by_code["security"]["installed"])
        self.assertFalse(by_code["custom_module"]["installed"])
        self.assertTrue(by_code["custom_module"]["can_view_installation"])
        self.assertGreaterEqual(summary["installed"], 4)
        self.assertEqual(summary["available"], 1)
