from uuid import uuid4

from django.test import SimpleTestCase

from apps.inventory.forms.custody_document_forms import (
    CustodyDocumentCreateForm,
)
from apps.inventory.models import CustodyAssigneeMode


class CustodyDocumentCreateFormTests(SimpleTestCase):
    def _form(self, *, mode, user_id=None, asset_count=2):
        department_id = uuid4()
        asset_ids = [uuid4() for _ in range(asset_count)]
        form = CustodyDocumentCreateForm(
            data={
                "department_id": str(department_id),
                "assignee_mode": mode,
                "assigned_to_id": str(user_id) if user_id else "",
                "asset_ids": [str(value) for value in asset_ids],
                "notes": "",
                "bypass_reason": "",
            }
        )
        form.fields["department_id"].choices = [
            (str(department_id), "Dependencia de prueba")
        ]
        form.fields["asset_ids"].choices = [
            (str(value), f"Bien {index}")
            for index, value in enumerate(asset_ids, start=1)
        ]
        if user_id:
            form.fields["assigned_to_id"].choices = [
                (str(user_id), "Servidor público de prueba")
            ]
        return form

    def test_department_manager_accepts_multiple_assets(self):
        form = self._form(
            mode=CustodyAssigneeMode.DEPARTMENT_MANAGER,
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(len(form.cleaned_asset_ids()), 2)

    def test_public_servant_requires_user(self):
        form = self._form(
            mode=CustodyAssigneeMode.PUBLIC_SERVANT,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("assigned_to_id", form.errors)

    def test_document_requires_at_least_one_asset(self):
        form = self._form(
            mode=CustodyAssigneeMode.DEPARTMENT_MANAGER,
            asset_count=0,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("asset_ids", form.errors)
