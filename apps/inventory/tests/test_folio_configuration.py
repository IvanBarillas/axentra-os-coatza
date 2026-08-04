from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from django.test import SimpleTestCase

from apps.inventory.models import InventoryAssetTypeCode
from apps.inventory.services.exceptions import InventoryConfigurationError
from apps.inventory.services.folio_service import _build_scope


class FolioMunicipalityConfigurationTests(SimpleTestCase):
    def _policy(self, municipality_code="039"):
        return SimpleNamespace(
            pk=uuid4(),
            municipality_code=municipality_code,
            progressive_length=4,
        )

    def _tenant(self, municipality_code="039", *, municipality=True):
        identity = None
        if municipality:
            identity = SimpleNamespace(
                id=uuid4(),
                code=municipality_code,
                is_available=True,
            )
        return SimpleNamespace(
            municipality=identity,
            is_available=True,
        )

    def _department(self, code="001"):
        return SimpleNamespace(
            id=uuid4(),
            normalized_code=code,
        )

    def _expenditure(self):
        return SimpleNamespace(code="5151")

    @patch("apps.inventory.services.folio_service.get_department")
    @patch("apps.inventory.services.folio_service.get_active_tenant")
    def test_accepts_equivalent_normalized_municipality_codes(
        self,
        get_active_tenant,
        get_department,
    ):
        get_active_tenant.return_value = self._tenant("39")
        get_department.return_value = self._department()

        scope = _build_scope(
            policy=self._policy("039"),
            fiscal_year=2026,
            expenditure_object=self._expenditure(),
            department_id=uuid4(),
            asset_type_code=InventoryAssetTypeCode.BM,
        )

        self.assertEqual(scope.municipality_code, "039")

    @patch("apps.inventory.services.folio_service.get_department")
    @patch("apps.inventory.services.folio_service.get_active_tenant")
    def test_rejects_municipality_code_mismatch(
        self,
        get_active_tenant,
        get_department,
    ):
        get_active_tenant.return_value = self._tenant("040")
        get_department.return_value = self._department()

        with self.assertRaisesMessage(
            InventoryConfigurationError,
            "no coincide con la configuración institucional",
        ):
            _build_scope(
                policy=self._policy("039"),
                fiscal_year=2026,
                expenditure_object=self._expenditure(),
                department_id=uuid4(),
                asset_type_code=InventoryAssetTypeCode.BM,
            )

    @patch("apps.inventory.services.folio_service.get_department")
    @patch("apps.inventory.services.folio_service.get_active_tenant")
    def test_rejects_tenant_without_municipality(
        self,
        get_active_tenant,
        get_department,
    ):
        get_active_tenant.return_value = self._tenant(municipality=False)
        get_department.return_value = self._department()

        with self.assertRaisesMessage(
            InventoryConfigurationError,
            "no tiene un municipio asociado",
        ):
            _build_scope(
                policy=self._policy(),
                fiscal_year=2026,
                expenditure_object=self._expenditure(),
                department_id=uuid4(),
                asset_type_code=InventoryAssetTypeCode.BM,
            )
