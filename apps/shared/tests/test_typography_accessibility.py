import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


SUB_MINIMUM_TEXT_SIZE = re.compile(
    r"text-\[(?:8|9|10|11)px\]"
)


class TypographyAccessibilityTests(SimpleTestCase):
    def test_templates_do_not_use_text_smaller_than_twelve_pixels(self):
        roots = (
            Path(settings.BASE_DIR) / "apps",
            Path(settings.BASE_DIR) / "templates",
        )
        violations = []

        for root in roots:
            for template in root.rglob("*.html"):
                if "staticfiles" in template.parts:
                    continue

                content = template.read_text(encoding="utf-8")
                if SUB_MINIMUM_TEXT_SIZE.search(content):
                    violations.append(
                        str(template.relative_to(settings.BASE_DIR))
                    )

        self.assertEqual(
            violations,
            [],
            "Se encontraron textos menores de 12 px:\n"
            + "\n".join(violations),
        )