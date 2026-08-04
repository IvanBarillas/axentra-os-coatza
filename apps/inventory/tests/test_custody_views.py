from types import SimpleNamespace
from uuid import uuid4

from django.test import SimpleTestCase

from apps.inventory.views.registry_views import _custody_context


class CustodyButtonVisibilityTests(SimpleTestCase):
    def _request(self, user_id, *permissions, root=False):
        return SimpleNamespace(
            user=SimpleNamespace(pk=user_id),
            axentra_permissions_list=list(permissions),
            axentra_is_root=root,
        )

    def _custody(self, assigned_to_id, status, delivered=False):
        return SimpleNamespace(
            assigned_to_id=assigned_to_id,
            status=status,
            delivered_at=object() if delivered else None,
        )

    def test_resguardatario_solo_ve_aceptar_su_resguardo_entregado(self):
        user_id = uuid4()
        context = _custody_context(
            self._request(user_id, "can_accept_custody"),
            self._custody(user_id, "PENDING_ACCEPTANCE", delivered=True),
        )
        self.assertTrue(context["can_accept_custody"])
        self.assertTrue(context["can_reject_custody"])
        self.assertFalse(context["can_authorize_custody"])
        self.assertFalse(context["can_cancel_custody"])

    def test_usuario_no_puede_aceptar_resguardo_ajeno(self):
        context = _custody_context(
            self._request(uuid4(), "can_accept_custody"),
            self._custody(uuid4(), "PENDING_ACCEPTANCE", delivered=True),
        )
        self.assertFalse(context["can_accept_custody"])
        self.assertFalse(context["can_reject_custody"])

    def test_patrimonio_ve_entrega_pero_no_firma_por_el_usuario(self):
        context = _custody_context(
            self._request(uuid4(), "can_manage_custody"),
            self._custody(uuid4(), "PENDING_ACCEPTANCE", delivered=False),
        )
        self.assertTrue(context["can_deliver_custody"])
        self.assertFalse(context["can_accept_custody"])

    def test_resguardatario_no_puede_iniciar_retiro_de_resguardo_activo(self):
        user_id = uuid4()
        context = _custody_context(
            self._request(user_id, "can_accept_custody"),
            self._custody(user_id, "ACTIVE", delivered=True),
        )
        self.assertFalse(context["can_request_custody_return"])
        self.assertFalse(context["can_complete_custody_return"])

    def test_patrimonio_debe_usar_liberacion_documental(self):
        context = _custody_context(
            self._request(uuid4(), "can_manage_custody"),
            self._custody(uuid4(), "ACTIVE", delivered=True),
        )
        self.assertFalse(context["can_request_custody_return"])
        self.assertFalse(context["can_complete_custody_return"])
