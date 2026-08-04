from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Count, OuterRef, Q, Subquery
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from apps.inventory.forms.custody_document_forms import (
    CustodyDocumentCreateForm,
    CustodyDocumentReleaseForm,
    CustodyDocumentReplaceForm,
)
from apps.inventory.documents import get_acknowledgement_state
from apps.inventory.integrations import core_directory
from apps.inventory.models import (
    CustodyAssignment,
    CustodyDocument,
    CustodyDocumentItem,
    CustodyDocumentStatus,
    CustodyDocumentType,
    CustodyStatus,
)
from apps.inventory.selectors import (
    AssetSelectors,
    CoreDirectorySelectors,
)
from apps.inventory.services.custody_document_service import (
    OPEN_STATUSES,
    close_custody_document,
    create_custody_document,
    create_custody_release_batch,
    create_custody_release_document,
    create_custody_releases_from_assignments,
    replace_custody_document,
)
from apps.inventory.services.exceptions import InventoryServiceError
from apps.security.decorators import axentra_gate_enforcer
from apps.shared.apps_config import AppIdentifier

from .common import render_inventory, run_service, selector_or_404, success


def _department_choices():
    return [
        (str(item.id), f"{item.code or 'SIN-CÓDIGO'} · {item.name}")
        for item in CoreDirectorySelectors.departments()
    ]


def _group_document_rows(documents):
    """Agrupa documentos individuales sin perder su expediente propio."""
    groups = {}
    for document in documents:
        key = (document.document_type, document.batch_id)
        groups.setdefault(key, []).append(document)

    rows = []
    active_statuses = {CustodyStatus.ACTIVE, CustodyStatus.RETURN_PENDING}
    historical_statuses = {CustodyStatus.RETURNED, CustodyStatus.CANCELLED}
    for siblings in groups.values():
        siblings.sort(key=lambda item: (item.batch_position, item.prepared_at))
        representative = siblings[0]
        custodies = [
            item.custody_assignment
            for document in siblings
            for item in document.items.all()
        ]
        active_count = sum(
            custody.status in active_statuses for custody in custodies
        )
        historical_count = sum(
            custody.status in historical_statuses for custody in custodies
        )
        total = len(custodies) or len(siblings)
        if total and historical_count == total:
            status_label = "Finalizado"
            status_color = "slate"
        elif total and active_count == total:
            status_label = "Vigente"
            status_color = "emerald"
        else:
            status_label = f"En proceso · {active_count} de {total} vigentes"
            status_color = "amber"
        rows.append({
            "document": representative,
            "siblings": siblings,
            "document_count": len(siblings),
            "active_count": active_count,
            "total": total,
            "status_label": status_label,
            "status_color": status_color,
        })
    return rows


def _configure_dynamic_choices(form, department_id, user_id=""):
    form.fields["department_id"].choices = _department_choices()
    form.fields["department_id"].widget.attrs.update({
        "hx-get": reverse("inventory:custody_document_create"),
        "hx-trigger": "change",
        "hx-target": "#page-content",
        "hx-swap": "innerHTML",
        "hx-push-url": "true",
    })
    if not department_id:
        return []

    busy_ids = CustodyAssignment.objects.filter(
        is_deleted=False,
        status__in=OPEN_STATUSES,
    ).values_list("asset_id", flat=True)
    assets = list(
        AssetSelectors.listar_activos(
            department_id=department_id,
            capitalizable="",
        )
        .exclude(id__in=busy_ids)
        .order_by("official_inventory_number", "name")
    )
    form.fields["asset_ids"].choices = [
        (
            str(asset.id),
            f"{asset.display_inventory_number} · {asset.name}"
            + (f" · Serie {asset.serial_number}" if asset.serial_number else ""),
        )
        for asset in assets
    ]
    users = CoreDirectorySelectors.users(department_id=department_id)
    form.fields["assigned_to_id"].choices = [
        (
            str(item.id),
            f"{item.display_name} · {item.email}"
            if item.email else item.display_name,
        )
        for item in users
    ]
    if user_id and not any(
        str(value) == str(user_id)
        for value, _label in form.fields["assigned_to_id"].choices
    ):
        try:
            identity = core_directory.get_user_identity(user_id)
        except core_directory.CoreDirectoryError:
            return assets
        form.fields["assigned_to_id"].choices.append(
            (
                str(identity.id),
                f"{identity.display_name} · {identity.normalized_email}",
            )
        )
    return assets


