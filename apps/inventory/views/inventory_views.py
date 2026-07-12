# apps/inventory/inventory_views.py

from django.shortcuts import render


def inventory_dashboard_view(request):
    context = {
        "modulo_actual": "inventory",
        "show_module_sidebar": True,
        "current_inventory_view": "inventory:dashboard",
    }

    if request.headers.get("HX-Request"):
        target = request.headers.get("HX-Target")

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