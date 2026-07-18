"""Utilidades internas de la capa de servicios de Inventory."""

from django.core.exceptions import ValidationError


def require_text(value, label):
    value = (value or "").strip()
    if not value:
        raise ValidationError({label: "Este dato es obligatorio."})
    return value


def lock_instance(model, object_id):
    try:
        return model.objects.select_for_update().get(pk=object_id, is_deleted=False)
    except model.DoesNotExist as exc:
        raise ValidationError(f"No se encontró {model._meta.verbose_name}.") from exc


def validate_and_save(instance, *, update_fields=None):
    instance.full_clean()
    instance.save(update_fields=update_fields)
    return instance


def transition(instance, *, expected, target, status_field="status"):
    current = getattr(instance, status_field)
    allowed = {expected} if isinstance(expected, str) else set(expected)
    if current not in allowed:
        raise ValidationError(
            {status_field: f"Transición inválida: {current} → {target}."}
        )
    setattr(instance, status_field, target)
    return current
