# apps/shared/templatetags/axentra_ui.py
from django import template

register = template.Library()

@register.inclusion_tag('common/tags/dashboard_header.html')
def dashboard_header(badge_text, title, description, modulo_actual, badge_class=None, status_text="Online", status_color="blue-600", status_pulse=True, mostrar_permisos=True, accent_color="blue-600"):
    """Renderiza el encabezado de gobernanza unificado de Axentra OS."""
    return {
        'badge_text': badge_text,
        'title': title,
        'description': description,
        'modulo_actual': modulo_actual,
        'badge_class': badge_class,
        'status_text': status_text,
        'status_color': status_color,
        'status_pulse': status_pulse,
        'mostrar_permisos': mostrar_permisos,
        'accent_color': accent_color,
    }

@register.inclusion_tag('common/tags/stats_card.html')
def stats_card(label, value, icon, hover_color="blue-600", value_color="gray-950", subtext=None, subtext_highlight=False, bg_icon="blue-50/50"):
    """Renderiza una tarjeta contadora demográfica adaptativa mapeada a Lucide."""
    return {
        'label': label,
        'value': value,
        'icon': icon,  # Recibe identificadores de Lucide (ej: 'users', 'activity')
        'hover_color': hover_color,
        'value_color': value_color,
        'subtext': subtext,
        'subtext_highlight': subtext_highlight,
        'bg_icon': bg_icon
    }
    
@register.inclusion_tag('common/tags/action_card.html')
def action_card(title, description, url_destination, icon, hover_color="blue-600", target_count=None, target_label="", count_color=None, bg_icon="blue-50/50", button_text="Abrir Módulo"):
    """Renderiza un mosaico interactivo para disparar flujos o llamadas asíncronas HTMX."""
    return {
        'title': title,
        'description': description,
        'url_destination': url_destination,
        'icon': icon,  # Recibe identificadores de Lucide (ej: 'user-plus')
        'hover_color': hover_color,
        'target_count': target_count,
        'target_label': target_label,
        'count_color': count_color,
        'bg_icon': bg_icon,
        'button_text': button_text
    }

@register.simple_tag(name='check_access')
def check_access(accesos_dict, slug_app):
    """Buscador atómico en RAM de privilegios modulares activos."""
    if isinstance(accesos_dict, dict):
        return accesos_dict.get(slug_app, False)
    return False

@register.inclusion_tag('common/tags/organizational_filters.html', takes_context=True)
def organizational_filters(context, action_url="", clear_url="", placeholder_text="", target_id="tbody-funcionarios"):
    """Filtros encadenados para la estructura jerárquica del Ayuntamiento con Target dinámico."""
    return {
        'sedes': context.get('sedes'),
        'dependencias': context.get('dependencias'),
        'current_q': context.get('current_q'),
        'current_sede': context.get('current_sede'),
        'current_dep': context.get('current_dep'),
        'action_url': action_url,
        'clear_url': clear_url,
        'placeholder_text': placeholder_text,
        'target_id': target_id,  #  Mapeo de contenedor flexible
    }
    
@register.simple_tag
def check_app_owner(owners_dict, app_slug):
    """Centinela perimetral para verificar si el usuario es el dueño raíz de un entorno."""
    if not owners_dict or not isinstance(owners_dict, dict):
        return False
    return owners_dict.get(app_slug, False)

# Boton para confirmar eliminar registros
@register.inclusion_tag('common/tags/confirm_modal_delete.html')
def confirm_modal(icon="shield-alert", bg_icon="bg-red-50", icon_color="text-red-600", cancel_text="Cancelar", action_text="Confirmar Baja", btn_class="bg-red-600 hover:bg-red-700 text-white"):
    """Inyecta el Confirmador Táctico perimetral en la raíz del Layout."""
    return {
        'icon': icon,
        'bg_icon': bg_icon,
        'icon_color': icon_color,
        'cancel_text': cancel_text,
        'action_text': action_text,
        'btn_class': btn_class,
    }
    
# badge para activar o desactivar 
@register.inclusion_tag('common/tags/badge_toggle_activo_inactivo.html')
def badge_toggle(is_active, toggle_url):
    """Renderiza el botón alternador de estatus operativo conectado a HTMX pipelines."""
    return {
        'is_active': is_active,
        'toggle_url': toggle_url,
    }