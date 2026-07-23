# apps/security/apps.py

import logging

from django.apps import AppConfig
from django.db.models.signals import post_migrate


logger = logging.getLogger(__name__)


def sincronizar_modulos_axentra(sender, **kwargs):
    """Sincroniza metadatos técnicos; nunca crea usuarios ni contraseñas."""
    from apps.shared.module_sdk.services import sync_installed_modules

    modules = sync_installed_modules()
    logger.info(
        "Registro modular de Axentra OS sincronizado: %s módulo(s).",
        len(modules),
    )


class SecurityConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.security"
    verbose_name = "Seguridad y Permisos del Sistema"

    def ready(self):
        # Registra las guías visuales de Security, Accounts y Organigrama.
        # El import es idempotente por el caché de módulos de Python.
        from apps.security import workflows  # noqa: F401

        post_migrate.connect(
            sincronizar_modulos_axentra,
            sender=self,
            dispatch_uid="apps.security.sincronizar_modulos_axentra",
            weak=False,
        )
