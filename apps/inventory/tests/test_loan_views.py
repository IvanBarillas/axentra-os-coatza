from types import SimpleNamespace
from datetime import datetime, timezone
from unittest.mock import patch
from uuid import UUID, uuid4

from django.test import SimpleTestCase

from apps.inventory.views.registry_views import (
    _loan_context,
    _loan_origin_department_id,
)
from apps.inventory.services.loan_service import _loan_folio


class LoanButtonVisibilityTests(SimpleTestCase):
    def _request(self, user_id, department_id, *permissions):
        request = SimpleNamespace(
            user=SimpleNamespace(pk=user_id),
            axentra_permissions_list=list(permissions),
            axentra_is_root=False,
        )
        request._inventory_department_id = department_id
        return request

    def _loan(self, **values):
        defaults = {
            "requested_by_id": uuid4(),
            "borrower_id": uuid4(),
            "destination_dependencia_id": uuid4(),
            "status": "REQUESTED",
            "external_borrower": False,
        }
        defaults.update(values)
        return SimpleNamespace(**defaults)

    def test_director_receptor_puede_decidir_solo_su_solicitud(self):
        department_id = uuid4()
        request = self._request(
            uuid4(),
            department_id,
            "can_request_loans",
            "can_authorize_loans",
        )
        context = _loan_context(
            request,
            self._loan(destination_dependencia_id=department_id),
        )
        self.assertTrue(context["can_decide_department_loan"])
        self.assertFalse(context["can_authorize_loan"])
        self.assertFalse(context["can_deliver_loan"])

    def test_director_no_decide_prestamos_de_otra_dependencia(self):
        request = self._request(
            uuid4(),
            uuid4(),
            "can_request_loans",
            "can_authorize_loans",
        )
        context = _loan_context(request, self._loan())
        self.assertFalse(context["can_decide_department_loan"])

    def test_patrimonio_autoriza_pero_no_suplanta_decision_departamental(self):
        request = self._request(
            uuid4(),
            uuid4(),
            "can_manage_loans",
        )
        context = _loan_context(
            request,
            self._loan(status="DEPARTMENT_APPROVED"),
        )
        self.assertTrue(context["can_authorize_loan"])
        self.assertFalse(context["can_decide_department_loan"])

    def test_director_solo_puede_usar_su_dependencia_como_origen(self):
        department_id = uuid4()
        request = self._request(
            uuid4(),
            department_id,
            "can_request_loans",
            "can_authorize_loans",
        )
        self.assertEqual(
            _loan_origin_department_id(request),
            department_id,
        )

    def test_patrimonio_puede_elegir_cualquier_dependencia_de_origen(self):
        request = self._request(
            uuid4(),
            uuid4(),
            "can_manage_loans",
        )
        self.assertIsNone(_loan_origin_department_id(request))

    @patch(
        "apps.inventory.services.loan_service.get_effective_folio_policy",
        return_value=SimpleNamespace(municipality_code="39"),
    )
    def test_folio_de_prestamo_incluye_municipio_dependencia_y_anio(
        self,
        _policy,
    ):
        folio = _loan_folio(
            loan_id=UUID("ca131c0d-0000-0000-0000-000000000000"),
            requested_at=datetime(2026, 7, 24, tzinfo=timezone.utc),
            department=SimpleNamespace(normalized_code="001"),
        )
        self.assertEqual(folio, "PRE-039-001-2026-CA131C0D")

    def test_prestamo_entregado_sin_acuse_se_marca_pendiente(self):
        request = self._request(
            uuid4(),
            uuid4(),
            "can_manage_loans",
        )
        context = _loan_context(
            request,
            self._loan(status="DELIVERED"),
        )
        self.assertTrue(context["receipt_required"])
        self.assertIsNone(context["loan_receipt"])
