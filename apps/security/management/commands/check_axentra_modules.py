from django.core.management.base import BaseCommand

from apps.shared.module_sdk.registry import module_registry
from apps.shared.module_sdk.services import (
    get_module_runtime_status,
    sync_installed_modules,
)


class Command(BaseCommand):
    help = "Sincroniza y comprueba módulos instalados de Axentra OS."

    def add_arguments(self, parser):
        parser.add_argument(
            "--persist",
            action="store_true",
            help="Guarda el resultado de salud en AppModule.",
        )

    def handle(self, *args, **options):
        sync_installed_modules()
        failed = False
        for manifest in module_registry.discover():
            status = get_module_runtime_status(
                manifest.code,
                persist=options["persist"],
            )
            marker = "OK" if status.available else "AVISO"
            self.stdout.write(
                f"[{marker}] {manifest.code}: {status.message}"
            )
            if status.enabled and not status.available:
                failed = True
        if failed:
            self.stderr.write(
                self.style.WARNING("Hay módulos activos que requieren atención.")
            )
        else:
            self.stdout.write(self.style.SUCCESS("Registro modular saludable."))
