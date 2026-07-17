# apps/inventory/views/inventory_views.py

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import FieldDoesNotExist
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.inventory.forms import AssetForm
from apps.inventory.models import (
    Asset,
    AssetCategory,
    AssetDocument,
    AssetOperationalStatus,
    AssetPatrimonialStatus,
    AssetPhoto,
    InventoryDocumentOwnerType,
)
from apps.inventory.selectors import AssetSelectors


def _is_htmx(request):
    return request.headers.get("HX-Request") == "true"


def _hx_target(request):
    return request.headers.get("HX-Target", "")


def _model_has_field(model, field_name):
    """
    Comprueba si un modelo tiene un campo o relación determinada.
    """

    try:
        model._meta.get_field(field_name)
        return True
    except FieldDoesNotExist:
        return False


def _existing_asset_relations(relation_names):
    """
    Devuelve únicamente relaciones que realmente existen en Asset.

    Permite soportar la transición desde los nombres anteriores:

        sede
        dependencia
        area

    hacia los nombres nuevos:

        current_sede
        current_dependencia
        current_area
    """

    return [
        relation_name
        for relation_name in relation_names
        if _model_has_field(Asset, relation_name)
    ]


def _asset_detail_queryset():
    """
    QuerySet optimizado para mostrar el expediente completo del activo.
    """

    select_related_candidates = [
        "source_intake_request",
        "category",
        "expenditure_object",
        "accounting_account",
        "manufacturer",
        "model",
        "supplier",
        "contract",

        # Adscripción de origen.
        "origin_sede",
        "origin_dependencia",
        "origin_area",

        # Adscripción actual.
        "current_sede",
        "current_dependencia",
        "current_area",
        "current_custodian",

        # Compatibilidad temporal con nombres anteriores.
        "sede",
        "dependencia",
        "area",

        # Registro.
        "registered_by",
    ]

    prefetch_related_candidates = [
        "movements",
        "loans",
        "custody_assignments",
        "depreciation_records",
        "disposal_requests",
        "physical_audit_items",
        "audit_logs",
    ]

    select_related_fields = _existing_asset_relations(
        select_related_candidates
    )
    prefetch_related_fields = _existing_asset_relations(
        prefetch_related_candidates
    )

    queryset = Asset.objects.all()

    if select_related_fields:
        queryset = queryset.select_related(*select_related_fields)

    if prefetch_related_fields:
        queryset = queryset.prefetch_related(
            *prefetch_related_fields
        )

    return queryset


def _get_asset_documents(asset):
    """
    Obtiene documentos mediante la referencia desacoplada owner_type/owner_id.
    """

    owner_type = getattr(
        InventoryDocumentOwnerType,
        "ASSET",
        "ASSET",
    )

    return (
        AssetDocument.objects
        .filter(
            owner_type=owner_type,
            owner_id=asset.id,
            is_deleted=False,
        )
        .select_related(
            "uploaded_by",
            "validated_by",
        )
        .order_by("-created_at")
    )


def _get_asset_photos(asset):
    """
    Obtiene fotografías mediante la referencia desacoplada owner_type/owner_id.
    """

    owner_type = getattr(
        InventoryDocumentOwnerType,
        "ASSET",
        "ASSET",
    )

    return (
        AssetPhoto.objects
        .filter(
            owner_type=owner_type,
            owner_id=asset.id,
            is_deleted=False,
        )
        .select_related(
            "uploaded_by",
        )
        .order_by("-created_at")
    )


def _build_asset_detail_context(asset):
    documents = _get_asset_documents(asset)
    photos = _get_asset_photos(asset)

    # Compatibilidad temporal con plantillas anteriores que utilicen:
    #
    #     asset.documents.all
    #     asset.photos.all
    #
    # Estas propiedades no se guardan en la base de datos.
    asset.documents = documents
    asset.photos = photos

    return {
        "modulo_actual": "inventory",
        "show_module_sidebar": True,
        "current_inventory_view": "inventory:asset_list",
        "asset": asset,
        "documents": documents,
        "photos": photos,
    }


@login_required
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
                "inventory/workbench/"
                "inventory_dashboard_workbench.html",
                context,
            )

        if target == "page-content":
            return render(
                request,
                "inventory/content/"
                "inventory_dashboard_content.html",
                context,
            )

    return render(
        request,
        "inventory/pages/inventory_dashboard.html",
        context,
    )


@login_required
def asset_list_view(request):
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    operational_status = (
        request.GET.get("operational_status", "").strip()
    )
    category_id = request.GET.get("category", "").strip()

    assets = AssetSelectors.listar_activos(
        q=q,
        status=status,
        operational_status=operational_status,
        category_id=category_id,
    )

    context = {
        "modulo_actual": "inventory",
        "show_module_sidebar": True,
        "current_inventory_view": "inventory:asset_list",
        "assets": assets,
        "q": q,
        "status": status,
        "operational_status": operational_status,
        "category_id": category_id,
        "categories": (
            AssetCategory.objects
            .filter(
                is_active=True,
                is_deleted=False,
            )
            .order_by("name")
        ),
        "statuses": AssetPatrimonialStatus.choices,
        "operational_statuses": AssetOperationalStatus.choices,
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


@login_required
def asset_detail_view(request, asset_id):
    asset = get_object_or_404(
        _asset_detail_queryset(),
        id=asset_id,
        is_deleted=False,
    )

    context = _build_asset_detail_context(asset)

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


@login_required
def asset_create_view(request):
    """
    Alta directa temporal para desarrollo.

    En la implementación definitiva esta vista deberá crear una
    AssetIntakeRequest y enviarla al flujo de aprobación. La creación del Asset
    oficial corresponderá al servicio de aprobación patrimonial.
    """

    if request.method == "POST":
        form = AssetForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():
            with transaction.atomic():
                asset = form.save(commit=False)

                if (
                    _model_has_field(Asset, "registered_by")
                    and not asset.registered_by_id
                ):
                    asset.registered_by = request.user

                asset.full_clean()
                asset.save()

                form.save_m2m()

            messages.success(
                request,
                (
                    f"Activo {asset.display_inventory_number} "
                    "registrado correctamente."
                ),
            )

            detail_url = reverse(
                "inventory:asset_detail",
                kwargs={"asset_id": asset.id},
            )

            if _is_htmx(request):
                context = _build_asset_detail_context(asset)

                response = render(
                    request,
                    "inventory/content/asset_detail_content.html",
                    context,
                )
                response["HX-Push-Url"] = detail_url

                return response

            return redirect(detail_url)

        messages.error(
            request,
            (
                "No se pudo registrar el activo. "
                "Revisa los campos marcados."
            ),
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


