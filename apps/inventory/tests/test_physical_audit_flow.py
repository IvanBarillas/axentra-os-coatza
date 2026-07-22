from types import SimpleNamespace
from uuid import uuid4

from django.test import SimpleTestCase

from apps.inventory.models import PhysicalAuditResult, PhysicalCondition
from apps.inventory.services.physical_audit_service import _determine_result


class PhysicalAuditResultTests(SimpleTestCase):
    def setUp(self):
        self.site_id = uuid4()
        self.department_id = uuid4()
        self.area_id = uuid4()
        self.custodian_id = uuid4()
        self.item = SimpleNamespace(
            expected_sede_id=self.site_id,
            expected_dependencia_id=self.department_id,
            expected_area_id=self.area_id,
            expected_custodian_id=self.custodian_id,
            expected_condition=PhysicalCondition.GOOD,
        )

    def test_coincidencia_total_es_conciliada(self):
        result = _determine_result(
            self.item, condition=PhysicalCondition.GOOD,
            site_id=self.site_id, department_id=self.department_id,
            area_id=self.area_id, custodian_id=self.custodian_id,
        )
        self.assertEqual(result, PhysicalAuditResult.FOUND)

    def test_detecta_ubicacion_y_resguardatario_distintos(self):
        result = _determine_result(
            self.item, condition=PhysicalCondition.GOOD,
            site_id=uuid4(), department_id=uuid4(), area_id=uuid4(),
            custodian_id=uuid4(),
        )
        self.assertEqual(
            result,
            PhysicalAuditResult.FOUND_DIFFERENT_LOCATION_AND_CUSTODIAN,
        )

    def test_condicion_mala_se_clasifica_como_dano(self):
        result = _determine_result(
            self.item, condition=PhysicalCondition.BAD,
            site_id=self.site_id, department_id=self.department_id,
            area_id=self.area_id, custodian_id=self.custodian_id,
        )
        self.assertEqual(result, PhysicalAuditResult.DAMAGED)
