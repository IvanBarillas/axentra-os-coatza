from django.shortcuts import redirect
from django.views.decorators.http import require_http_methods

from apps.inventory.forms.custody_signed_forms import (
    CustodySignedDocumentForm,
)
from apps.inventory.selectors import CustodySelectors
from apps.inventory.services.custody_simple_service import (
    activate_custody_with_signed_document,
)
from apps.security.decorators import axentra_gate_enforcer
from apps.shared.apps_config import AppIdentifier

from .access import custody_scope, require_any_permission
from .common import render_inventory, run_service, selector_or_404, success


def _visible_custody(request, custody_id):
    scope, department_id = custody_scope(request)
    return selector_or_404(
        lambda: CustodySelectors.obtener(
            custody_id,
            scope=scope,
            actor_id=request.user.pk,
            department_id=department_id,
        )
    )


@axentra_gate_enforcer(
    AppIdentifier.INVENTORY,
    required_fine_permission="has_access_module",
)
def custody_print_view(request, custody_id):
    require_any_permission(
        request,
        "can_manage_custody",
        "can_accept_custody",
    )
    custody = _visible_custody(request, custody_id)
    return render_inventory(
        request,
        page="inventory/pages/custody_print.html",
        content="inventory/content/custody_print_content.html",
        context={
            "current_inventory_view": "inventory:custody_list",
            "custody": custody,
            "print_view": True,
        },
    )


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(
    AppIdentifier.INVENTORY,
    required_fine_permission="can_manage_custody",
)
def custody_signed_upload_view(request, custody_id):
    custody = _visible_custody(request, custody_id)
    form = CustodySignedDocumentForm(
        request.POST or None,
        request.FILES or None,
    )
    if request.method == "POST" and form.is_valid():
        result = run_service(
            form,
            lambda: activate_custody_with_signed_document(
                custody_id=custody.id,
                signed_at=form.cleaned_data["signed_at"],
                uploaded_file=form.cleaned_data["file"],
                notes=form.cleaned_data.get("notes", ""),
                actor_id=request.user.pk,
                request=request,
            ),
        )
        if result:
            success(
                request,
                "Resguardo firmado agregado y responsabilidad activada.",
            )
            return redirect(
                "inventory:custody_detail",
                custody_id=custody.id,
            )
    return render_inventory(
        request,
        page="inventory/pages/custody_signed_form.html",
        content="inventory/content/custody_signed_form_content.html",
        context={
            "current_inventory_view": "inventory:custody_list",
            "custody": custody,
            "form": form,
        },
        status=422 if request.method == "POST" else 200,
    )


__all__ = ["custody_print_view", "custody_signed_upload_view"]