def _create_document_form(request, department_id):
    """Conserva visualmente la dependencia elegida al recargar la cascada."""
    form = CustodyDocumentCreateForm(
        request.POST or None,
        initial=(
            {"department_id": department_id}
            if request.method == "GET" and department_id
            else None
        ),
    )
    if not form.is_bound and department_id:
        form.fields["department_id"].initial = department_id
    return form


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(
    AppIdentifier.INVENTORY,
    required_fine_permission="can_manage_custody",
)
def custody_document_create_view(request):
    department_id = (
        request.POST.get("department_id", "").strip()
        or request.GET.get("department_id", "").strip()
    )
    user_id = request.POST.get("assigned_to_id", "").strip()
    form = _create_document_form(request, department_id)
    available_assets = _configure_dynamic_choices(
        form,
        department_id,
        user_id,
    )
    if not getattr(request, "axentra_is_root", False):
        form.fields.pop("bypass_reason", None)
    selected_asset_ids = set(request.POST.getlist("asset_ids"))

    if request.method == "POST" and form.is_valid():
        document = run_service(
            form,
            lambda: create_custody_document(
                department_id=form.cleaned_data["department_id"],
                asset_ids=form.cleaned_asset_ids(),
                assignee_mode=form.cleaned_data["assignee_mode"],
                assigned_to_id=form.cleaned_data.get("assigned_to_id"),
                notes=form.cleaned_data.get("notes", ""),
                bypass_reason=form.cleaned_data.get("bypass_reason", ""),
                actor_id=request.user.pk,
                request=request,
            ),
        )
        if document:
            quantity = document.batch_size
            success(
                request,
                (
                    f"Se crearon {quantity} resguardos individuales."
                    if quantity > 1
                    else f"Resguardo {document.folio} creado correctamente."
                ),
            )
            return redirect(
                "inventory:custody_document_detail",
                document_id=document.id,
            )

    return render_inventory(
        request,
        page="inventory/pages/custody_document_form.html",
        content="inventory/content/custody_document_form_content.html",
        context={
            "current_inventory_view": "inventory:custody_list",
            "form": form,
            "selected_department_id": department_id,
            "available_asset_rows": [
                {
                    "asset": asset,
                    "selected": str(asset.id) in selected_asset_ids,
                }
                for asset in available_assets
            ],
        },
        status=422 if request.method == "POST" else 200,
    )


