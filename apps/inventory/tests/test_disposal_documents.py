from types import SimpleNamespace
from uuid import uuid4

from django.test import SimpleTestCase

from apps.inventory.forms import DisposalStageDocumentUploadForm
from apps.inventory.models import DisposalApprovalStage, DocumentType
from apps.inventory.services.disposal_service import disposal_stage_document_types
from apps.inventory.services.document_service import (
    disposal_stage_document_upload_permissions,
)


class DisposalStageDocumentChoiceTests(SimpleTestCase):
    def test_patrimonio_suple_dictamen_solo_sin_helpdesk(self):
        unavailable = disposal_stage_document_upload_permissions(
            DisposalApprovalStage.TECHNICAL,
            helpdesk_available=False,
        )
        available = disposal_stage_document_upload_permissions(
            DisposalApprovalStage.TECHNICAL,
            helpdesk_available=True,
        )
        self.assertIn("can_review_patrimony_disposal", unavailable)
        self.assertNotIn("can_review_patrimony_disposal", available)

    def test_patrimonio_puede_integrar_confirmacion_contable(self):
        permissions = disposal_stage_document_upload_permissions(
            DisposalApprovalStage.FINAL_AUTHORIZATION,
            document_type=DocumentType.ACCOUNTING_DISPOSAL_CONFIRMATION,
            helpdesk_available=True,
        )
        self.assertIn("can_finalize_disposal", permissions)
        self.assertIn("can_review_patrimony_disposal", permissions)

    def test_integracion_custodial_exige_datos_del_emisor(self):
        form = DisposalStageDocumentUploadForm(
            approval_id=uuid4(),
            document_choices=((DocumentType.TECHNICAL_REPORT, "Dictamen técnico"),),
            custodial_integration=True,
        )
        # La obligatoriedad se aplica en clean únicamente al seleccionar un
        # dictamen o constancia contable, no al oficio emitido por Patrimonio.
        self.assertFalse(form.fields["external_reference"].required)
        self.assertIn("issuing_authority", form.fields)
        self.assertIn("issuing_official_role", form.fields)
        self.assertIn("document_date", form.fields)

    def test_patrimonio_emite_oficio_de_solicitud_de_dictamen(self):
        permissions = disposal_stage_document_upload_permissions(
            DisposalApprovalStage.TECHNICAL,
            document_type=DocumentType.TECHNICAL_REPORT_REQUEST,
            helpdesk_available=True,
        )
        self.assertEqual(permissions, ("can_review_patrimony_disposal",))

    def test_empty_stage_choices_never_fall_back_to_full_catalog(self):
        form = DisposalStageDocumentUploadForm(
            approval_id=uuid4(),
            document_choices=(),
        )
        self.assertEqual(list(form.fields["document_type"].choices), [])

    def test_legacy_snapshot_is_separated_by_stage(self):
        disposal = SimpleNamespace(
            required_document_types_snapshot=[
                DocumentType.TECHNICAL_REPORT,
                DocumentType.COUNCIL_MINUTES,
            ]
        )
        self.assertEqual(
            disposal_stage_document_types(
                disposal, DisposalApprovalStage.DEPARTMENT
            ),
            (DocumentType.DISPOSAL_REQUEST,),
        )
        self.assertEqual(
            disposal_stage_document_types(
                disposal, DisposalApprovalStage.TECHNICAL
            ),
            (
                DocumentType.TECHNICAL_REPORT,
                DocumentType.TECHNICAL_REPORT_REQUEST,
            ),
        )
        self.assertEqual(
            disposal_stage_document_types(
                disposal, DisposalApprovalStage.PATRIMONY
            ),
            (DocumentType.ACCOUNTING_DISPOSAL_REQUEST,),
        )
        self.assertEqual(
            disposal_stage_document_types(
                disposal, DisposalApprovalStage.FINAL_AUTHORIZATION
            ),
            (DocumentType.ACCOUNTING_DISPOSAL_CONFIRMATION,),
        )

    def test_etapa_tecnica_heredada_recupera_tipo_de_dictamen(self):
        disposal = SimpleNamespace(
            required_document_types_snapshot=[],
            technical_report_required=True,
            reason="OTHER",
        )
        self.assertEqual(
            disposal_stage_document_types(
                disposal, DisposalApprovalStage.TECHNICAL
            ),
            (
                DocumentType.TECHNICAL_REPORT,
                DocumentType.TECHNICAL_REPORT_REQUEST,
            ),
        )
