from django.test import SimpleTestCase

from apps.inventory.permissions import InventoryPermissions


class InventoryDirectorPermissionsTests(SimpleTestCase):
    def test_director_solo_recibe_funciones_de_su_responsabilidad(self):
        permissions = set(InventoryPermissions.ROLE_MAPPING["director"])
        self.assertEqual(
            permissions,
            {
                "has_access_module",
                "can_view_dashboard",
                "can_view_assets",
                "can_approve_department_intake",
                "can_accept_custody",
                "can_request_loans",
                "can_authorize_loans",
            },
        )

    def test_director_no_opera_finanzas_movimientos_ni_bajas(self):
        permissions = set(InventoryPermissions.ROLE_MAPPING["director"])
        forbidden = {
            "can_view_financials",
            "can_export_reports",
            "can_authorize_movements",
            "can_request_disposals",
        }
        self.assertTrue(permissions.isdisjoint(forbidden))
