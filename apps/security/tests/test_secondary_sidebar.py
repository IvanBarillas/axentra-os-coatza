from django.contrib.staticfiles import finders
from django.template.loader import get_template
from django.test import SimpleTestCase


class SecondarySidebarAssetsTests(SimpleTestCase):
    def test_shell_base_compiles(self):
        self.assertIsNotNone(get_template("shell/base.html"))

    def test_secondary_sidebar_controller_is_discoverable(self):
        asset_path = finders.find("js/axentra-secondary-sidebar.js")
        self.assertTrue(asset_path)

        with open(asset_path, encoding="utf-8") as asset:
            source = asset.read()

        self.assertIn("htmx:pushedIntoHistory", source)
        self.assertIn("aria-current", source)
        self.assertIn("AxentraSecondarySidebar", source)
