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
                "can_view_department_intake_inbox",
                "can_accept_custody",
                "can_view_own_custody_tasks",
                "can_request_loans",
                "can_authorize_loans",
                "can_authorize_movements",
                "can_request_disposals",
                "can_confirm_department_disposal",
            },
        )

    def test_director_no_administra_finanzas_movimientos_ni_bajas_globales(self):
        permissions = set(InventoryPermissions.ROLE_MAPPING["director"])
        forbidden = {
            "can_view_financials",
            "can_export_reports",
            "can_manage_movements",
            "can_manage_disposals",
            "can_review_patrimony_disposal",
            "can_finalize_disposal",
        }
        self.assertTrue(permissions.isdisjoint(forbidden))

    def test_director_puede_autorizar_movimientos_de_su_dependencia(self):
        permissions = set(InventoryPermissions.ROLE_MAPPING["director"])
        self.assertIn("can_authorize_movements", permissions)
        self.assertNotIn("can_manage_movements", permissions)

    def test_patrimonio_no_sustituye_al_dictaminador_tecnico(self):
        permissions = set(InventoryPermissions.ROLE_MAPPING["admin_patrimonio"])
        self.assertIn("can_review_patrimony_disposal", permissions)
        self.assertNotIn("can_review_technical_disposal", permissions)
