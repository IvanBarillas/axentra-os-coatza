from django.db import transaction

from apps.inventory.models import InventoryAuditAction
from apps.inventory.services.audit_service import log_model_change, model_snapshot


@transaction.atomic
def save_catalog_entry(*, form, actor_id, request=None):
    """Crea o actualiza un catálogo y conserva evidencia del cambio."""
    instance = form.instance
    creating = instance._state.adding
    before = {}
    if not creating:
        current = type(instance).objects.select_for_update().get(pk=instance.pk)
        before = model_snapshot(current)

    entry = form.save(commit=False)
    entry.full_clean()
    entry.save()

    log_model_change(
        action=(InventoryAuditAction.CREATE if creating else InventoryAuditAction.UPDATE),
        summary=(
            f"Creación de catálogo: {entry}"
            if creating
            else f"Actualización de catálogo: {entry}"
        ),
        target=entry,
        actor_id=actor_id,
        before=before,
        after=entry,
        request=request,
    )
    return entry


@transaction.atomic
def deactivate_catalog_entry(*, entry, actor_id, request=None):
    """Desactiva sin borrar para preservar referencias históricas."""
    locked = type(entry).objects.select_for_update().get(pk=entry.pk)
    before = model_snapshot(locked)
    locked.is_active = False
    locked.full_clean()
    locked.save(update_fields=["is_active", "updated_at"])
    log_model_change(
        action=InventoryAuditAction.UPDATE,
        summary=f"Desactivación de catálogo: {locked}",
        target=locked,
        actor_id=actor_id,
        before=before,
        after=locked,
        request=request,
    )
    return locked


__all__ = ["deactivate_catalog_entry", "save_catalog_entry"]
