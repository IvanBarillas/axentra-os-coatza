from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from django.test import SimpleTestCase

from apps.inventory.views.registry_views import _disposal_context


class _Approvals:
    def __init__(self, pending):
        self.pending = pending

    def filter(self, **_kwargs):
        return self

    def exists(self):
        return self.pending


class DisposalButtonVisibilityTests(SimpleTestCase):
    def _request(self, user_id, *permissions, root=False):
        return SimpleNamespace(
            user=SimpleNamespace(pk=user_id),
            axentra_permissions_list=list(permissions),
            axentra_is_root=root,
        )

    def _disposal(self, requested_by_id, status, pending=True):
        return SimpleNamespace(
            requested_by_id=requested_by_id,
            status=status,
            asset=SimpleNamespace(current_dependencia_id=uuid4()),
            approvals=_Approvals(pending),
        )

    @patch("apps.inventory.views.registry_views.core_directory.user_can_approve_department")
    def test_solicitante_puede_enviar_su_borrador(self, authority):
        authority.return_value = SimpleNamespace(allowed=False)
        user_id = uuid4()
        context = _disposal_context(
            self._request(user_id, "can_request_disposals"),
            self._disposal(user_id, "DRAFT", pending=False),
        )
        self.assertTrue(context["can_submit_disposal"])
        self.assertTrue(context["can_cancel_disposal"])
        self.assertFalse(context["can_execute_disposal"])

    @patch("apps.inventory.views.registry_views.core_directory.user_can_approve_department")
    def test_director_no_necesita_confirmar_despues_del_oficio(self, authority):
        authority.return_value = SimpleNamespace(allowed=True)
        context = _disposal_context(
            self._request(
                uuid4(),
                "can_request_disposals",
                "can_confirm_department_disposal",
            ),
            self._disposal(uuid4(), "ADMINISTRATIVE_REVIEW"),
        )
        self.assertFalse(context["can_resolve_disposal"])
        self.assertFalse(context["can_finalize_disposal"])

    @patch("apps.inventory.views.registry_views.core_directory.user_can_approve_department")
    def test_ejecutor_solo_ve_ejecucion_cuando_esta_aprobada(self, authority):
        authority.return_value = SimpleNamespace(allowed=False)
        context = _disposal_context(
            self._request(uuid4(), "can_execute_disposals"),
            self._disposal(uuid4(), "APPROVED", pending=False),
        )
        self.assertTrue(context["can_execute_disposal"])
        self.assertFalse(context["can_cancel_disposal"])

    @patch("apps.inventory.views.registry_views.AssetLoan.objects")
    @patch("apps.inventory.views.registry_views.CustodyDocument.objects")
    @patch("apps.inventory.views.registry_views.CustodyAssignment.objects")
    @patch("apps.inventory.views.registry_views.core_directory.user_can_approve_department")
    def test_resguardo_vigente_bloquea_ejecucion_y_ofrece_retiro(
        self, authority, custody_objects, document_objects, loan_objects
    ):
        authority.return_value = SimpleNamespace(allowed=False)
        disposal = self._disposal(uuid4(), "APPROVED", pending=False)
        disposal.asset_id = uuid4()
        custody = SimpleNamespace(id=uuid4(), status="ACTIVE")
        custody_objects.select_related.return_value.filter.return_value.order_by.return_value.first.return_value = custody
        document_objects.filter.return_value.order_by.return_value.first.return_value = None
        loan_objects.filter.return_value.order_by.return_value.first.return_value = None

        context = _disposal_context(
            self._request(
                uuid4(),
                "can_execute_disposals",
                "can_manage_custody",
                "can_review_patrimony_disposal",
            ),
            disposal,
        )

        self.assertFalse(context["can_execute_disposal"])
        self.assertIs(context["blocking_custody"], custody)
        self.assertTrue(context["can_prepare_custody_release"])

    @patch("apps.inventory.views.registry_views.AssetLoan.objects")
    @patch("apps.inventory.views.registry_views.CustodyDocument.objects")
    @patch("apps.inventory.views.registry_views.CustodyAssignment.objects")
    @patch("apps.inventory.views.registry_views.core_directory.user_can_approve_department")
    def test_dependencia_solicitante_no_opera_retiro_por_baja(
        self, authority, custody_objects, document_objects, loan_objects
    ):
        authority.return_value = SimpleNamespace(allowed=True)
        disposal = self._disposal(uuid4(), "APPROVED", pending=False)
        disposal.asset_id = uuid4()
        custody = SimpleNamespace(id=uuid4(), status="ACTIVE")
        custody_objects.select_related.return_value.filter.return_value.order_by.return_value.first.return_value = custody
        document_objects.filter.return_value.order_by.return_value.first.return_value = None
        loan_objects.filter.return_value.order_by.return_value.first.return_value = None

        context = _disposal_context(
            self._request(
                disposal.requested_by_id,
                "can_request_disposals",
                "can_manage_custody",
            ),
            disposal,
        )

        self.assertFalse(context["can_operate_custody_release"])
        self.assertFalse(context["can_prepare_custody_release"])

    @patch("apps.inventory.views.registry_views.AssetLoan.objects")
    @patch("apps.inventory.views.registry_views.core_directory.user_can_approve_department")
    def test_prestamo_abierto_bloquea_envio_de_baja(
        self, authority, loan_objects
    ):
        authority.return_value = SimpleNamespace(allowed=True)
        disposal = self._disposal(uuid4(), "DRAFT", pending=False)
        disposal.asset_id = uuid4()
        loan = SimpleNamespace(id=uuid4(), folio="PRE-039-222-2026-TEST")
        loan_objects.filter.return_value.order_by.return_value.first.return_value = loan

        context = _disposal_context(
            self._request(
                disposal.requested_by_id,
                "can_request_disposals",
            ),
            disposal,
        )

        self.assertIs(context["blocking_loan"], loan)
        self.assertFalse(context["can_submit_disposal"])

    @patch("apps.inventory.views.registry_views.core_directory.user_can_approve_department")
    def test_dependencia_no_cancela_despues_de_confirmar(self, authority):
        authority.return_value = SimpleNamespace(allowed=True)
        user_id = uuid4()
        context = _disposal_context(
            self._request(
                user_id,
                "can_request_disposals",
                "can_confirm_department_disposal",
            ),
            self._disposal(user_id, "TECHNICAL_REVIEW"),
        )
        self.assertFalse(context["can_cancel_disposal"])

    @patch("apps.inventory.views.registry_views.core_directory.user_can_approve_department")
    def test_expediente_cancelado_no_muestra_acciones_pendientes(self, authority):
        authority.return_value = SimpleNamespace(allowed=True)
        user_id = uuid4()
        context = _disposal_context(
            self._request(
                user_id,
                "can_request_disposals",
                "can_confirm_department_disposal",
            ),
            self._disposal(user_id, "CANCELLED"),
        )
        self.assertFalse(context["can_resolve_disposal"])
        self.assertFalse(context["can_cancel_disposal"])
        self.assertFalse(context["can_validate_disposal_document"])
