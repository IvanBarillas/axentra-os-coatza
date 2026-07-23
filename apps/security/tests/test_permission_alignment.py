import ast
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import NoReverseMatch, reverse

from apps.security.permissions import (
    AccountsPermissions,
    ConfigurationPermissions,
    OrganigramaPermissions,
    SecurityPermissions,
)
from apps.security.models import AppModule, UserAppRole
from apps.security.services.permission_loader import get_user_permissions_for_app


MANIFESTS = {
    "SECURITY": SecurityPermissions,
    "CONFIGURATION": ConfigurationPermissions,
    "ACCOUNTS": AccountsPermissions,
    "ORGANIGRAMA": OrganigramaPermissions,
}


class PermissionManifestAlignmentTests(SimpleTestCase):
    def test_roles_and_sidebar_only_reference_declared_permissions(self):
        for manifest in MANIFESTS.values():
            declared = set(manifest.PERMISSIONS)
            self.assertEqual(
                set(manifest.ROLE_MAPPING["owner"]),
                declared,
                msg=f"OWNER debe contener todas las llaves de {manifest.APP_CODE}.",
            )
            for role, permissions in manifest.ROLE_MAPPING.items():
                self.assertIn(
                    "has_access_module",
                    permissions,
                    msg=f"El rol {role} de {manifest.APP_CODE} no puede entrar.",
                )
                self.assertFalse(
                    set(permissions) - declared,
                    msg=f"El rol {role} usa permisos no declarados.",
                )
            for item in manifest.SIDEBAR_MENU:
                permission = item.get("permission") if isinstance(item, dict) else item[4]
                self.assertIn(permission, declared)

    def test_every_primary_sidebar_route_resolves(self):
        for manifest in MANIFESTS.values():
            for item in manifest.SIDEBAR_MENU:
                url_name = item.get("url") if isinstance(item, dict) else item[2]
                self.assertNotEqual(url_name, "#")
                try:
                    reverse(url_name)
                except NoReverseMatch as exc:
                    self.fail(f"La ruta {url_name} no existe: {exc}")

    def test_view_decorators_use_permissions_from_the_correct_manifest(self):
        views_dir = Path(settings.BASE_DIR) / "apps" / "security" / "views"
        for filename in (
            "security_views.py",
            "accounts_views.py",
            "organigrama_views.py",
        ):
            tree = ast.parse((views_dir / filename).read_text(encoding="utf-8"))
            for node in tree.body:
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                gate_decorators = []
                for decorator in node.decorator_list:
                    if not isinstance(decorator, ast.Call):
                        continue
                    if "axentra_module_gate" not in ast.unparse(decorator.func):
                        continue
                    gate_decorators.append(decorator)
                self.assertLessEqual(
                    len(gate_decorators),
                    1,
                    msg=f"{filename}:{node.name} tiene el gate duplicado.",
                )
                for decorator in gate_decorators:
                    module_expr = (
                        decorator.args[0]
                        if decorator.args
                        else next(
                            kw.value for kw in decorator.keywords
                            if kw.arg == "module_identifier"
                        )
                    )
                    module_name = ast.unparse(module_expr).rsplit(".", 1)[-1]
                    permission_node = next(
                        (
                            kw.value for kw in decorator.keywords
                            if kw.arg == "required_fine_permission"
                        ),
                        None,
                    )
                    if permission_node is None:
                        continue
                    permission = ast.literal_eval(permission_node)
                    self.assertIn(
                        permission,
                        MANIFESTS[module_name].PERMISSIONS,
                        msg=(
                            f"{filename}:{node.name} exige {permission} "
                            f"dentro de {module_name}."
                        ),
                    )

    def test_global_sidebar_has_no_hardcoded_satellite_routes(self):
        template = (
            Path(settings.BASE_DIR)
            / "templates"
            / "navigation"
            / "global_sidebar_menu.html"
        ).read_text(encoding="utf-8")
        self.assertNotIn("inventory:", template)
        self.assertNotIn("helpdesk:", template)
        self.assertIn("satellite_navigation", template)


class PermissionMembershipSafetyTests(TestCase):
    def test_soft_deleted_membership_never_grants_access(self):
        user = get_user_model().objects.create_user(
            email="inactive-membership@example.test",
            password="Password-Seguro-2026!",
            first_name="Prueba",
        )
        module = AppModule.objects.get(slug="security")
        UserAppRole.objects.create(
            user=user,
            app=module,
            role="viewer",
            permissions_list=["has_access_module"],
            is_active=True,
            is_deleted=True,
        )

        permissions = get_user_permissions_for_app(user, "security")

        self.assertFalse(permissions["has_access_module"])
        self.assertEqual(permissions["permissions_list"], [])
