from django.test import SimpleTestCase

from apps.inventory.selectors import CustodySelectors


class CustodySelectorQueryTests(SimpleTestCase):
    def test_base_queryset_uses_current_custody_relations(self):
        """La consulta debe compilar sin referencias a campos heredados."""

        query = CustodySelectors.base_queryset()
        sql = str(query.query)

        self.assertTrue(sql)
        self.assertNotIn("assigned_by", query.query.select_related)
        self.assertIn("prepared_by", query.query.select_related)
        self.assertIn("authorized_by", query.query.select_related)
        self.assertIn("delivered_by", query.query.select_related)
