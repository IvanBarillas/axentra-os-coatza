from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class CorePlaceholderIntegrationTests(SimpleTestCase):
    FORBIDDEN_REFERENCES = (
        "Integración futura",
        "Próximamente",
        "funcionario_sub_hardware",
        "funcionario_sub_telefonia",
        "activos_simulados",
        "extensiones_simuladas",
        '"provider": "assets"',
        '"provider": "telefonia"',
        '"provider": "helpdesk"',
        "item.stub",
        '"stub":',
    )

    def test_core_does_not_publish_placeholder_integrations(self):
        security_root = Path(settings.BASE_DIR) / "apps" / "security"
        violations = []

        for path in security_root.rglob("*"):
            if not path.is_file():
                continue
            if "__pycache__" in path.parts:
                continue
            if path.suffix not in {".py", ".html"}:
                continue

            content = path.read_text(encoding="utf-8")

            for reference in self.FORBIDDEN_REFERENCES:
                if reference in content:
                    violations.append(
                        f"{path.relative_to(settings.BASE_DIR)}: {reference}"
                    )

        self.assertEqual(
            violations,
            [],
            "El Core contiene integraciones ficticias:\n"
            + "\n".join(violations),
        )