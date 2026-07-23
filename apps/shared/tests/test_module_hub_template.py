from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class ModuleHubTemplateTests(SimpleTestCase):
    def test_hub_is_a_control_panel_not_an_installer_or_launcher(self):
        template = (Path(settings.BASE_DIR) / "templates" / "index_hub.html").read_text(
            encoding="utf-8"
        )

        self.assertNotIn("Abrir módulo", template)
        self.assertNotIn("Cómo instalar este módulo", template)
        self.assertNotIn("Distribución:", template)
        self.assertIn("Disponible para usuarios autorizados", template)
        self.assertIn("Activar", template)
        self.assertIn("Desactivar", template)
