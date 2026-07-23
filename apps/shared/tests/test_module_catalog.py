from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings

from apps.shared.module_sdk.catalog import available_module_catalog
from apps.shared.module_sdk.services import (
    module_center_cards,
    module_center_summary,
)


class ModuleCatalogTests(SimpleTestCase):
    @override_settings(
        AXENTRA_MODULE_CATALOG=(
            {
                "code": "custom_module",
                "name": "Módulo personalizado",
                "description": "Producto institucional de prueba.",
                "distribution": "axentra-custom",
                "dependencies": ("security",),
                "install_steps": ("Instalar distribución.",),
            },
        )
    )
    def test_settings_extend_the_default_catalog(self):
        catalog = {entry.code: entry for entry in available_module_catalog()}
        self.assertIn("inventory", catalog)
        self.assertIn("helpdesk", catalog)
        self.assertIn("custom_module", catalog)
        self.assertEqual(
            catalog["custom_module"].dependencies,
            ("security",),
        )


class ModuleCenterTests(TestCase):
    def test_center_distinguishes_installed_and_available_products(self):
        User = get_user_model()
        owner = User.objects.create_superuser(
            email="sdk-owner@example.test",
            password="Password-Seguro-2026!",
        )

        cards = module_center_cards(owner)
        by_code = {card["code"]: card for card in cards}
        summary = module_center_summary(cards)

        self.assertTrue(by_code["security"]["installed"])
        self.assertFalse(by_code["helpdesk"]["installed"])
        self.assertTrue(by_code["helpdesk"]["can_view_installation"])
        self.assertGreaterEqual(summary["installed"], 4)
        self.assertGreaterEqual(summary["available"], 1)