@axentra_gate_enforcer(
    AppIdentifier.INVENTORY,
    required_fine_permission="can_manage_custody",
)
def custody_document_list_view(request):
    tab = request.GET.get("tab", "current").strip().lower()
    documents = (
        CustodyDocument.objects.filter(is_deleted=False)
        .select_related("prepared_by", "closed_by")
        .prefetch_related("items__custody_assignment")
        .annotate(asset_count=Count("items", distinct=True))
    )
    historical = {
        CustodyDocumentStatus.CLOSED,
        CustodyDocumentStatus.REPLACED,
        CustodyDocumentStatus.CANCELLED,
    }
    release_custodies = None
    bulk_release_form = CustodyDocumentReleaseForm(
        request.POST or None,
    ) if tab == "release_bulk" else None
    department_filter = request.GET.get("department_id", "").strip()
    search_query = request.GET.get("q", "").strip()
    if tab in {"release_individual", "release_bulk"}:
        pending_release = CustodyDocumentItem.objects.filter(
            custody_assignment_id=OuterRef("pk"),
            is_deleted=False,
            document__is_deleted=False,
            document__document_type=CustodyDocumentType.RELEASE,
            document__status__in={
                CustodyDocumentStatus.DRAFT,
                CustodyDocumentStatus.IN_PROCESS,
            },
        ).order_by("-document__prepared_at")
        release_custodies = CustodyAssignment.objects.filter(
            is_deleted=False,
            status__in={CustodyStatus.ACTIVE, CustodyStatus.RETURN_PENDING},
        ).select_related(
            "asset", "dependencia", "assigned_to",
        ).annotate(
            pending_release_id=Subquery(
                pending_release.values("document_id")[:1],
            ),
        )
        if department_filter:
            release_custodies = release_custodies.filter(
                dependencia_id=department_filter,
            )
        if search_query:
            release_custodies = release_custodies.filter(
                Q(folio__icontains=search_query)
                | Q(asset__official_inventory_number__icontains=search_query)
                | Q(asset__internal_inventory_number__icontains=search_query)
                | Q(asset__name__icontains=search_query)
                | Q(assigned_to_name_snapshot__icontains=search_query)
            )
        release_custodies = release_custodies.order_by(
            "dependencia_name_snapshot", "assigned_to_name_snapshot", "folio",
        )

    if (
        request.method == "POST"
        and tab == "release_bulk"
        and bulk_release_form.is_valid()
    ):
        selected_ids = request.POST.getlist("custody_ids")
        release = run_service(
            bulk_release_form,
            lambda: create_custody_releases_from_assignments(
                custody_ids=selected_ids,
                reason=bulk_release_form.cleaned_data["reason"],
                actor_id=request.user.pk,
                request=request,
            ),
        )
        if release:
            success(
                request,
                f"Se prepararon {len(selected_ids)} constancias individuales.",
            )
            return redirect(
                "inventory:custody_document_detail",
                document_id=release.id,
            )

    if tab == "history":
        documents = documents.filter(status__in=historical)
    elif tab == "release_individual":
        documents = documents.filter(
            document_type=CustodyDocumentType.ASSIGNMENT,
            items__custody_assignment__status__in={
                CustodyStatus.ACTIVE,
                CustodyStatus.RETURN_PENDING,
            },
            asset_count=1,
        ).exclude(status__in=historical).distinct()
    elif tab == "release_bulk":
        documents = documents.filter(
            document_type=CustodyDocumentType.ASSIGNMENT,
            items__custody_assignment__status__in={
                CustodyStatus.ACTIVE,
                CustodyStatus.RETURN_PENDING,
            },
        ).filter(
            Q(batch_size__gt=1, batch_position=1)
            | Q(asset_count__gt=1)
        ).exclude(status__in=historical).distinct()
    else:
        documents = documents.exclude(status__in=historical)
        tab = "current"
    selecting_release = tab in {"release_individual", "release_bulk"}
    document_rows = (
        [] if selecting_release else _group_document_rows(list(documents))
    )
    return render_inventory(
        request,
        page="inventory/pages/custody_document_list.html",
        content="inventory/content/custody_document_list_content.html",
        context={
            "current_inventory_view": "inventory:custody_list",
            "documents": documents,
            "document_rows": document_rows,
            "tab": tab,
            "selecting_release": selecting_release,
            "release_custodies": release_custodies,
            "department_choices": _department_choices(),
            "selected_department_id": department_filter,
            "q": search_query,
            "bulk_release_form": bulk_release_form,
        },
        status=422 if request.method == "POST" else 200,
    )


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(
    AppIdentifier.INVENTORY,
    required_fine_permission="can_manage_custody",
)
def custody_release_individual_view(request, custody_id):
    custody = selector_or_404(
        lambda: CustodyAssignment.objects.select_related("asset").get(
            pk=custody_id,
            is_deleted=False,
            status__in={CustodyStatus.ACTIVE, CustodyStatus.RETURN_PENDING},
        )
    )
    form = CustodyDocumentReleaseForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        release = run_service(
            form,
            lambda: create_custody_releases_from_assignments(
                custody_ids=[custody.id],
                reason=form.cleaned_data["reason"],
                actor_id=request.user.pk,
                request=request,
            ),
        )
        if release:
            success(request, f"Constancia {release.folio} preparada para firma.")
            return redirect(
                "inventory:custody_document_detail",
                document_id=release.id,
            )
    return render_inventory(
        request,
        page="inventory/pages/custody_assignment_release.html",
        content="inventory/content/custody_assignment_release_content.html",
        context={
            "current_inventory_view": "inventory:custody_list",
            "custody": custody,
            "form": form,
        },
        status=422 if request.method == "POST" else 200,
    )


