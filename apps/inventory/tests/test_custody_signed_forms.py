from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from apps.inventory.forms.custody_signed_forms import CustodySignedDocumentForm


class CustodySignedDocumentFormTests(SimpleTestCase):
    def test_accepts_signed_pdf(self):
        form = CustodySignedDocumentForm(
            data={"signed_at": "2026-07-23T13:00", "notes": "Firmado."},
            files={
                "file": SimpleUploadedFile(
                    "resguardo-firmado.pdf",
                    b"%PDF-1.4 signed",
                    content_type="application/pdf",
                )
            },
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_rejects_non_pdf_file(self):
        form = CustodySignedDocumentForm(
            data={"signed_at": "2026-07-23T13:00"},
            files={
                "file": SimpleUploadedFile(
                    "resguardo.txt",
                    b"not a pdf",
                    content_type="text/plain",
                )
            },
        )
        self.assertFalse(form.is_valid())
        self.assertIn("file", form.errors)
