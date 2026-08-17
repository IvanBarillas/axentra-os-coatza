from django.test import SimpleTestCase

from apps.shared.module_sdk.launcher import build_launcher_context


def make_card(index, **overrides):
    card = {
        "code": f"module_{index}",
        "name": f"Aplicación {index:02d}",
        "description": "Herramienta institucional de prueba.",
        "kind": "SATELLITE",
        "installed": True,
        "enabled": True,
        "health": "HEALTHY",
        "can_open": True,
    }
    card.update(overrides)
    return card


class ScalableLauncherTests(SimpleTestCase):
    def test_thirty_apps_are_paginated_in_pages_of_twelve(self):
        context = build_launcher_context(
            [make_card(index) for index in range(30)],
            is_root=True,
        )
        self.assertEqual(context["launcher_result_count"], 30)
        self.assertEqual(len(context["application_page"]), 12)
        self.assertEqual(context["application_page"].paginator.num_pages, 3)

    def test_core_components_are_separated_for_root(self):
        cards = [
            make_card(1),
            make_card(2, kind="CORE", code="security", name="Seguridad"),
        ]
        context = build_launcher_context(cards, is_root=True)
        self.assertEqual(len(context["core_cards"]), 1)
        self.assertEqual(context["launcher_result_count"], 1)

    def test_operator_only_sees_apps_they_can_open(self):
        cards = [
            make_card(1),
            make_card(2, can_open=False),
            make_card(3, enabled=False),
            make_card(4, installed=False),
        ]
        context = build_launcher_context(cards, is_root=False)
        self.assertEqual(
            [card["code"] for card in context["application_page"]],
            ["module_1"],
        )

    def test_search_and_state_filters_compose(self):
        cards = [
            make_card(1, name="Inventario patrimonial"),
            make_card(2, name="Inventario histórico", health="WARNING"),
            make_card(3, name="Mesa de ayuda"),
        ]
        context = build_launcher_context(
            cards,
            is_root=True,
            query="inventario",
            state="attention",
        )
        self.assertEqual(context["launcher_result_count"], 1)
        self.assertEqual(context["application_page"][0]["code"], "module_2")