@axentra_gate_enforcer(
    AppIdentifier.INVENTORY,
    required_fine_permission="can_manage_custody",
)
def custody_document_detail_view(request, document_id):
    document = selector_or_404(
        lambda: CustodyDocument.objects.select_related(
            "prepared_by",
            "closed_by",
            "replacement_of",
        )
        .prefetch_related("items__custody_assignment")
        .get(pk=document_id, is_deleted=False)
    )
    generated_type = (
        "RETURN_RECEIPT"
        if document.document_type == CustodyDocumentType.RELEASE
        else "CUSTODY_RECEIPT"
    )
    acknowledgement = get_acknowledgement_state(
        owner_type="CUSTODY_DOCUMENT",
        owner_id=document.id,
        generated_type=generated_type,
    )
    permissions = set(
        getattr(request, "axentra_permissions_list", []) or []
    )
    return render_inventory(
        request,
        page="inventory/pages/custody_document_detail.html",
        content="inventory/content/custody_document_detail_content.html",
        context={
            "current_inventory_view": "inventory:custody_list",
            "document": document,
            "can_replace": not document.is_historical,
            "can_release": (
                document.document_type == CustodyDocumentType.ASSIGNMENT
                and not document.is_historical
                and document.items.filter(
                    custody_assignment__status__in={
                        CustodyStatus.ACTIVE,
                        CustodyStatus.RETURN_PENDING,
                    },
                ).exists()
            ),
            "is_individual_document": document.items.count() == 1,
            "batch_documents": CustodyDocument.objects.filter(
                batch_id=document.batch_id,
                is_deleted=False,
            ).order_by("batch_position", "prepared_at"),
            "generated_type": generated_type,
            "acknowledgement": acknowledgement,
            "can_validate_acknowledgement": (
                getattr(request, "axentra_is_root", False)
                or "can_validate_documents" in permissions
            ),
        },
    )


@axentra_gate_enforcer(
    AppIdentifier.INVENTORY,
    required_fine_permission="can_manage_custody",
)
def custody_document_print_view(request, document_id):
    document = selector_or_404(
        lambda: CustodyDocument.objects.select_related(
            "prepared_by",
            "closed_by",
            "replacement_of",
        ).prefetch_related(
            "items__custody_assignment",
        ).get(
            pk=document_id,
            is_deleted=False,
        )
    )
    batch_print = request.GET.get("batch") == "1" and document.batch_size > 1
    batch_documents = (
        CustodyDocument.objects.filter(
            batch_id=document.batch_id,
            document_type=document.document_type,
            is_deleted=False,
        )
        .select_related("prepared_by", "closed_by", "replacement_of")
        .prefetch_related("items__custody_assignment")
        .order_by("batch_position", "prepared_at")
        if batch_print else None
    )
    return render_inventory(
        request,
        page="inventory/pages/custody_document_print.html",
        content=(
            "inventory/content/custody_document_batch_print_content.html"
            if batch_print
            else "inventory/content/custody_document_print_content.html"
        ),
        context={
            "current_inventory_view": "inventory:custody_list",
            "document": document,
            "documents": batch_documents,
            "print_view": True,
            "embed_preview": request.GET.get("embed") == "1",
        },
    )


