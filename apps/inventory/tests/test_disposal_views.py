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
    def test_director_puede_resolver_etapa_de_su_dependencia(self, authority):
        authority.return_value = SimpleNamespace(allowed=True)
        context = _disposal_context(
            self._request(uuid4(), "can_request_disposals"),
            self._disposal(uuid4(), "ADMINISTRATIVE_REVIEW"),
        )
        self.assertTrue(context["can_resolve_disposal"])
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
