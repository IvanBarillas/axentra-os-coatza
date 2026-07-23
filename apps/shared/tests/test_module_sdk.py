from types import SimpleNamespace
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase, TestCase

from apps.security.decorators import axentra_module_gate
from apps.security.models import AppModule
from apps.shared.module_sdk import (
    ModuleHealth,
    ModuleManifest,
    ModuleRuntimeStatus,
)
from apps.shared.module_sdk.services import sync_installed_modules


class ModuleManifestTests(SimpleTestCase):
    def test_manifest_normalizes_code_and_dependencies(self):
        manifest = ModuleManifest(
            code=" HELP_DESK ",
            name="Mesa de ayuda",
            description="Tickets",
            entry_url="helpdesk:dashboard",
            dependencies=(" SECURITY ",),
        )
        self.assertEqual(manifest.code, "help_desk")
        self.assertEqual(manifest.dependencies, ("security",))

    def test_disabled_module_blocks_even_root(self):
        manifest = ModuleManifest(
            code="demo", name="Demo", description="Demo",
            entry_url="index_hub",
        )
        runtime = ModuleRuntimeStatus(
            manifest=manifest,
            installed=True,
            enabled=False,
            health=ModuleHealth.DISABLED,
            message="Módulo deshabilitado.",
        )
        request = RequestFactory().get("/demo/", HTTP_HX_REQUEST="true")
        request.user = SimpleNamespace(
            is_authenticated=True,
            is_active=True,
            is_deleted=False,
            is_manager=True,
            is_superuser=True,
        )

        @axentra_module_gate("demo")
        def protected_view(request):
            raise AssertionError("La vista no debe ejecutarse.")

        with patch(
            "apps.shared.module_sdk.services.get_module_runtime_status",
            return_value=runtime,
        ):
            response = protected_view(request)
        self.assertEqual(response.status_code, 503)


class ModuleProvisioningTests(TestCase):
    def test_sync_does_not_reactivate_disabled_module(self):
        manifest = ModuleManifest(
            code="demo_satellite",
            name="Satélite de prueba",
            description="Módulo desactivable usado por la prueba.",
            entry_url="index_hub",
            default_enabled=True,
            can_disable=True,
        )
        AppModule.objects.create(
            slug=manifest.code,
            name=manifest.name,
            description="",
            is_active=False,
        )
        with patch(
            "apps.shared.module_sdk.services.module_registry.discover",
            return_value=(manifest,),
        ):
            sync_installed_modules()
        module = AppModule.objects.get(slug=manifest.code)
        self.assertFalse(module.is_active)
