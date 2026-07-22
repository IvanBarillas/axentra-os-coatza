from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import render

from apps.inventory.services.exceptions import InventoryServiceError


def is_htmx(request):
    return str(request.headers.get("HX-Request", "")).lower() == "true"


def render_inventory(request, *, page, content, context, status=200):
    base = {
        "modulo_actual": "inventory",
        "show_module_sidebar": True,
    }
    base.update(context)
    htmx_request = is_htmx(request)
    if htmx_request and request.headers.get("HX-Target", "") == "workbench":
        template = "inventory/workbench/module_workbench.html"
        base["inventory_content_template"] = content
    elif htmx_request:
        template = content
    else:
        template = page

    # HTMX no intercambia por defecto respuestas 4xx. En una validación 422
    # necesitamos que sustituya el formulario para mostrar sus errores. La
    # navegación tradicional conserva el código semántico 422.
    response_status = 200 if htmx_request and status == 422 else status
    return render(request, template, base, status=response_status)


def form_error(form, exc):
    if isinstance(exc, ValidationError):
        if hasattr(exc, "message_dict"):
            for field, errors in exc.message_dict.items():
                target = field if field in form.fields else None
                for error in errors:
                    form.add_error(target, error)
        else:
            form.add_error(None, exc)
    else:
        form.add_error(None, str(exc))


def run_service(form, callback):
    try:
        return callback()
    except (InventoryServiceError, ValidationError) as exc:
        form_error(form, exc)
        return None


def success(request, text):
    messages.success(request, text)


def selector_or_404(callback):
    try:
        return callback()
    except Exception as exc:
        if exc.__class__.__name__ == "DoesNotExist":
            raise Http404 from exc
        raise


def apply_directory_choices(form):
    from apps.inventory.selectors import CoreDirectorySelectors

    choices = CoreDirectorySelectors.form_choices()
    mapping = {
        "requested_department_id": "department_choices",
        "department_id": "department_choices",
        "destination_department_id": "department_choices",
        "origin_department_id": "department_choices",
        "observed_department_id": "department_choices",
        "requested_site_id": "site_choices",
        "site_id": "site_choices",
        "destination_site_id": "site_choices",
        "origin_site_id": "site_choices",
        "observed_site_id": "site_choices",
        "requested_area_id": "area_choices",
        "area_id": "area_choices",
        "destination_area_id": "area_choices",
        "origin_area_id": "area_choices",
        "observed_area_id": "area_choices",
        "proposed_custodian_id": "user_choices",
        "custodian_id": "user_choices",
        "user_id": "user_choices",
        "borrower_id": "user_choices",
        "returned_by_id": "user_choices",
        "observed_custodian_id": "user_choices",
    }
    for field, source in mapping.items():
        if field in form.fields:
            form.fields[field].choices = [("", "--- Seleccione ---"), *choices[source]]
    return form
