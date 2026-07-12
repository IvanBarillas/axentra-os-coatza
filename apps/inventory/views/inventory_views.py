# apps/inventory/inventory_views.py

from django.shortcuts import render


# apps/inventory/views.py

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.inventory.forms import AssetForm
from apps.inventory.models import Asset, AssetCategory, AssetLifecycleStatus
from apps.inventory.selectors import AssetSelectors


def _is_htmx(request):
    return request.headers.get("HX-Request") == "true"


def _hx_target(request):
    return request.headers.get("HX-Target", "")


def inventory_dashboard_view(request):
    context = {
        "modulo_actual": "inventory",
        "show_module_sidebar": True,
        "current_inventory_view": "inventory:dashboard",
        "metrics": AssetSelectors.dashboard_metrics(),
    }

    if _is_htmx(request):
        target = _hx_target(request)

        if target == "workbench":
            return render(
                request,
                "inventory/workbench/inventory_dashboard_workbench.html",
                context,
            )

        if target == "page-content":
            return render(
                request,
                "inventory/content/inventory_dashboard_content.html",
                context,
            )

    return render(
        request,
        "inventory/pages/inventory_dashboard.html",
        context,
    )


def asset_list_view(request):
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    category_id = request.GET.get("category", "").strip()

    assets = AssetSelectors.listar_activos(
        q=q,
        status=status,
        category_id=category_id,
    )

    context = {
        "modulo_actual": "inventory",
        "show_module_sidebar": True,
        "current_inventory_view": "inventory:asset_list",
        "assets": assets,
        "q": q,
        "status": status,
        "category_id": category_id,
        "categories": AssetCategory.objects.filter(
            is_active=True,
            is_deleted=False,
        ).order_by("name"),
        "statuses": AssetLifecycleStatus.choices,
    }

    if _is_htmx(request):
        target = _hx_target(request)

        if target == "workbench":
            return render(
                request,
                "inventory/workbench/asset_list_workbench.html",
                context,
            )

        if target == "page-content":
            return render(
                request,
                "inventory/content/asset_list_content.html",
                context,
            )

    return render(
        request,
        "inventory/pages/asset_list.html",
        context,
    )


def asset_detail_view(request, asset_id):
    asset = get_object_or_404(
        Asset.objects.select_related(
            "category",
            "accounting_account",
            "manufacturer",
            "model",
            "supplier",
            "contract",
            "sede",
            "dependencia",
            "area",
            "current_custodian",
        ),
        id=asset_id,
        is_deleted=False,
    )

    context = {
        "modulo_actual": "inventory",
        "show_module_sidebar": True,
        "current_inventory_view": "inventory:asset_list",
        "asset": asset,
    }

    if _is_htmx(request):
        target = _hx_target(request)

        if target == "workbench":
            return render(
                request,
                "inventory/workbench/asset_detail_workbench.html",
                context,
            )

        if target == "page-content":
            return render(
                request,
                "inventory/content/asset_detail_content.html",
                context,
            )

    return render(
        request,
        "inventory/pages/asset_detail.html",
        context,
    )


def asset_create_view(request):
    if request.method == "POST":
        form = AssetForm(request.POST)

        if form.is_valid():
            asset = form.save()
            messages.success(
                request,
                f"Activo {asset.inventory_number} registrado correctamente.",
            )

            detail_url = reverse(
                "inventory:asset_detail",
                kwargs={"asset_id": asset.id},
            )

            if _is_htmx(request):
                response = redirect(detail_url)
                response["HX-Redirect"] = detail_url
                return response

            return redirect(detail_url)

        messages.error(
            request,
            "No se pudo registrar el activo. Revisa los campos marcados.",
        )
    else:
        form = AssetForm()

    context = {
        "modulo_actual": "inventory",
        "show_module_sidebar": True,
        "current_inventory_view": "inventory:asset_create",
        "form": form,
    }

    if _is_htmx(request):
        target = _hx_target(request)

        if target == "workbench":
            return render(
                request,
                "inventory/workbench/asset_form_workbench.html",
                context,
            )

        if target == "page-content":
            return render(
                request,
                "inventory/content/asset_form_content.html",
                context,
            )

    return render(
        request,
        "inventory/pages/asset_form.html",
        context,
    )
    

