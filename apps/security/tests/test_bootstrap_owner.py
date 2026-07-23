from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.security.models import AppModule, UserAppRole
from apps.shared.module_sdk.registry import module_registry


@override_settings(
    AXENTRA_OWNER_EMAIL="owner@municipio.test",
    AXENTRA_OWNER_DEFAULT_PASSWORD="Password-Seguro-2026!",
)
class BootstrapAxentraOwnerTests(TestCase):
    def test_creates_one_owner_with_membership_for_every_module(self):
        call_command("bootstrap_axentra_owner", stdout=StringIO())

        User = get_user_model()
        owner = User.objects.get(email="owner@municipio.test")
        self.assertTrue(owner.is_superuser)
        self.assertTrue(owner.is_manager)
        self.assertTrue(owner.check_password("Password-Seguro-2026!"))

        installed_codes = {item.code for item in module_registry.discover()}
        membership_codes = set(
            UserAppRole.objects.filter(
                user=owner,
                role=UserAppRole.ReservedRoles.OWNER,
            ).values_list("app__slug", flat=True)
        )
        self.assertEqual(membership_codes, installed_codes)

    def test_is_idempotent_and_preserves_existing_password(self):
        call_command("bootstrap_axentra_owner", stdout=StringIO())
        owner = get_user_model().objects.get(email="owner@municipio.test")
        owner.set_password("Password-Cambiado-Por-Usuario!")
        owner.save(update_fields=["password"])

        call_command("bootstrap_axentra_owner", stdout=StringIO())
        owner.refresh_from_db()

        self.assertTrue(owner.check_password("Password-Cambiado-Por-Usuario!"))
        self.assertEqual(
            UserAppRole.objects.filter(user=owner).count(),
            AppModule.objects.filter(is_deleted=False).count(),
        )
