from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from django.test import SimpleTestCase

from apps.inventory.views.custody_document_views import (
    _configure_dynamic_choices,
    _create_document_form,
)


class CustodyDocumentFormInitialTests(SimpleTestCase):
    def test_get_conserva_la_dependencia_seleccionada(self):
        department_id = uuid4()
        request = SimpleNamespace(method="GET", POST={})
        form = _create_document_form(request, str(department_id))
        form.fields["department_id"].choices = [
            ("other", "Dirección de Egresos"),
            (str(department_id), "Innovación Gubernamental"),
        ]
        self.assertEqual(
            form["department_id"].value(),
            str(department_id),
        )

    def test_post_respeta_el_valor_enviado_por_el_usuario(self):
        department_id = uuid4()
        request = SimpleNamespace(
            method="POST",
            POST={"department_id": str(department_id)},
        )
        form = _create_document_form(request, str(department_id))
        form.fields["department_id"].choices = [
            (str(department_id), "Innovación Gubernamental"),
        ]
        self.assertEqual(
            form["department_id"].value(),
            str(department_id),
        )

    @patch(
        "apps.inventory.views.custody_document_views._department_choices",
        return_value=[],
    )
    def test_dependencia_recarga_el_contenido_mediante_htmx(self, _choices):
        request = SimpleNamespace(method="GET", POST={})
        form = _create_document_form(request, "")

        assets = _configure_dynamic_choices(form, "")
        attrs = form.fields["department_id"].widget.attrs

        self.assertEqual(assets, [])
        self.assertEqual(attrs["hx-target"], "#page-content")
        self.assertEqual(attrs["hx-trigger"], "change")
        self.assertEqual(attrs["hx-swap"], "innerHTML")
        self.assertEqual(attrs["hx-push-url"], "true")
