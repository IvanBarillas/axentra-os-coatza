from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

from django.test import SimpleTestCase

from apps.inventory.documents import (
    get_acknowledgement_spec,
    get_acknowledgement_state,
)
from apps.inventory.models import DocumentValidationStatus


class DocumentAcknowledgementContractTests(SimpleTestCase):
    def test_prestamo_separa_vale_generado_de_acuse_firmado(self):
        spec = get_acknowledgement_spec("LOAN_RECEIPT", "LOAN")
        self.assertEqual(spec.generated_type, "LOAN_RECEIPT")
        self.assertEqual(
            spec.acknowledgement_type,
            "SIGNED_LOAN_RECEIPT",
        )

    def test_resguardo_agrupador_utiliza_el_mismo_contrato(self):
        spec = get_acknowledgement_spec(
            "CUSTODY_RECEIPT",
            "CUSTODY_DOCUMENT",
        )
        self.assertIn("CUSTODY_DOCUMENT", spec.owner_types)

    def test_liberacion_masiva_admite_acuse_en_documento_de_resguardo(self):
        spec = get_acknowledgement_spec(
            "RETURN_RECEIPT",
            "CUSTODY_DOCUMENT",
        )
        self.assertEqual(spec.acknowledgement_type, "SIGNED_RETURN_RECEIPT")
        self.assertIn("CUSTODY_DOCUMENT", spec.owner_types)

    def test_rechaza_una_pareja_documental_incompatible(self):
        with self.assertRaises(ValueError):
            get_acknowledgement_spec(
                "LOAN_RECEIPT",
                "CUSTODY_ASSIGNMENT",
            )

    @patch(
        "apps.inventory.documents.acknowledgements."
        "AssetDocument.objects.filter"
    )
    def test_documento_rechazado_se_muestra_como_acuse_observado(
        self,
        filter_mock,
    ):
        document = SimpleNamespace(
            validation_status=DocumentValidationStatus.REJECTED,
        )
        queryset = MagicMock()
        queryset.order_by.return_value.first.return_value = document
        filter_mock.return_value = queryset
        state = get_acknowledgement_state(
            owner_type="LOAN",
            owner_id=uuid4(),
            generated_type="LOAN_RECEIPT",
        )
        self.assertEqual(state.code, "OBSERVED")
        self.assertEqual(state.label, "Acuse observado")
