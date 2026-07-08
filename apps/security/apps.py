# apps/security/apps.py

from django.apps import AppConfig
from django.db.models.signals import post_migrate


def sincronizar_entorno_so_axentra(sender, **kwargs):
    """Motor de Aprovisionamiento e Integridad de Axentra OS post-migración."""
    try:
        from django.conf import settings
        from django.contrib.auth import get_user_model
        from apps.security.models import AppModule, UserAppRole
        from apps.shared.manifest_registry import AxentraOSRegistry

        User = get_user_model()

        print("\n⚙️  " + "=" * 76)
        print("🛰️  [AXENTRA OS] INICIANDO PROTOCOLO DE INTEGRIDAD POST-MIGRACIÓN")
        print("=" * 80)

        print("👥 1. Validando existencia del Operador Supremo...")
        email_root = getattr(settings, "AXENTRA_OWNER_EMAIL", "owner@axentra.com.mx")
        password_root = getattr(settings, "AXENTRA_OWNER_DEFAULT_PASSWORD", "1q2w3e4r5t%")

        user_root, user_creado = User.objects.get_or_create(
            email=email_root,
            defaults={
                "first_name": "Operador",
                "last_name": "Supremo",
                "is_staff": False,
                "is_superuser": True,
                "is_active": True,
                "is_deleted": False,
            },
        )

        if user_creado:
            user_root.set_password(password_root)
            if hasattr(user_root, "is_manager"):
                user_root.is_manager = True
            if hasattr(user_root, "must_change_password"):
                user_root.must_change_password = False
            if hasattr(user_root, "is_email_verified"):
                user_root.is_email_verified = True
            user_root.save()
            print(f"   ↳ 👑 Operador Supremo creado con éxito: [{email_root}] (Pass default configurada)")
        else:
            campos_actualizados = []
            if not user_root.is_superuser:
                user_root.is_superuser = True
                campos_actualizados.append("is_superuser")
            if hasattr(user_root, "is_manager") and not user_root.is_manager:
                user_root.is_manager = True
                campos_actualizados.append("is_manager")
            if not user_root.is_active:
                user_root.is_active = True
                campos_actualizados.append("is_active")
            if hasattr(user_root, "is_deleted") and user_root.is_deleted:
                user_root.is_deleted = False
                campos_actualizados.append("is_deleted")
            if hasattr(user_root, "deleted_at") and user_root.deleted_at:
                user_root.deleted_at = None
                campos_actualizados.append("deleted_at")
            if hasattr(user_root, "must_change_password") and user_root.must_change_password:
                user_root.must_change_password = False
                campos_actualizados.append("must_change_password")
            if hasattr(user_root, "is_email_verified") and not user_root.is_email_verified:
                user_root.is_email_verified = True
                campos_actualizados.append("is_email_verified")
            if campos_actualizados:
                if hasattr(user_root, "updated_at"):
                    campos_actualizados.append("updated_at")
                user_root.save(update_fields=campos_actualizados)
            print(f"   ↳ ✓ Operador Supremo verificado: [{email_root}] (Flags de bypass asegurados)")

        print("🔒 2. Re-calculando matrices de privilegios independientes por App...")
        print("-" * 80)

        manifiestos_detectados = AxentraOSRegistry.get_all_manifests()
        roles_modificados = 0
        total_llaves_sembradas = 0

        for slug, clase_manifiesto in manifiestos_detectados.items():
            slug = str(slug).strip().lower()
            nombre_legible = slug.replace("_", " ").capitalize()

            app_obj, creado_app = AppModule.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": f"Satélite {nombre_legible}",
                    "description": f"Módulo desacoplado para la gestión de {nombre_legible}.",
                    "is_active": True,
                    "is_deleted": False,
                },
            )

            app_update_fields = []
            if not app_obj.is_active:
                app_obj.is_active = True
                app_update_fields.append("is_active")
            if getattr(app_obj, "is_deleted", False):
                app_obj.is_deleted = False
                app_update_fields.append("is_deleted")
            if getattr(app_obj, "deleted_at", None):
                app_obj.deleted_at = None
                app_update_fields.append("deleted_at")
            if not app_obj.name:
                app_obj.name = f"Satélite {nombre_legible}"
                app_update_fields.append("name")
            if not app_obj.description:
                app_obj.description = f"Módulo desacoplado para la gestión de {nombre_legible}."
                app_update_fields.append("description")
            if app_update_fields:
                if hasattr(app_obj, "updated_at"):
                    app_update_fields.append("updated_at")
                app_obj.save(update_fields=app_update_fields)

            if creado_app:
                print(f"   🛰️  Módulo Sembrado -> App: [{slug:<14}] | Nombre: {app_obj.name}")

            llaves_owner = clase_manifiesto.ROLE_MAPPING.get("owner", [])
            total_llaves_sembradas += len(llaves_owner)

            role_obj, creado_rol = UserAppRole.objects.get_or_create(
                user=user_root,
                app=app_obj,
                defaults={
                    "role": UserAppRole.ReservedRoles.OWNER,
                    "permissions_list": llaves_owner,
                    "is_active": True,
                    "is_deleted": False,
                },
            )

            if creado_rol:
                print(f"   🟢 Membresía Sembrada -> App: [{slug:<14}] | Inyectadas: {len(llaves_owner)} llaves JSON.")
                roles_modificados += 1
                continue

            role_update_fields = []
            if role_obj.role != UserAppRole.ReservedRoles.OWNER:
                role_obj.role = UserAppRole.ReservedRoles.OWNER
                role_update_fields.append("role")
            if set(role_obj.permissions_list or []) != set(llaves_owner):
                role_obj.permissions_list = llaves_owner
                role_update_fields.append("permissions_list")
            if not role_obj.is_active:
                role_obj.is_active = True
                role_update_fields.append("is_active")
            if getattr(role_obj, "is_deleted", False):
                role_obj.is_deleted = False
                role_update_fields.append("is_deleted")
            if getattr(role_obj, "deleted_at", None):
                role_obj.deleted_at = None
                role_update_fields.append("deleted_at")
            if role_update_fields:
                if hasattr(role_obj, "updated_at"):
                    role_update_fields.append("updated_at")
                role_obj.save(update_fields=role_update_fields)
                print(f"   🛠️  Membresía Sincronizada -> App: [{slug:<14}] | Re-inyectadas: {len(llaves_owner)} llaves JSON.")
                roles_modificados += 1
            else:
                print(f"   🛡️  Membresía Verificada -> App: [{slug:<14}] | Contiene: {len(role_obj.permissions_list or [])} llaves inmutables.")

        print("-" * 80)
        if roles_modificados > 0:
            print(f"   🚀 Aprovisionamiento exitoso: {total_llaves_sembradas} llaves mapeadas en registros desacoplados.")
        else:
            print(f"   ✓ Integridad Perfecta: Las {total_llaves_sembradas} llaves JSON de la BD coinciden con tus Manifiestos Maestros.")
        print("=" * 80 + "\n")

    except Exception as e:
        print(f"   ↳ ⚠️  Protocolo pospuesto (Excepción en el hilo transaccional): {e}\n")


class SecurityConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.security"
    verbose_name = "Seguridad y Permisos del Sistema"

    def ready(self):
        post_migrate.connect(
            sincronizar_entorno_so_axentra,
            sender=self,
            dispatch_uid="apps.security.sincronizar_entorno_so_axentra",
        )