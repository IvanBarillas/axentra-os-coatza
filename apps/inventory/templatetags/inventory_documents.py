from django import template

from apps.inventory.documents import get_acknowledgement_state


register = template.Library()


@register.simple_tag
def acknowledgement_state(owner_type, owner_id, generated_type):
    return get_acknowledgement_state(
        owner_type=owner_type,
        owner_id=owner_id,
        generated_type=generated_type,
    )


__all__ = ["acknowledgement_state"]
