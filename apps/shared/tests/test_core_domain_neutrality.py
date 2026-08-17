from django.test import SimpleTestCase, override_settings

from apps.shared.module_sdk.catalog import available_module_catalog
from apps.shared.module_sdk.contracts import __all__ as contract_exports
from apps.shared.module_sdk.registry import BUILTIN_MODULES


class CoreDomainNeutralityTests(SimpleTestCase):
    @override_settings(AXENTRA_MODULE_CATALOG=())
    def test_core_catalog_is_empty_by_default(self):
        self.assertEqual(available_module_catalog(), ())

    def test_builtin_modules_only_contain_core_capabilities(self):
        self.assertEqual(
            {manifest.code for manifest in BUILTIN_MODULES},
            {"security", "configuration", "accounts", "organigrama"},
        )

    def test_core_contracts_do_not_export_asset_domain_types(self):
        self.assertNotIn("ExternalAssetActivity", contract_exports)
        self.assertNotIn("ExternalAssetActivityCollection", contract_exports)
