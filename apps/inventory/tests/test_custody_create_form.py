from uuid import uuid4

from django.test import SimpleTestCase

from apps.inventory.forms import CustodyCreateForm
from apps.inventory.models import CustodyAssigneeMode


class CustodyCreateFormTests(SimpleTestCase):
    @staticmethod
    def _form(*, asset_id=None, user_id=None, **data):
        asset_id = asset_id or uuid4()
        form = CustodyCreateForm(
            data={
                "asset_id": str(asset_id),
                "assigned_to_id": str(user_id) if user_id else "",
                "notes": "",
                "bypass_reason": "",
                **data,
            }
        )
        form.fields["asset_id"].choices = [
            (str(asset_id), "Bien de prueba"),
        ]
        if user_id:
            form.fields["assigned_to_id"].choices = [
                (str(user_id), "Servidor público de prueba"),
            ]
        return form

    def test_public_servant_requires_user(self):
        form = self._form(
            assignee_mode=CustodyAssigneeMode.PUBLIC_SERVANT,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("assigned_to_id", form.errors)

    def test_department_manager_does_not_require_manual_user(self):
        form = self._form(
            assignee_mode=CustodyAssigneeMode.DEPARTMENT_MANAGER,
        )

        self.assertTrue(form.is_valid(), form.errors)
        dto = form.to_dto()
        self.assertIsNone(dto.assigned_to_id)
        self.assertEqual(
            dto.assignee_mode,
            CustodyAssigneeMode.DEPARTMENT_MANAGER,
        )

    def test_public_servant_is_preserved_in_dto(self):
        user_id = uuid4()
        form = self._form(
            user_id=user_id,
            assignee_mode=CustodyAssigneeMode.PUBLIC_SERVANT,
            notes="Equipo instalado en oficina.",
        )

        self.assertTrue(form.is_valid(), form.errors)
        dto = form.to_dto()
        self.assertEqual(dto.assigned_to_id, user_id)
        self.assertEqual(dto.notes, "Equipo instalado en oficina.")
