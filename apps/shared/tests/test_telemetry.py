from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from apps.shared.utils.telemetry import AxentraRadar


class AxentraRadarTests(SimpleTestCase):
    @override_settings(AXENTRA_CORE_VERBOSE_RADAR=False)
    def test_disabled_radar_emits_nothing(self):
        with patch("apps.shared.utils.telemetry.logger.log") as log:
            AxentraRadar.emitir_evento(
                componente="test",
                titulo="Evento silenciado",
                extra_data={"dato": "valor"},
            )
        log.assert_not_called()

    @override_settings(AXENTRA_CORE_VERBOSE_RADAR=True)
    def test_enabled_radar_uses_logging_and_redacts_secrets(self):
        request = SimpleNamespace(
            path="/test/",
            user=SimpleNamespace(
                is_authenticated=True,
                email="operator@example.test",
            ),
        )
        with patch("apps.shared.utils.telemetry.logger.log") as log:
            AxentraRadar.emitir_evento(
                componente="test",
                titulo="Evento visible",
                request=request,
                extra_data={
                    "resultado": "correcto",
                    "password": "NuncaDebeAparecer",
                },
            )

        log.assert_called_once()
        rendered_payload = str(log.call_args)
        self.assertIn("[REDACTED]", rendered_payload)
        self.assertNotIn("NuncaDebeAparecer", rendered_payload)

    def test_source_tree_has_no_direct_print_calls(self):
        from pathlib import Path
        from django.conf import settings

        roots = (
            Path(settings.BASE_DIR) / "apps",
            Path(settings.BASE_DIR) / "core",
        )
        offenders = []
        for root in roots:
            for path in root.rglob("*.py"):
                text = path.read_text(encoding="utf-8")
                if "print(" in text and path.name != "test_telemetry.py":
                    offenders.append(str(path.relative_to(settings.BASE_DIR)))

        self.assertEqual(offenders, [])
