# apps/inventory/views/common.py

from uuid import UUID

from django.contrib import messages
from django.core.exceptions import (
    ObjectDoesNotExist,
    PermissionDenied,
    ValidationError,
)
from django.http import Http404
from django.shortcuts import render

from apps.inventory.integrations.core_directory import (
    CoreDirectoryError,
    get_module_role,
    get_user_identity,
    get_user_organizational_context,
)
from apps.inventory.services.exceptions import InventoryServiceError


def is_htmx(request):
    return (
        str(request.headers.get("HX-Request", ""))
        .strip()
        .lower()
        == "true"
    )


def render_inventory(
    request,
    *,
    page,
    content,
    context,
    status=200,
):
    base = {
        "modulo_actual": "inventory",
        "show_module_sidebar": True,
    }
    base.update(context)

    hx_target = str(
        request.headers.get("HX-Target", "")
    ).strip()

    if is_htmx(request) and hx_target == "workbench":
        template = "inventory/workbench/module_workbench.html"
        base["inventory_content_template"] = content
    elif is_htmx(request):
        template = content
    else:
        template = page

    return render(request, template, base, status=status)


def form_error(form, exc):
    if isinstance(exc, ValidationError):
        if hasattr(exc, "message_dict"):
            for field, errors in exc.message_dict.items():
                target = field if field in form.fields else None
                for error in errors:
                    form.add_error(target, error)
        else:
            form.add_error(None, exc)
        return

    details = getattr(exc, "details", None) or {}
    domain_errors = details.get("errors", {})

    if isinstance(domain_errors, dict) and domain_errors:
        for field, errors in domain_errors.items():
            target = field if field in form.fields else None
            if not isinstance(errors, (list, tuple)):
                errors = [errors]
            for error in errors:
                form.add_error(target, str(error))
        return

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
    except ObjectDoesNotExist as exc:
        # No distinguimos entre inexistente y fuera del alcance autorizado.
        raise Http404 from exc


def _uuid_or_none(value):
    if value in (None, ""):
        return None

    try:
        return value if isinstance(value, UUID) else UUID(str(value))
    except (TypeError, ValueError, AttributeError):
        return None


def _selected_value(form, field_name):
    if field_name not in form.fields:
        return None

    if form.is_bound:
        return form.data.get(form.add_prefix(field_name))

    value = form.initial.get(field_name)
    if value not in (None, ""):
        return getattr(value, "pk", value)

    return form.fields[field_name].initial


def _department_field(form):
    for field_name in (
        "requested_department_id",
        "destination_department_id",
        "origin_department_id",
        "department_id",
    ):
        if field_name in form.fields:
            return field_name
    return None


def _site_field(form):
    for field_name in (
        "requested_site_id",
        "destination_site_id",
        "origin_site_id",
        "site_id",
    ):
        if field_name in form.fields:
            return field_name
    return None


def apply_directory_choices(form, *, actor_id):
    """Carga opciones del Core aplicando el alcance del usuario.

    El navegador nunca decide si puede operar otra dependencia. Si el usuario
    no tiene permiso transversal, su dependencia se fija como única opción.
    El servicio vuelve a validar esta regla dentro de la transacción.
    """

    from apps.inventory.selectors import CoreDirectorySelectors

    try:
        actor = get_user_identity(actor_id)
        role = get_module_role(actor.id)
        organization = get_user_organizational_context(
            actor.id,
            require_profile=not actor.has_global_bypass,
        )
    except CoreDirectoryError as exc:
        raise PermissionDenied(str(exc)) from exc

    if not actor.has_global_bypass and not role:
        raise PermissionDenied(
            "El usuario no tiene un rol activo dentro de Inventory."
        )

    can_select_any_department = bool(
        actor.has_global_bypass
        or (
            role
            and role.has_permission(
                "can_create_intake_for_any_department"
            )
        )
    )

    department_field = _department_field(form)
    site_field = _site_field(form)

    selected_department_id = _uuid_or_none(
        _selected_value(form, department_field)
        if department_field else None
    )
    selected_site_id = _uuid_or_none(
        _selected_value(form, site_field)
        if site_field else None
    )

    if not can_select_any_department:
        selected_department_id = organization.department_id
        if not selected_department_id:
            raise PermissionDenied(
                "El usuario no tiene una dependencia activa para operar."
            )

        if department_field and not form.is_bound:
            form.fields[department_field].initial = (
                selected_department_id
            )

    choices = CoreDirectorySelectors.form_choices(
        department_id=selected_department_id,
        site_id=selected_site_id,
    )

    if not can_select_any_department:
        choices["department_choices"] = [
            item
            for item in choices["department_choices"]
            if _uuid_or_none(item[0]) == selected_department_id
        ]

    mapping = {
        "requested_department_id": "department_choices",
        "department_id": "department_choices",
        "destination_department_id": "department_choices",
        "origin_department_id": "department_choices",
        "requested_site_id": "site_choices",
        "site_id": "site_choices",
        "destination_site_id": "site_choices",
        "origin_site_id": "site_choices",
        "requested_area_id": "area_choices",
        "area_id": "area_choices",
        "destination_area_id": "area_choices",
        "origin_area_id": "area_choices",
        "proposed_custodian_id": "user_choices",
        "custodian_id": "user_choices",
        "user_id": "user_choices",
        "borrower_id": "user_choices",
        "returned_by_id": "user_choices",
    }

    for field_name, source in mapping.items():
        if field_name not in form.fields:
            continue

        form.fields[field_name].choices = [
            ("", "--- Seleccione ---"),
            *choices[source],
        ]

    return form


__all__ = [
    "apply_directory_choices",
    "form_error",
    "is_htmx",
    "render_inventory",
    "run_service",
    "selector_or_404",
    "success",
]