@require_http_methods(["POST"])
@axentra_gate_enforcer(
    AppIdentifier.INVENTORY,
    required_fine_permission="can_manage_custody",
)
def custody_document_close_view(request, document_id):
    document = selector_or_404(
        lambda: CustodyDocument.objects.get(
            pk=document_id,
            is_deleted=False,
        )
    )
    try:
        close_custody_document(
            document_id=document.id,
            reason=request.POST.get(
                "reason",
                "Todos los resguardos del documento fueron concluidos.",
            ),
            actor_id=request.user.pk,
        )
    except (InventoryServiceError, ValidationError) as exc:
        messages.error(request, str(exc))
    else:
        success(request, "Documento enviado al histórico inmutable.")
    return redirect(
        "inventory:custody_document_detail",
        document_id=document.id,
    )


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(
    AppIdentifier.INVENTORY,
    required_fine_permission="can_manage_custody",
)
def custody_document_replace_view(request, document_id):
    document = selector_or_404(
        lambda: CustodyDocument.objects.prefetch_related("items").get(
            pk=document_id,
            is_deleted=False,
        )
    )
    department_id = str(document.department_id)
    user_id = request.POST.get("assigned_to_id", "").strip()
    form = CustodyDocumentReplaceForm(request.POST or None)
    form.fields["assigned_to_id"].choices = []
    users = CoreDirectorySelectors.users(department_id=department_id)
    form.fields["assigned_to_id"].choices = [
        (
            str(item.id),
            f"{item.display_name} · {item.email}"
            if item.email else item.display_name,
        )
        for item in users
    ]
    if request.method == "POST" and form.is_valid():
        replacement = run_service(
            form,
            lambda: replace_custody_document(
                document_id=document.id,
                assignee_mode=form.cleaned_data["assignee_mode"],
                assigned_to_id=form.cleaned_data.get("assigned_to_id"),
                reason=form.cleaned_data["reason"],
                actor_id=request.user.pk,
                request=request,
            ),
        )
        if replacement:
            success(
                request,
                f"El documento fue sustituido por {replacement.folio}.",
            )
            return redirect(
                "inventory:custody_document_detail",
                document_id=replacement.id,
            )
    return render_inventory(
        request,
        page="inventory/pages/custody_document_replace.html",
        content="inventory/content/custody_document_replace_content.html",
        context={
            "current_inventory_view": "inventory:custody_list",
            "document": document,
            "form": form,
        },
        status=422 if request.method == "POST" else 200,
    )


@require_http_methods(["GET", "POST"])
@axentra_gate_enforcer(
    AppIdentifier.INVENTORY,
    required_fine_permission="can_manage_custody",
)
def custody_document_release_view(request, document_id):
    document = selector_or_404(
        lambda: CustodyDocument.objects.prefetch_related(
            "items__custody_assignment"
        ).get(pk=document_id, is_deleted=False)
    )
    form = CustodyDocumentReleaseForm(request.POST or None)
    bulk_release = request.GET.get("bulk") == "1"
    if request.method == "POST" and form.is_valid():
        release = run_service(
            form,
            lambda: (
                create_custody_release_batch(
                    source_document_id=document.id,
                    reason=form.cleaned_data["reason"],
                    actor_id=request.user.pk,
                    request=request,
                )
                if bulk_release
                else create_custody_release_document(
                    document_id=document.id,
                    reason=form.cleaned_data["reason"],
                    actor_id=request.user.pk,
                    request=request,
                )
            ),
        )
        if release:
            success(
                request,
                f"Constancia {release.folio} preparada para firma.",
            )
            return redirect(
                "inventory:custody_document_detail",
                document_id=release.id,
            )
    return render_inventory(
        request,
        page="inventory/pages/custody_document_release.html",
        content="inventory/content/custody_document_release_content.html",
        context={
            "current_inventory_view": "inventory:custody_list",
            "document": document,
            "form": form,
            "active_items": [
                item for item in document.items.all()
                if item.custody_assignment.status in {
                    CustodyStatus.ACTIVE,
                    CustodyStatus.RETURN_PENDING,
                }
            ],
            "bulk_release": bulk_release,
            "batch_size": (
                max(document.batch_size, document.items.count())
                if bulk_release else 1
            ),
        },
        status=422 if request.method == "POST" else 200,
    )


__all__ = [name for name in globals() if name.endswith("_view")]
