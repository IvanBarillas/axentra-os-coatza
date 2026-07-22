from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST, require_http_methods

from apps.inventory.forms import (
    AccountingAccountForm,
    AssetCategoryForm,
    AssetModelForm,
    ExpenditureObjectForm,
    ManufacturerForm,
)
from apps.inventory.selectors import CatalogSelectors
from apps.inventory.services import deactivate_catalog_entry, save_catalog_entry
from apps.security.decorators import axentra_gate_enforcer
from apps.shared.apps_config import AppIdentifier

from .common import render_inventory, run_service, success


CATALOGS = {
    "categories": {
        "title": "Categorías patrimoniales",
        "singular": "categoría patrimonial",
        "form": AssetCategoryForm,
    },
    "accounts": {
        "title": "Cuentas contables",
        "singular": "cuenta contable",
        "form": AccountingAccountForm,
    },
    "expenditure-objects": {
        "title": "Objetos del gasto",
        "singular": "objeto del gasto",
        "form": ExpenditureObjectForm,
    },
    "manufacturers": {
        "title": "Fabricantes",
        "singular": "fabricante",
        "form": ManufacturerForm,
    },
    "models": {
        "title": "Modelos",
        "singular": "modelo",
        "form": AssetModelForm,
    },
}


def _config(catalog):
    try:
        return CATALOGS[catalog]
    except KeyError as exc:
        raise Http404("El catálogo solicitado no existe.") from exc


def _catalog_url(catalog):
    return reverse("inventory:catalog_list", kwargs={"catalog": catalog})


@axentra_gate_enforcer(
    AppIdentifier.INVENTORY,
    required_fine_permission="can_manage_catalogs",
)
def catalog_list_view(request, catalog="categories"):
    config = _config(catalog)
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "active").strip().lower()
    if status not in {"active", "inactive", "all"}:
        status = "active"
    entries = CatalogSelectors.managed_entries(catalog, q=q, status=status)
    return render_inventory(
        request,
        page="inventory/pages/catalog_list.html",
        content="inventory/content/catalog_list_content.html",
        context={
            "current_inventory_view": "inventory:catalog_list",
            "catalog": catalog,
            "catalog_config": config,
            "catalogs": CATALOGS,
            "entries": entries,
            "q": q,
            "status": status,
        },
    )


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(
    AppIdentifier.INVENTORY,
    required_fine_permission="can_manage_catalogs",
)
def catalog_create_view(request, catalog):
    config = _config(catalog)
    form = config["form"](request.POST or None)
    if request.method == "POST" and form.is_valid():
        entry = run_service(
            form,
            lambda: save_catalog_entry(
                form=form,
                actor_id=request.user.pk,
                request=request,
            ),
        )
        if entry:
            success(request, f"Se creó {config['singular']} correctamente.")
            return redirect(_catalog_url(catalog))
    return render_inventory(
        request,
        page="inventory/pages/catalog_form.html",
        content="inventory/content/catalog_form_content.html",
        context={
            "current_inventory_view": "inventory:catalog_list",
            "catalog": catalog,
            "catalog_config": config,
            "form": form,
            "editing": False,
        },
        status=422 if request.method == "POST" else 200,
    )


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(
    AppIdentifier.INVENTORY,
    required_fine_permission="can_manage_catalogs",
)
def catalog_update_view(request, catalog, entry_id):
    config = _config(catalog)
    model = CatalogSelectors.MANAGED_MODELS[catalog]
    entry = get_object_or_404(model, pk=entry_id, is_deleted=False)
    form = config["form"](request.POST or None, instance=entry)
    if request.method == "POST" and form.is_valid():
        saved = run_service(
            form,
            lambda: save_catalog_entry(
                form=form,
                actor_id=request.user.pk,
                request=request,
            ),
        )
        if saved:
            success(request, f"Se actualizó {config['singular']} correctamente.")
            return redirect(_catalog_url(catalog))
    return render_inventory(
        request,
        page="inventory/pages/catalog_form.html",
        content="inventory/content/catalog_form_content.html",
        context={
            "current_inventory_view": "inventory:catalog_list",
            "catalog": catalog,
            "catalog_config": config,
            "form": form,
            "entry": entry,
            "editing": True,
        },
        status=422 if request.method == "POST" else 200,
    )


@require_POST
@axentra_gate_enforcer(
    AppIdentifier.INVENTORY,
    required_fine_permission="can_manage_catalogs",
)
def catalog_deactivate_view(request, catalog, entry_id):
    config = _config(catalog)
    model = CatalogSelectors.MANAGED_MODELS[catalog]
    entry = get_object_or_404(model, pk=entry_id, is_deleted=False)
    deactivate_catalog_entry(
        entry=entry,
        actor_id=request.user.pk,
        request=request,
    )
    success(request, f"Se desactivó {config['singular']} sin borrar su historial.")
    return redirect(_catalog_url(catalog))


__all__ = [
    "catalog_create_view",
    "catalog_deactivate_view",
    "catalog_list_view",
    "catalog_update_view",
]
