# apps/shared/templatetags/axentra_ui.py

from django import template
from django.urls import reverse, NoReverseMatch

register = template.Library()


# =========================================================================
# ⚙️ RESOLUTORES DE NAVEGACIÓN / SHELL / WORKBENCH / HTMX
# =========================================================================

def _get_nav_value(boton, key, index=None, default=""):
    """
    Resolver universal para elementos de navegación.

    Soporta:
    - lista / tupla:
      ["icon", "name", "url", order, "permission"]

    - diccionario:
      {"icon": "...", "name": "...", "url": "...", "order": 1}

    - objeto:
      boton.icon, boton.name, boton.url
    """
    if isinstance(boton, dict):
        return boton.get(key, default)

    if isinstance(boton, (list, tuple)) and index is not None:
        try:
            return boton[index]
        except IndexError:
            return default

    return getattr(boton, key, default)


@register.simple_tag
def define_url_context(boton, request, current_funcionario=None):
    """
    Resuelve el nombre de URL del botón.

    Si la vista es contextual y lleva "sub_", inyecta el ID del funcionario.
    """
    url_name = (
        _get_nav_value(boton, "url", index=2, default="")
        or _get_nav_value(boton, "url_name", default="")
    )

    if not url_name:
        return ""

    try:
        if "sub_" in url_name and current_funcionario:
            return reverse(url_name, kwargs={"pk": current_funcionario.id})
        return reverse(url_name)
    except NoReverseMatch:
        return ""


@register.simple_tag
def define_view_name(boton):
    """Extrae el view_name o patrón lógico del elemento."""
    return (
        _get_nav_value(boton, "url", index=2, default="")
        or _get_nav_value(boton, "url_name", default="")
    )


@register.simple_tag
def define_button_icon(boton):
    """Devuelve el identificador Lucide del botón."""
    return _get_nav_value(boton, "icon", index=0, default="circle")


@register.simple_tag
def define_button_text(boton):
    """Devuelve el texto visible del botón."""
    return (
        _get_nav_value(boton, "name", index=1, default="")
        or _get_nav_value(boton, "title", default="")
        or "Enlace"
    )


@register.simple_tag
def define_button_permission(boton):
    """Devuelve el permiso asociado al botón, si existe."""
    return (
        _get_nav_value(boton, "permission", index=4, default="")
        or _get_nav_value(boton, "perm", default="")
    )


@register.simple_tag
def define_button_order(boton):
    """Devuelve el orden del botón."""
    return _get_nav_value(boton, "order", index=3, default=99)


# =========================================================================
# 🏛️ COMPONENTES REUSABLES
# =========================================================================

@register.inclusion_tag("common/tags/stats_card.html")
def stats_card(
    label,
    value,
    icon,
    hover_color="blue-600",
    value_color="gray-950",
    subtext=None,
    subtext_highlight=False,
    bg_icon="blue-50/50",
):
    """Renderiza una tarjeta contadora reutilizable."""
    return {
        "label": label,
        "value": value,
        "icon": icon,
        "hover_color": hover_color,
        "value_color": value_color,
        "subtext": subtext,
        "subtext_highlight": subtext_highlight,
        "bg_icon": bg_icon,
    }


@register.simple_tag(name="check_access")
def check_access(accesos_dict, slug_app):
    """Busca privilegios modulares activos en memoria."""
    if isinstance(accesos_dict, dict):
        return accesos_dict.get(slug_app, False)
    return False


@register.inclusion_tag("common/tags/organizational_filters.html", takes_context=True)
def organizational_filters(
    context,
    action_url="",
    clear_url="",
    placeholder_text="",
    target_id="tbody-funcionarios",
):
    """Filtros encadenados para estructura organizacional."""
    return {
        "sedes": context.get("sedes"),
        "dependencias": context.get("dependencias"),
        "current_q": context.get("current_q"),
        "current_sede": context.get("current_sede"),
        "current_dep": context.get("current_dep"),
        "action_url": action_url,
        "clear_url": clear_url,
        "placeholder_text": placeholder_text,
        "target_id": target_id,
    }


@register.simple_tag
def check_app_owner(owners_dict, app_slug):
    """Verifica si el usuario es dueño raíz de un entorno."""
    if not owners_dict or not isinstance(owners_dict, dict):
        return False
    return owners_dict.get(app_slug, False)


@register.inclusion_tag("common/tags/confirm_modal_delete.html")
def confirm_modal(
    icon="shield-alert",
    bg_icon="bg-red-50",
    icon_color="text-red-600",
    cancel_text="Cancelar",
    action_text="Confirmar Baja",
    btn_class="bg-red-600 hover:bg-red-700 text-white",
):
    """Inyecta el modal confirmador de baja."""
    return {
        "icon": icon,
        "bg_icon": bg_icon,
        "icon_color": icon_color,
        "cancel_text": cancel_text,
        "action_text": action_text,
        "btn_class": btn_class,
    }


@register.inclusion_tag("common/tags/badge_toggle_activo_inactivo.html")
def badge_toggle(is_active, toggle_url):
    """Renderiza el botón alternador de estatus conectado a HTMX."""
    return {
        "is_active": is_active,
        "toggle_url": toggle_url,
    }


@register.inclusion_tag("common/tags/user_search_component.html")
def user_search_filter(
    search_url,
    target_id="search-results-container",
    placeholder="Buscar operador por nombre o email...",
    input_name="user_q",
):
    """Renderiza el buscador reutilizable de usuarios."""
    return {
        "search_url": search_url,
        "target_id": target_id,
        "placeholder": placeholder,
        "input_name": input_name,
    }
    
