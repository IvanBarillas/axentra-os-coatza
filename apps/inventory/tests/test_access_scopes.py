from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.inventory.selectors import InventoryScope
from apps.inventory.views.access import asset_scope, intake_scope


def request_with(*permissions, root=False):
    return SimpleNamespace(
        user=SimpleNamespace(
            pk="user-1",
            is_superuser=root,
            is_manager=False,
        ),
        axentra_permissions_list=list(permissions),
        axentra_is_root=root,
    )


class InventoryAccessScopeTests(SimpleTestCase):
    def test_root_obtiene_alcance_global(self):
        request = request_with(root=True)
        self.assertEqual(asset_scope(request), (InventoryScope.GLOBAL, None))
        self.assertEqual(intake_scope(request), (InventoryScope.GLOBAL, None))

    @patch("apps.inventory.views.access.department_id", return_value="dep-1")
    def test_director_obtiene_alcance_de_dependencia(self, _department_id):
        request = request_with("can_approve_department_intake")
        self.assertEqual(
            asset_scope(request),
            (InventoryScope.DEPARTMENT, "dep-1"),
        )
        self.assertEqual(
            intake_scope(request),
            (InventoryScope.DEPARTMENT, "dep-1"),
        )

    def test_resguardatario_obtiene_solo_expedientes_propios(self):
        request = request_with("can_view_assets", "can_accept_custody")
        self.assertEqual(asset_scope(request), (InventoryScope.OWN, None))
        self.assertEqual(intake_scope(request), (InventoryScope.OWN, None))

    def test_patrimonio_obtiene_alcance_global(self):
        request = request_with("can_validate_patrimony_intake")
        self.assertEqual(asset_scope(request), (InventoryScope.GLOBAL, None))
        self.assertEqual(intake_scope(request), (InventoryScope.GLOBAL, None))

