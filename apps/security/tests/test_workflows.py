from django.template.loader import get_template
from django.test import SimpleTestCase

from apps.shared.workflows import get_workflow


class CoreWorkflowRegistrationTests(SimpleTestCase):
    def test_security_workflows_are_registered(self):
        expected = {
            "security.access_resolution",
            "accounts.user_lifecycle",
            "organigrama.structure",
        }
        definitions = {get_workflow(code).code for code in expected}
        self.assertEqual(definitions, expected)

    def test_dashboard_templates_compile(self):
        templates = (
            "security/content/security_dashboard_content.html",
            "accounts/content/accounts_dashboard_content.html",
            "organigrama/content/estructura_list_content.html",
        )
        for template_name in templates:
            with self.subTest(template=template_name):
                self.assertIsNotNone(get_template(template_name))
