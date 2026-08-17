# apps/security/views/organigrama_views.py
import logging
import uuid
import json
from django.db.models import Q, Count
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.db import transaction

from apps.security.models.accounts import UserProfile
from apps.security.permissions import OrganigramaPermissions
from apps.shared.apps_config import AppIdentifier
from apps.security.decorators import axentra_module_gate
from apps.security.models.organigrama import Sede, Dependencia, AreaOperativa
from apps.security.models.audit import SecurityAuditLog
from apps.security.selectors.organigrama_selectors import SedeSelectors, DependenciaSelectors, AreaOperativaSelectors
from apps.security.services.organigrama_services import OrganigramaService
from apps.security.forms import SedeForm, DependenciaForm, AreaOperativaForm
from apps.security.utils.forensic_auditor import ForensicAuditor
from django.contrib import messages

User = get_user_model()
logger = logging.getLogger(__name__)


# =========================================================================
# 📊 PILAR 1: CUADROS DE MANDO Y REJILLAS PRINCIPALES (ANALYTICS & CONTROL)
# =========================================================================



@login_required
@axentra_module_gate(AppIdentifier.ORGANIGRAMA, required_fine_permission="can_view_analytics")
def organigrama_dashboard_view(request):
    """Cabina de mando analítica: Métrica con mapeo plano seguro para evitar fallos de Lookup."""
    
    # 1. KPIs Numéricos Tradicionales
    total_sedes = Sede.objects.filter(is_deleted=False).count()
    total_dependencias = Dependencia.objects.filter(is_deleted=False).count()
    total_areas = AreaOperativa.objects.filter(is_deleted=False).count()
    
    # Verificación segura de la existencia del perfil
    funcionarios_sin_area = 0
    if hasattr(User, 'axentra_profile'):
        funcionarios_sin_area = User.objects.filter(
            is_active=True, axentra_profile__area__isnull=True
        ).count()

    # 📊 METRICA 1 SEGURO: Conteo desde el Perfil de Usuario hacia la Dependencia
    grafica_dep_labels = []
    grafica_dep_valores = []
    
    try:
        # Buscamos en el modelo de perfil (asumiendo que se llama AxentraProfile de tu paquete account/staff)
        # Agrupamos directamente por el campo de la FK de la dependencia que está amarrada al Área
        perfiles_queryset = User.objects.filter(is_active=True, axentra_profile__area__isnull=False)\
            .values('axentra_profile__area__dependencia__nombre')\
            .annotate(total=Count('id'))\
            .order_by('-total')[:7]
            
        for item in perfiles_queryset:
            nombre_dep = item['axentra_profile__area__dependencia__nombre']
            if nombre_dep:
                grafica_dep_labels.append(nombre_dep)
                grafica_dep_valores.append(item['total'])
    except Exception:
        # Plan de respaldo: Si los nombres de campos varían, listamos las dependencias vacías para no tumbar la app
        dependencias = Dependencia.objects.filter(is_deleted=False)[:7]
        grafica_dep_labels = [d.nombre for d in dependencias]
        grafica_dep_valores = [0] * len(dependencias)

    # 📊 METRICA 2 SEGURO: Conteo de Áreas Operativas por Sede Física
    grafica_sede_labels = []
    grafica_sede_valores = []
    
    try:
        # Agrupamos las áreas usando los valores planos de la Sede para no arriesgar lookups inversos
        areas_queryset = AreaOperativa.objects.filter(is_deleted=False, sede_fisica__is_deleted=False)\
            .values('sede_fisica__nombre')\
            .annotate(total=Count('id'))\
            .order_by('-total')[:7]
            
        for item in areas_queryset:
            nombre_sede = item['sede_fisica__nombre']
            if nombre_sede:
                grafica_sede_labels.append(nombre_sede)
                grafica_sede_valores.append(item['total'])
    except Exception:
        sedes = Sede.objects.filter(is_deleted=False)[:7]
        grafica_sede_labels = [s.nombre for s in sedes]
        grafica_sede_valores = [0] * len(sedes)

    context = {
        'total_sedes': total_sedes,
        'total_dependencias': total_dependencias,
        'total_areas': total_areas,
        'funcionarios_sin_area': funcionarios_sin_area,
        
        # Inyección serializada limpia
        'grafica_dep_labels': json.dumps(grafica_dep_labels),
        'grafica_dep_valores': json.dumps(grafica_dep_valores),
        'grafica_sede_labels': json.dumps(grafica_sede_labels),
        'grafica_sede_valores': json.dumps(grafica_sede_valores),
    }
    
    return render(request, 'organigrama/dashboard/organigrama_dashboard.html', context)


@login_required
@axentra_module_gate(AppIdentifier.ORGANIGRAMA, required_fine_permission="has_access_module")
def estructura_list_view(request):
    """Hub principal de estructura orgánica gubernamental."""

    is_htmx = str(request.headers.get("HX-Request", "")).strip().lower() == "true"
    target_htmx = request.headers.get("HX-Target", "")

    dependencias = (
        Dependencia.objects
        .filter(is_deleted=False)
        .prefetch_related("areas__sede_fisica")
        .order_by("nombre")
    )

    sedes = (
        Sede.objects
        .filter(is_deleted=False)
        .prefetch_related("areas")
        .order_by("nombre")
    )

    areas = (
        AreaOperativa.objects
        .filter(is_deleted=False)
        .select_related("dependencia", "sede_fisica")
        .order_by("dependencia__nombre", "nombre")
    )

    context = {
        "dependencias": dependencias,
        "sedes": sedes,
        "areas": areas,
        "total_dependencias": dependencias.count(),
        "total_sedes": sedes.count(),
        "total_areas": areas.count(),
        "modulo_actual": AppIdentifier.ORGANIGRAMA,
        "show_module_sidebar": False,
    }

    if is_htmx and target_htmx == "workbench":
        return render(request, "organigrama/workbench/estructura_list_workbench.html", context)

    if is_htmx and target_htmx == "page-content":
        return render(request, "organigrama/content/estructura_list_content.html", context)

    return render(request, "organigrama/pages/estructura_list.html", context)


# =========================================================================
# 🏛️ PILAR 2: GESTIÓN GEOGRÁFICA (SEDES E INMUEBLES MUNICIPALES)
# =========================================================================
@login_required
@axentra_module_gate(AppIdentifier.ORGANIGRAMA, required_fine_permission="can_manage_infrastructure")
def sede_list_view(request):
    """Inventario geográfico físico de palacios y anexos municipales."""

    is_htmx = str(request.headers.get("HX-Request", "")).strip().lower() == "true"
    target_htmx = request.headers.get("HX-Target", "")

    sedes = SedeSelectors.listar_todas()

    context = {
        "sedes": sedes,
        "modulo_actual": AppIdentifier.ORGANIGRAMA,
        "show_module_sidebar": False,
    }

    if is_htmx and target_htmx == "workbench":
        return render(request, "organigrama/workbench/sede_list_workbench.html", context)

    if is_htmx and target_htmx == "page-content":
        return render(request, "organigrama/content/sede_list_content.html", context)

    if is_htmx and target_htmx == "sede-results":
        return render(request, "organigrama/htmx/sede_cards.html", context)

    return render(request, "organigrama/pages/sede_list.html", context)

@login_required
@axentra_module_gate(AppIdentifier.ORGANIGRAMA, required_fine_permission="can_manage_infrastructure")
def sede_create_view(request):
    """Aprovisionamiento de nuevos inmuebles institucionales."""
    is_htmx = str(request.headers.get("HX-Request", "")).strip().lower() == "true"
    target_htmx = request.headers.get("HX-Target", "")

    if request.method == "POST":
        form = SedeForm(request.POST)
        
        if form.is_valid():
            exito, sede, errores = OrganigramaService.crear_sede(request, form.cleaned_data)
            
            if exito:
                messages.success(request, f"Sede '{sede.nombre}' registrada correctamente.")
                context_list = {
                    "sedes": SedeSelectors.listar_todas(),
                    "modulo_actual": AppIdentifier.ORGANIGRAMA,
                    "show_module_sidebar": False,
                }
                if is_htmx:
                    response = render(request, "organigrama/htmx/sede_list_with_messages.html", context_list)
                    response["HX-Push-Url"] = reverse("organigrama:sede_list")
                    return response
                return redirect("organigrama:sede_list")

            error_msg = errores.get("server_error", ["Error de persistencia"])[0]
            messages.error(request, error_msg)
            form.add_error(None, error_msg)
        else:
            messages.error(request, "Revisa los campos del formulario antes de guardar la sede.")
    else:
        form = SedeForm()

    context = {
        "form": form,
        "action": "create",
        "sede": None,
        "modulo_actual": AppIdentifier.ORGANIGRAMA,
        "show_module_sidebar": False,
    }

    if is_htmx and target_htmx == "page-content":
        return render(request, "organigrama/content/sede_form_content.html", context)

    return render(request, "organigrama/pages/sede_form.html", context)

@login_required
@axentra_module_gate(AppIdentifier.ORGANIGRAMA, required_fine_permission="can_manage_infrastructure")
def sede_update_view(request, pk: uuid.UUID):
    """Modificación contextual de metadatos geográficos de una sede."""

    is_htmx = str(request.headers.get("HX-Request", "")).strip().lower() == "true"
    target_htmx = request.headers.get("HX-Target", "")

    sede_instancia = get_object_or_404(Sede, pk=pk, is_deleted=False)

    if request.method == "POST":
        form = SedeForm(request.POST, instance=sede_instancia)

        if form.is_valid():
            exito, errores = OrganigramaService.actualizar_sede(
                request,
                sede_instancia,
                form.cleaned_data,
            )

            if exito:
                messages.success(
                    request,
                    f"Sede '{sede_instancia.nombre}' actualizada correctamente.",
                )

                areas = (
                    AreaOperativa.objects
                    .filter(
                        sede_fisica=sede_instancia,
                        is_deleted=False,
                    )
                    .select_related("dependencia")
                    .order_by("dependencia__nombre", "nombre")
                )

                dependencias = (
                    Dependencia.objects
                    .filter(
                        areas__sede_fisica=sede_instancia,
                        areas__is_deleted=False,
                        is_deleted=False,
                    )
                    .distinct()
                    .order_by("nombre")
                )

                context_detail = {
                    "sede": sede_instancia,
                    "areas": areas,
                    "dependencias": dependencias,
                    "total_areas": areas.count(),
                    "total_dependencias": dependencias.count(),
                    "modulo_actual": AppIdentifier.ORGANIGRAMA,
                    "show_module_sidebar": True,
                }

                if is_htmx and target_htmx == "page-content":
                    return render(
                        request,
                        "organigrama/htmx/sede_identidad_with_messages.html",
                        context_detail,
                    )

                return redirect("organigrama:sede_detail", pk=sede_instancia.id)

            error_msg = errores.get("server_error", ["Fallo de actualización"])[0]
            messages.error(request, error_msg)
            form.add_error(None, error_msg)

        else:
            messages.error(
                request,
                "Revisa los campos del formulario antes de actualizar la sede.",
            )

    else:
        form = SedeForm(instance=sede_instancia)

    return render_sede_contextual_subview(
        request=request,
        sede=sede_instancia,
        partial_template="organigrama/content/sede_form_content.html",
        current_sub_view="organigrama:sede_sub_identidad",
        extra_context={
            "form": form,
            "action": "update",
            "sede": sede_instancia,
            "back_label": "Volver a Ficha de Sede",
            "back_target": "#page-content",
        },
    )


@require_POST
@login_required
@axentra_module_gate(AppIdentifier.ORGANIGRAMA, required_fine_permission="can_manage_infrastructure")
def sede_soft_delete_view(request, pk: uuid.UUID):
    """Baja lógica protegida de una sede física."""

    is_htmx = str(request.headers.get("HX-Request", "")).strip().lower() == "true"
    target_htmx = request.headers.get("HX-Target", "")

    sede_instancia = get_object_or_404(
        Sede,
        pk=pk,
        is_deleted=False,
    )

    nombre_sede = sede_instancia.nombre

    exito, errores = OrganigramaService.eliminar_sede(
        request,
        sede_instancia,
    )

    if exito:
        messages.warning(
            request,
            f"Sede '{nombre_sede}' enviada a baja lógica correctamente.",
        )

        sedes = SedeSelectors.listar_todas()

        context_list = {
            "sedes": sedes,
            "total_sedes": sedes.count(),
            "modulo_actual": AppIdentifier.ORGANIGRAMA,
            "show_module_sidebar": False,
        }

        if is_htmx:
            return render(
                request,
                "organigrama/htmx/sede_list_with_messages.html",
                context_list,
            )

        return redirect("organigrama:sede_list")

    error_msg = errores.get(
        "server_error",
        ["No fue posible dar de baja la sede."],
    )[0]

    messages.error(request, error_msg)

    areas = (
        AreaOperativa.objects
        .filter(
            sede_fisica=sede_instancia,
            is_deleted=False,
        )
        .select_related("dependencia")
        .order_by("dependencia__nombre", "nombre")
    )

    dependencias = (
        Dependencia.objects
        .filter(
            areas__sede_fisica=sede_instancia,
            areas__is_deleted=False,
            is_deleted=False,
        )
        .distinct()
        .order_by("nombre")
    )

    raw_menu = OrganigramaPermissions.SEDE_DETAIL_MENU
    detail_menu = []

    current_sub_view = "organigrama:sede_sub_identidad"

    for item in raw_menu:
        url_name = item.get("url_name")

        if not url_name:
            continue

        required_perm = item.get("permission")

        tiene_permiso = (
            getattr(request, "axentra_is_root", False)
            or required_perm in getattr(request, "axentra_permissions_list", [])
            or f"{AppIdentifier.ORGANIGRAMA}__{required_perm}" in getattr(request, "axentra_permissions_list", [])
        )

        if not tiene_permiso:
            continue

        href = "#"

        if url_name != "#":
            href = reverse(url_name, args=[sede_instancia.id])

        detail_menu.append({
            "icon": item.get("icon", "circle"),
            "title": item.get("title", "Sin título"),
            "href": href,
            "order": item.get("order", 99),
            "provider": item.get("provider", "organigrama"),
            "active": url_name == current_sub_view,
        })

    detail_menu.sort(key=lambda item: item["order"])

    context_detail = {
        "sede": sede_instancia,
        "areas": areas,
        "dependencias": dependencias,
        "total_areas": areas.count(),
        "total_dependencias": dependencias.count(),
        "detail_menu": detail_menu,
        "modulo_actual": AppIdentifier.ORGANIGRAMA,
        "show_module_sidebar": True,
    }

    if is_htmx and target_htmx == "workbench":
        return render(
            request,
            "organigrama/workbench/sede_detail_workbench_with_messages.html",
            context_detail,
        )

    if is_htmx and target_htmx == "page-content":
        return render(
            request,
            "organigrama/htmx/sede_identidad_with_messages.html",
            context_detail,
        )

    return redirect("organigrama:sede_detail", pk=sede_instancia.id)


@require_POST
@login_required
@axentra_module_gate(AppIdentifier.ORGANIGRAMA, required_fine_permission="can_manage_infrastructure")
def sede_toggle_status_view(request, pk: uuid.UUID):
    """
    Alternador protegido de estado operativo para sedes.

    Regla Axentra:
    Inactivar una sede no apaga áreas operativas.
    No se modifican dependencias automáticamente.
    """

    is_htmx = str(request.headers.get("HX-Request", "")).strip().lower() == "true"
    target_htmx = request.headers.get("HX-Target", "")

    sede_instancia = get_object_or_404(
        Sede,
        pk=pk,
        is_deleted=False,
    )

    estado_anterior = sede_instancia.is_active

    areas = (
        AreaOperativa.objects
        .filter(
            sede_fisica=sede_instancia,
            is_deleted=False,
        )
        .select_related("dependencia")
        .order_by("dependencia__nombre", "nombre")
    )

    dependencias = (
        Dependencia.objects
        .filter(
            areas__sede_fisica=sede_instancia,
            areas__is_deleted=False,
            is_deleted=False,
        )
        .distinct()
        .order_by("nombre")
    )

    total_areas = areas.count()
    total_dependencias = dependencias.count()

    with transaction.atomic():
        sede_instancia.is_active = not sede_instancia.is_active
        sede_instancia.save(
            update_fields=[
                "is_active",
                "updated_at",
            ]
        )

        ForensicAuditor.registrar_evento(
            request=request,
            action_type=SecurityAuditLog.ActionTypes.UPDATE,
            module_component="SEDES_INFRAESTRUCTURA",
            action_name="TOGGLE_STATUS_SEDE_PROTEGIDO",
            target_scope=(
                f"Actualización protegida del estado operativo para la sede "
                f"{sede_instancia.nombre}. "
                f"Activo anterior: {estado_anterior}. "
                f"Activo final: {sede_instancia.is_active}. "
                "No se modificaron áreas ni dependencias vinculadas."
            ),
            level=SecurityAuditLog.Levels.INFO,
            search_target=str(sede_instancia.id),
            payload={
                "sede_id": str(sede_instancia.id),
                "sede_nombre": sede_instancia.nombre,
                "estado_anterior": estado_anterior,
                "estado_nuevo": sede_instancia.is_active,
                "areas_activas": total_areas,
                "dependencias_vinculadas": total_dependencias,
                "cascade_applied": False,
            },
        )

    if sede_instancia.is_active:
        messages.success(
            request,
            f"Sede '{sede_instancia.nombre}' activada correctamente.",
        )
    else:
        if total_areas > 0:
            messages.warning(
                request,
                (
                    f"Sede '{sede_instancia.nombre}' inactivada. "
                    f"Tiene {total_areas} área(s) operativa(s) vinculada(s) "
                    f"y {total_dependencias} dependencia(s) presente(s). "
                    "Las áreas no fueron apagadas automáticamente."
                ),
            )
        else:
            messages.warning(
                request,
                f"Sede '{sede_instancia.nombre}' inactivada correctamente.",
            )

    context = {
        "sede": sede_instancia,
        "areas": areas,
        "dependencias": dependencias,
        "total_areas": total_areas,
        "total_dependencias": total_dependencias,
        "modulo_actual": AppIdentifier.ORGANIGRAMA,
    }

    if is_htmx and target_htmx == "page-content":
        return render(
            request,
            "organigrama/htmx/sede_identidad_with_messages.html",
            context,
        )

    if is_htmx:
        return render(
            request,
            "common/tags/badge_toggle_with_messages.html",
            {
                "is_active": sede_instancia.is_active,
                "toggle_url": reverse(
                    "organigrama:sede_toggle_status",
                    args=[sede_instancia.id],
                ),
            },
        )

    return redirect("organigrama:sede_detail", pk=sede_instancia.id)


@login_required
@axentra_module_gate(AppIdentifier.ORGANIGRAMA, required_fine_permission="can_manage_infrastructure")
def sede_detail_view(request, pk: uuid.UUID):
    """Expediente contextual de una sede física."""
    is_htmx = str(request.headers.get("HX-Request", "")).strip().lower() == "true"
    target_htmx = request.headers.get("HX-Target", "")

    sede = get_object_or_404(Sede, pk=pk, is_deleted=False)

    areas = (
        AreaOperativa.objects.filter(sede_fisica=sede, is_deleted=False)
        .select_related("dependencia")
        .order_by("dependencia__nombre", "nombre")
    )

    dependencias = (
        Dependencia.objects.filter(areas__sede_fisica=sede, areas__is_deleted=False, is_deleted=False)
        .distinct()
        .order_by("nombre")
    )

    raw_menu = OrganigramaPermissions.SEDE_DETAIL_MENU
    detail_menu = []
    current_sub_view = request.GET.get("sub_view", "organigrama:sede_sub_identidad")

    for item in raw_menu:
        url_name = item.get("url_name")
        if not url_name:
            continue

        required_perm = item.get("permission")
        tiene_permiso = (
            request.axentra_is_root
            or required_perm in getattr(request, "axentra_permissions_list", [])
            or f"{AppIdentifier.ORGANIGRAMA}__{required_perm}" in getattr(request, "axentra_permissions_list", [])
        )
        if not tiene_permiso:
            continue

        href = "#" if url_name == "#" else reverse(url_name, args=[sede.id])

        detail_menu.append({
            "icon": item.get("icon", "circle"),
            "title": item.get("title", "Sin título"),
            "href": href,
            "order": item.get("order", 99),
            "provider": item.get("provider", "organigrama"),
            "active": url_name == current_sub_view,
        })

    detail_menu.sort(key=lambda item: item["order"])

    context = {
        "sede": sede,
        "areas": areas,
        "dependencias": dependencias,
        "total_areas": areas.count(),
        "total_dependencias": dependencias.count(),
        "detail_menu": detail_menu,
        "modulo_actual": AppIdentifier.ORGANIGRAMA,
        "show_module_sidebar": True,
    }

    if is_htmx and target_htmx == "workbench":
        return render(request, "organigrama/workbench/sede_detail_workbench.html", context)

    return render(request, "organigrama/pages/sede_detail.html", context)


@login_required
@axentra_module_gate(AppIdentifier.ORGANIGRAMA, required_fine_permission="can_manage_infrastructure")
def sede_sub_identidad_view(request, pk: uuid.UUID):
    """Subvista de identidad del expediente contextual de sede."""

    sede = get_object_or_404(
        Sede,
        pk=pk,
        is_deleted=False,
    )

    return render_sede_contextual_subview(
        request=request,
        sede=sede,
        partial_template="organigrama/contextual/partials/sede_identidad.html",
        current_sub_view="organigrama:sede_sub_identidad",
    )

def render_sede_contextual_subview(
    request,
    sede: Sede,
    partial_template: str,
    current_sub_view: str,
    extra_context: dict | None = None,
):
    """
    Render inteligente para subvistas del expediente contextual de sede.

    HTMX:
        devuelve sólo el partial para reemplazar #page-content.

    Normal/F5:
        devuelve página completa con shell + sidebar secundario + partial.
    """

    is_htmx = str(request.headers.get("HX-Request", "")).strip().lower() == "true"

    areas_base = (
        AreaOperativa.objects
        .filter(
            sede_fisica=sede,
            is_deleted=False,
        )
        .select_related("dependencia")
        .order_by("dependencia__nombre", "nombre")
    )

    dependencias_base = (
        Dependencia.objects
        .filter(
            areas__sede_fisica=sede,
            areas__is_deleted=False,
            is_deleted=False,
        )
        .distinct()
        .order_by("nombre")
    )

    raw_menu = OrganigramaPermissions.SEDE_DETAIL_MENU
    detail_menu = []

    for item in raw_menu:
        url_name = item.get("url_name")

        if not url_name:
            continue

        required_perm = item.get("permission")

        tiene_permiso = (
            getattr(request, "axentra_is_root", False)
            or required_perm in getattr(request, "axentra_permissions_list", [])
            or f"{AppIdentifier.ORGANIGRAMA}__{required_perm}" in getattr(request, "axentra_permissions_list", [])
        )

        if not tiene_permiso:
            continue

        href = "#"

        if url_name != "#":
            href = reverse(url_name, args=[sede.id])

        detail_menu.append({
            "icon": item.get("icon", "circle"),
            "title": item.get("title", "Sin título"),
            "href": href,
            "order": item.get("order", 99),
            "provider": item.get("provider", "organigrama"),
            "active": url_name == current_sub_view,
        })

    detail_menu.sort(key=lambda item: item["order"])

    context = {
        "sede": sede,
        "areas": areas_base,
        "dependencias": dependencias_base,
        "total_areas": areas_base.count(),
        "total_dependencias": dependencias_base.count(),
        "detail_menu": detail_menu,
        "partial_template": partial_template,
        "current_sub_view": current_sub_view,
        "modulo_actual": AppIdentifier.ORGANIGRAMA,
        "show_module_sidebar": True,
    }

    if extra_context:
        context.update(extra_context)

    if is_htmx:
        return render(
            request,
            partial_template,
            context,
        )

    return render(
        request,
        "organigrama/pages/sede_subpage.html",
        context,
    )

@login_required
@axentra_module_gate(AppIdentifier.ORGANIGRAMA, required_fine_permission="can_manage_infrastructure")
def sede_sub_dependencias_view(request, pk: uuid.UUID):
    """Subvista de dependencias presentes en una sede."""

    sede = get_object_or_404(
        Sede,
        pk=pk,
        is_deleted=False,
    )

    dependencias = (
        Dependencia.objects
        .filter(
            areas__sede_fisica=sede,
            areas__is_deleted=False,
            is_deleted=False,
        )
        .annotate(
            total_areas=Count(
                "areas",
                filter=Q(
                    areas__sede_fisica=sede,
                    areas__is_deleted=False,
                ),
                distinct=True,
            ),
        )
        .distinct()
        .order_by("nombre")
    )

    return render_sede_contextual_subview(
        request=request,
        sede=sede,
        partial_template="organigrama/contextual/partials/sede_dependencias.html",
        current_sub_view="organigrama:sede_sub_dependencias",
        extra_context={
            "dependencias": dependencias,
            "total_dependencias": dependencias.count(),
        },
    )

@login_required
@axentra_module_gate(AppIdentifier.ORGANIGRAMA, required_fine_permission="can_manage_infrastructure")
def sede_sub_areas_view(request, pk: uuid.UUID):
    """Subvista de áreas operativas presentes en una sede."""

    sede = get_object_or_404(
        Sede,
        pk=pk,
        is_deleted=False,
    )

    areas = (
        AreaOperativa.objects
        .filter(
            sede_fisica=sede,
            is_deleted=False,
        )
        .select_related("dependencia")
        .order_by("dependencia__nombre", "nombre")
    )

    return render_sede_contextual_subview(
        request=request,
        sede=sede,
        partial_template="organigrama/contextual/partials/sede_areas.html",
        current_sub_view="organigrama:sede_sub_areas",
        extra_context={
            "areas": areas,
            "total_areas": areas.count(),
        },
    )

   
@login_required
@axentra_module_gate(AppIdentifier.ORGANIGRAMA, required_fine_permission="can_manage_infrastructure")
def sede_sub_funcionarios_view(request, pk: uuid.UUID):
    """Subvista de funcionarios adscritos a una sede."""

    sede = get_object_or_404(
        Sede,
        pk=pk,
        is_deleted=False,
    )

    funcionarios = (
        UserProfile.objects
        .filter(
            area__sede_fisica=sede,
            user__is_deleted=False,
        )
        .select_related(
            "user",
            "area",
            "area__dependencia",
        )
        .order_by(
            "user__first_name",
            "user__last_name",
        )
    )

    return render_sede_contextual_subview(
        request=request,
        sede=sede,
        partial_template="organigrama/contextual/partials/sede_funcionarios.html",
        current_sub_view="organigrama:sede_sub_funcionarios",
        extra_context={
            "funcionarios": funcionarios,
            "total_funcionarios": funcionarios.count(),
        },
    )
    

# =========================================================================
# 🏛️ PILAR 3: RAMOS ESTRUCTURALES (DEPENDENCIAS / DIRECCIONES GENERALES)
# =========================================================================
@login_required
@axentra_module_gate(AppIdentifier.ORGANIGRAMA, required_fine_permission="has_access_module")
def dependencia_list_view(request):
    """Inventario administrativo de dependencias institucionales."""

    is_htmx = str(request.headers.get("HX-Request", "")).strip().lower() == "true"
    target_htmx = request.headers.get("HX-Target", "")

    dependencias = (
        Dependencia.objects
        .filter(is_deleted=False)
        .annotate(
            total_areas=Count(
                "areas",
                filter=Q(areas__is_deleted=False),
                distinct=True,
            ),
            total_sedes=Count(
                "areas__sede_fisica",
                filter=Q(
                    areas__is_deleted=False,
                    areas__sede_fisica__is_deleted=False,
                ),
                distinct=True,
            ),
        )
        .order_by("nombre")
    )

    context = {
        "dependencias": dependencias,
        "total_dependencias": dependencias.count(),
        "dependencias_activas": dependencias.filter(is_active=True).count(),
        "dependencias_inactivas": dependencias.filter(is_active=False).count(),
        "modulo_actual": AppIdentifier.ORGANIGRAMA,
        "show_module_sidebar": False,
    }

    if is_htmx and target_htmx == "workbench":
        return render(
            request,
            "organigrama/workbench/dependencia_list_workbench.html",
            context,
        )

    if is_htmx and target_htmx == "page-content":
        return render(
            request,
            "organigrama/content/dependencia_list_content.html",
            context,
        )

    return render(
        request,
        "organigrama/pages/dependencia_list.html",
        context,
    )
    
    
@login_required
@axentra_module_gate(AppIdentifier.ORGANIGRAMA, required_fine_permission="can_mutate_structure")
def dependencia_create_view(request):
    """Alta de dependencias administrativas institucionales."""
    is_htmx = str(request.headers.get("HX-Request", "")).strip().lower() == "true"
    target_htmx = request.headers.get("HX-Target", "")

    if request.method == "POST":
        form = DependenciaForm(request.POST)

        if form.is_valid():
            payload = {
                "nombre": form.cleaned_data["nombre"],
                "codigo_presupuestal": form.cleaned_data["codigo_presupuestal"],
                "parent_id": form.cleaned_data["parent"].id if form.cleaned_data.get("parent") else None,
                "encargado_departamento_id": form.cleaned_data["encargado_departamento"].id if form.cleaned_data.get("encargado_departamento") else None,
            }

            exito, dependencia, errores = OrganigramaService.crear_dependencia(request, payload)

            if exito:
                messages.success(request, f"Dependencia '{dependencia.nombre}' registrada correctamente.")
                
                dependencias = (
                    Dependencia.objects.filter(is_deleted=False).select_related("parent")
                    .annotate(
                        total_areas=Count("areas", filter=Q(areas__is_deleted=False), distinct=True),
                        total_sedes=Count("areas__sede_fisica", filter=Q(areas__is_deleted=False, areas__sede_fisica__is_deleted=False), distinct=True),
                        total_hijas=Count("children", filter=Q(children__is_deleted=False), distinct=True),
                    ).order_by("parent__nombre", "nombre")
                )

                context_list = {
                    "dependencias": dependencias,
                    "total_dependencias": dependencias.count(),
                    "dependencias_activas": dependencias.filter(is_active=True).count(),
                    "dependencias_inactivas": dependencias.filter(is_active=False).count(),
                    "modulo_actual": AppIdentifier.ORGANIGRAMA,
                    "show_module_sidebar": False,
                }

                if is_htmx:
                    response = render(request, "organigrama/htmx/dependencia_list_with_messages.html", context_list)
                    response["HX-Push-Url"] = reverse("organigrama:dependencia_list")
                    return response
                return redirect("organigrama:dependencia_list")

            error_msg = errores.get("server_error", ["Fallo del Servidor"])[0]
            messages.error(request, error_msg)
            form.add_error(None, error_msg)
        else:
            messages.error(request, "Revisa los campos del formulario antes de guardar la dependencia.")
    else:
        form = DependenciaForm()

    context = {
        "form": form,
        "action": "create",
        "dependencia": None,
        "modulo_actual": AppIdentifier.ORGANIGRAMA,
        "show_module_sidebar": False,
    }

    if is_htmx and target_htmx == "page-content":
        template = "organigrama/htmx/dependencia_form_with_messages.html" if request.method == "POST" else "organigrama/content/dependencia_form_content.html"
        return render(request, template, context)

    return render(request, "organigrama/pages/dependencia_form.html", context)


@login_required
@axentra_module_gate(AppIdentifier.ORGANIGRAMA, required_fine_permission="can_mutate_structure")
def dependencia_update_view(request, pk: uuid.UUID):
    """Modificación contextual de nomenclatura, jerarquía y titular de dependencia."""
    is_htmx = str(request.headers.get("HX-Request", "")).strip().lower() == "true"
    target_htmx = request.headers.get("HX-Target", "")

    dep_instancia = get_object_or_404(Dependencia.objects.select_related("parent"), pk=pk, is_deleted=False)

    if request.method == "POST":
        form = DependenciaForm(request.POST, instance=dep_instancia)

        if form.is_valid():
            payload = {
                "nombre": form.cleaned_data["nombre"],
                "codigo_presupuestal": form.cleaned_data["codigo_presupuestal"],
                "parent_id": form.cleaned_data["parent"].id if form.cleaned_data.get("parent") else None,
                "encargado_departamento_id": form.cleaned_data["encargado_departamento"].id if form.cleaned_data.get("encargado_departamento") else None,
            }

            exito, errores = OrganigramaService.actualizar_dependencia(request, dep_instancia, payload)

            if exito:
                dep_instancia.refresh_from_db()
                messages.success(request, f"Dependencia '{dep_instancia.nombre}' actualizada correctamente.")

                areas = AreaOperativa.objects.filter(dependencia=dep_instancia, is_deleted=False).select_related("dependencia", "sede_fisica").order_by("sede_fisica__nombre", "nombre")
                sedes = Sede.objects.filter(areas__dependencia=dep_instancia, areas__is_deleted=False, is_deleted=False).distinct().order_by("nombre")
                funcionarios = UserProfile.objects.filter(area__dependencia=dep_instancia, area__is_deleted=False, user__is_deleted=False).select_related("user", "area", "area__dependencia", "area__sede_fisica").order_by("user__first_name", "user__last_name")
                dependencias_hijas = Dependencia.objects.filter(parent=dep_instancia, is_deleted=False).annotate(total_areas=Count("areas", filter=Q(areas__is_deleted=False), distinct=True)).order_by("nombre")

                context_detail = {
                    "dependencia": dep_instancia,
                    "dependencia_padre": dep_instancia.parent,
                    "dependencias_hijas": dependencias_hijas,
                    "total_dependencias_hijas": dependencias_hijas.count(),
                    "areas": areas,
                    "sedes": sedes,
                    "funcionarios": funcionarios,
                    "total_areas": areas.count(),
                    "total_sedes": sedes.count(),
                    "total_funcionarios": funcionarios.count(),
                    "modulo_actual": AppIdentifier.ORGANIGRAMA,
                    "show_module_sidebar": True,
                }

                if is_htmx:
                    response = render(request, "organigrama/htmx/dependencia_identidad_with_messages.html", context_detail)
                    response["HX-Push-Url"] = reverse("organigrama:dependencia_sub_identidad", args=[dep_instancia.id])
                    return response
                return redirect("organigrama:dependencia_detail", pk=dep_instancia.id)

            error_msg = errores.get("server_error", ["Fallo de actualización"])[0]
            messages.error(request, error_msg)
            form.add_error(None, error_msg)
        else:
            messages.error(request, "Revisa los campos del formulario antes de actualizar la dependencia.")
    else:
        form = DependenciaForm(instance=dep_instancia)

    return render_dependencia_contextual_subview(
        request=request,
        dependencia=dep_instancia,
        partial_template="organigrama/content/dependencia_form_content.html",
        current_sub_view="organigrama:dependencia_sub_identidad",
        extra_context={
            "form": form,
            "action": "update",
            "dependencia": dep_instancia,
            "back_label": "Volver a Ficha de Dependencia",
            "back_target": "#page-content",
        },
    )


@require_POST
@login_required
@axentra_module_gate(AppIdentifier.ORGANIGRAMA, required_fine_permission="can_mutate_structure")
def dependencia_soft_delete_view(request, pk: uuid.UUID):
    """Baja lógica protegida de una dependencia administrativa."""

    is_htmx = str(request.headers.get("HX-Request", "")).strip().lower() == "true"
    target_htmx = request.headers.get("HX-Target", "")

    dep_instancia = get_object_or_404(
        Dependencia,
        pk=pk,
        is_deleted=False,
    )

    nombre_dependencia = dep_instancia.nombre

    exito, errores = OrganigramaService.eliminar_dependencia(
        request,
        dep_instancia,
    )

    if exito:
        messages.warning(
            request,
            f"Dependencia '{nombre_dependencia}' enviada a baja lógica correctamente.",
        )

        dependencias = (
            Dependencia.objects
            .filter(is_deleted=False)
            .annotate(
                total_areas=Count(
                    "areas",
                    filter=Q(areas__is_deleted=False),
                    distinct=True,
                ),
                total_sedes=Count(
                    "areas__sede_fisica",
                    filter=Q(
                        areas__is_deleted=False,
                        areas__sede_fisica__is_deleted=False,
                    ),
                    distinct=True,
                ),
            )
            .order_by("nombre")
        )

        context_list = {
            "dependencias": dependencias,
            "total_dependencias": dependencias.count(),
            "dependencias_activas": dependencias.filter(is_active=True).count(),
            "dependencias_inactivas": dependencias.filter(is_active=False).count(),
            "modulo_actual": AppIdentifier.ORGANIGRAMA,
            "show_module_sidebar": False,
        }

        if is_htmx:
            response = render(
                request,
                "organigrama/htmx/dependencia_list_with_messages.html",
                context_list,
            )
            response["HX-Push-Url"] = reverse("organigrama:dependencia_list")
            return response

        return redirect("organigrama:dependencia_list")

    error_msg = errores.get(
        "server_error",
        ["No fue posible dar de baja la dependencia."],
    )[0]

    messages.error(request, error_msg)

    areas = (
        AreaOperativa.objects
        .filter(
            dependencia=dep_instancia,
            is_deleted=False,
        )
        .select_related(
            "dependencia",
            "sede_fisica",
        )
        .order_by(
            "sede_fisica__nombre",
            "nombre",
        )
    )

    sedes = (
        Sede.objects
        .filter(
            areas__dependencia=dep_instancia,
            areas__is_deleted=False,
            is_deleted=False,
        )
        .distinct()
        .order_by("nombre")
    )

    funcionarios = (
        UserProfile.objects
        .filter(
            area__dependencia=dep_instancia,
            area__is_deleted=False,
            user__is_deleted=False,
        )
        .select_related(
            "user",
            "area",
            "area__dependencia",
            "area__sede_fisica",
        )
        .order_by(
            "user__first_name",
            "user__last_name",
        )
    )

    raw_menu = OrganigramaPermissions.DEPENDENCIA_DETAIL_MENU
    detail_menu = []
    current_sub_view = "organigrama:dependencia_sub_identidad"

    for item in raw_menu:
        url_name = item.get("url_name")

        if not url_name:
            continue

        required_perm = item.get("permission")

        tiene_permiso = (
            getattr(request, "axentra_is_root", False)
            or required_perm in getattr(request, "axentra_permissions_list", [])
            or f"{AppIdentifier.ORGANIGRAMA}__{required_perm}" in getattr(request, "axentra_permissions_list", [])
        )

        if not tiene_permiso:
            continue

        href = "#"

        if url_name != "#":
            href = reverse(url_name, args=[dep_instancia.id])

        detail_menu.append({
            "icon": item.get("icon", "circle"),
            "title": item.get("title", "Sin título"),
            "href": href,
            "order": item.get("order", 99),
            "provider": item.get("provider", "organigrama"),
            "active": url_name == current_sub_view,
        })

    detail_menu.sort(key=lambda item: item["order"])

    context_detail = {
        "dependencia": dep_instancia,
        "areas": areas,
        "sedes": sedes,
        "funcionarios": funcionarios,
        "total_areas": areas.count(),
        "total_sedes": sedes.count(),
        "total_funcionarios": funcionarios.count(),
        "detail_menu": detail_menu,
        "modulo_actual": AppIdentifier.ORGANIGRAMA,
        "show_module_sidebar": True,
    }

    if is_htmx and target_htmx == "workbench":
        return render(
            request,
            "organigrama/workbench/dependencia_detail_workbench_with_messages.html",
            context_detail,
        )

    if is_htmx and target_htmx == "page-content":
        return render(
            request,
            "organigrama/htmx/dependencia_identidad_with_messages.html",
            context_detail,
        )

    return redirect(
        "organigrama:dependencia_detail",
        pk=dep_instancia.id,
    )
    

@require_POST
@login_required
@axentra_module_gate(AppIdentifier.ORGANIGRAMA, required_fine_permission="can_mutate_structure")
def dependencia_toggle_status_view(request, pk: uuid.UUID):
    """
    Alternador protegido de estado operativo para dependencias.

    Regla Axentra:
    Inactivar una dependencia no apaga sus áreas operativas.
    La operación vinculada debe revisarse explícitamente desde Áreas Operativas.
    """

    is_htmx = str(request.headers.get("HX-Request", "")).strip().lower() == "true"
    target_htmx = request.headers.get("HX-Target", "")

    dep_instancia = get_object_or_404(
        Dependencia,
        pk=pk,
        is_deleted=False,
    )

    estado_anterior = dep_instancia.is_active

    areas = (
        AreaOperativa.objects
        .filter(
            dependencia=dep_instancia,
            is_deleted=False,
        )
        .select_related("sede_fisica")
        .order_by("sede_fisica__nombre", "nombre")
    )

    sedes = (
        Sede.objects
        .filter(
            areas__dependencia=dep_instancia,
            areas__is_deleted=False,
            is_deleted=False,
        )
        .distinct()
        .order_by("nombre")
    )

    total_areas = areas.count()
    total_sedes = sedes.count()

    with transaction.atomic():
        dep_instancia.is_active = not dep_instancia.is_active
        dep_instancia.save(
            update_fields=[
                "is_active",
                "updated_at",
            ]
        )

        ForensicAuditor.registrar_evento(
            request=request,
            action_type=SecurityAuditLog.ActionTypes.UPDATE,
            module_component="DEPENDENCIAS_RAIZ",
            action_name="TOGGLE_STATUS_DEPENDENCIA_PROTEGIDO",
            target_scope=(
                f"Actualización protegida del estado operativo para la dependencia "
                f"{dep_instancia.nombre}. "
                f"Activo anterior: {estado_anterior}. "
                f"Activo final: {dep_instancia.is_active}. "
                "No se modificaron áreas operativas vinculadas."
            ),
            level=SecurityAuditLog.Levels.INFO,
            search_target=str(dep_instancia.id),
            payload={
                "dependencia_id": str(dep_instancia.id),
                "dependencia_nombre": dep_instancia.nombre,
                "estado_anterior": estado_anterior,
                "estado_nuevo": dep_instancia.is_active,
                "areas_activas": total_areas,
                "sedes_vinculadas": total_sedes,
                "cascade_applied": False,
            },
        )

    if dep_instancia.is_active:
        messages.success(
            request,
            f"Dependencia '{dep_instancia.nombre}' activada correctamente.",
        )
    else:
        if total_areas > 0:
            messages.warning(
                request,
                (
                    f"Dependencia '{dep_instancia.nombre}' inactivada. "
                    f"Tiene {total_areas} área(s) operativa(s) vinculada(s) "
                    f"en {total_sedes} sede(s). "
                    "Las áreas no fueron apagadas automáticamente."
                ),
            )
        else:
            messages.warning(
                request,
                f"Dependencia '{dep_instancia.nombre}' inactivada correctamente.",
            )

    logger.info(
        f"🛰️ AUDITORÍA: Toggle protegido aplicado sobre Dependencia ID=[{dep_instancia.id}] "
        f"Estado=[{estado_anterior} -> {dep_instancia.is_active}] "
        f"Áreas=[{total_areas}] Sedes=[{total_sedes}]"
    )

    context_detail = {
        "dependencia": dep_instancia,
        "areas": areas,
        "sedes": sedes,
        "total_areas": total_areas,
        "total_sedes": total_sedes,
        "modulo_actual": AppIdentifier.ORGANIGRAMA,
        "show_module_sidebar": True,
    }

    if is_htmx and target_htmx == "page-content":
        return render(
            request,
            "organigrama/htmx/dependencia_identidad_with_messages.html",
            context_detail,
        )

    if is_htmx:
        return render(
            request,
            "organigrama/htmx/dependencia_identidad_with_messages.html",
            context_detail,
        )

    return redirect(
        "organigrama:dependencia_detail",
        pk=dep_instancia.id,
    )


def render_dependencia_contextual_subview(
    request,
    dependencia: Dependencia,
    partial_template: str,
    current_sub_view: str,
    extra_context: dict | None = None,
):
    """
    Render inteligente para subvistas del expediente contextual de dependencia.

    HTMX:
        devuelve sólo el partial para reemplazar #page-content.

    Normal/F5:
        devuelve página completa con shell + sidebar secundario + partial.
    """

    is_htmx = str(request.headers.get("HX-Request", "")).strip().lower() == "true"

    areas_base = (
        AreaOperativa.objects
        .filter(
            dependencia=dependencia,
            is_deleted=False,
        )
        .select_related("sede_fisica")
        .order_by("sede_fisica__nombre", "nombre")
    )

    sedes_base = (
        Sede.objects
        .filter(
            areas__dependencia=dependencia,
            areas__is_deleted=False,
            is_deleted=False,
        )
        .distinct()
        .order_by("nombre")
    )

    raw_menu = OrganigramaPermissions.DEPENDENCIA_DETAIL_MENU
    detail_menu = []

    for item in raw_menu:
        url_name = item.get("url_name")

        if not url_name:
            continue

        required_perm = item.get("permission")

        tiene_permiso = (
            getattr(request, "axentra_is_root", False)
            or required_perm in getattr(request, "axentra_permissions_list", [])
            or f"{AppIdentifier.ORGANIGRAMA}__{required_perm}" in getattr(request, "axentra_permissions_list", [])
        )

        if not tiene_permiso:
            continue

        href = "#"

        if url_name != "#":
            href = reverse(url_name, args=[dependencia.id])

        detail_menu.append({
            "icon": item.get("icon", "circle"),
            "title": item.get("title", "Sin título"),
            "href": href,
            "order": item.get("order", 99),
            "provider": item.get("provider", "organigrama"),
            "active": url_name == current_sub_view,
        })

    detail_menu.sort(key=lambda item: item["order"])

    context = {
        "dependencia": dependencia,
        "areas": areas_base,
        "sedes": sedes_base,
        "total_areas": areas_base.count(),
        "total_sedes": sedes_base.count(),
        "detail_menu": detail_menu,
        "partial_template": partial_template,
        "current_sub_view": current_sub_view,
        "modulo_actual": AppIdentifier.ORGANIGRAMA,
        "show_module_sidebar": True,
    }

    if extra_context:
        context.update(extra_context)

    if is_htmx:
        return render(
            request,
            partial_template,
            context,
        )

    return render(
        request,
        "organigrama/pages/dependencia_subpage.html",
        context,
    )
    
@login_required
@axentra_module_gate(AppIdentifier.ORGANIGRAMA, required_fine_permission="has_access_module")
def dependencia_detail_view(request, pk: uuid.UUID):
    """Expediente contextual de una dependencia administrativa."""

    is_htmx = str(request.headers.get("HX-Request", "")).strip().lower() == "true"
    target_htmx = request.headers.get("HX-Target", "")

    dependencia = get_object_or_404(
        Dependencia.objects.select_related(
            "parent",
            "encargado_departamento",
        ),
        pk=pk,
        is_deleted=False,
    )

    areas = (
        AreaOperativa.objects
        .filter(
            dependencia=dependencia,
            is_deleted=False,
        )
        .select_related("sede_fisica")
        .order_by("sede_fisica__nombre", "nombre")
    )

    sedes = (
        Sede.objects
        .filter(
            areas__dependencia=dependencia,
            areas__is_deleted=False,
            is_deleted=False,
        )
        .distinct()
        .order_by("nombre")
    )

    funcionarios = (
        UserProfile.objects
        .filter(
            area__dependencia=dependencia,
            area__is_deleted=False,
            user__is_deleted=False,
        )
        .select_related(
            "user",
            "area",
            "area__dependencia",
            "area__sede_fisica",
        )
        .order_by(
            "user__first_name",
            "user__last_name",
        )
    )

    raw_menu = OrganigramaPermissions.DEPENDENCIA_DETAIL_MENU
    detail_menu = []

    current_sub_view = request.GET.get(
        "sub_view",
        "organigrama:dependencia_sub_identidad",
    )

    for item in raw_menu:
        url_name = item.get("url_name")

        if not url_name:
            continue

        required_perm = item.get("permission")

        tiene_permiso = (
            getattr(request, "axentra_is_root", False)
            or required_perm in getattr(request, "axentra_permissions_list", [])
            or f"{AppIdentifier.ORGANIGRAMA}__{required_perm}" in getattr(request, "axentra_permissions_list", [])
        )

        if not tiene_permiso:
            continue

        href = "#"

        if url_name != "#":
            href = reverse(url_name, args=[dependencia.id])

        detail_menu.append({
            "icon": item.get("icon", "circle"),
            "title": item.get("title", "Sin título"),
            "href": href,
            "order": item.get("order", 99),
            "provider": item.get("provider", "organigrama"),
            "active": url_name == current_sub_view,
        })

    detail_menu.sort(key=lambda item: item["order"])

    context = {
        "dependencia": dependencia,
        "areas": areas,
        "sedes": sedes,
        "funcionarios": funcionarios,
        "total_areas": areas.count(),
        "total_sedes": sedes.count(),
        "total_funcionarios": funcionarios.count(),
        "detail_menu": detail_menu,
        "modulo_actual": AppIdentifier.ORGANIGRAMA,
        "show_module_sidebar": True,
    }

    if is_htmx and target_htmx == "workbench":
        return render(
            request,
            "organigrama/workbench/dependencia_detail_workbench.html",
            context,
        )

    return render(
        request,
        "organigrama/pages/dependencia_detail.html",
        context,
    )
    
    
@login_required
@axentra_module_gate(AppIdentifier.ORGANIGRAMA, required_fine_permission="has_access_module")
def dependencia_sub_identidad_view(request, pk: uuid.UUID):
    """Subvista de identidad del expediente contextual de dependencia."""

    dependencia = get_object_or_404(
        Dependencia,
        pk=pk,
        is_deleted=False,
    )

    return render_dependencia_contextual_subview(
        request=request,
        dependencia=dependencia,
        partial_template="organigrama/contextual/partials/dependencia_identidad.html",
        current_sub_view="organigrama:dependencia_sub_identidad",
    )
    
@login_required
@axentra_module_gate(AppIdentifier.ORGANIGRAMA, required_fine_permission="has_access_module")
def dependencia_sub_areas_view(request, pk: uuid.UUID):
    """Subvista de áreas operativas adscritas a una dependencia."""

    dependencia = get_object_or_404(
        Dependencia,
        pk=pk,
        is_deleted=False,
    )

    areas = (
        AreaOperativa.objects
        .filter(
            dependencia=dependencia,
            is_deleted=False,
        )
        .select_related(
            "sede_fisica",
            "dependencia",
        )
        .order_by(
            "sede_fisica__nombre",
            "nombre",
        )
    )

    return render_dependencia_contextual_subview(
        request=request,
        dependencia=dependencia,
        partial_template="organigrama/contextual/partials/dependencia_areas.html",
        current_sub_view="organigrama:dependencia_sub_areas",
        extra_context={
            "areas": areas,
            "total_areas": areas.count(),
        },
    )


@login_required
@axentra_module_gate(AppIdentifier.ORGANIGRAMA, required_fine_permission="has_access_module")
def dependencia_sub_sedes_view(request, pk: uuid.UUID):
    """Subvista de sedes donde opera una dependencia."""

    dependencia = get_object_or_404(
        Dependencia,
        pk=pk,
        is_deleted=False,
    )

    sedes = (
        Sede.objects
        .filter(
            areas__dependencia=dependencia,
            areas__is_deleted=False,
            is_deleted=False,
        )
        .annotate(
            total_areas=Count(
                "areas",
                filter=Q(
                    areas__dependencia=dependencia,
                    areas__is_deleted=False,
                ),
                distinct=True,
            ),
        )
        .distinct()
        .order_by("nombre")
    )

    return render_dependencia_contextual_subview(
        request=request,
        dependencia=dependencia,
        partial_template="organigrama/contextual/partials/dependencia_sedes.html",
        current_sub_view="organigrama:dependencia_sub_sedes",
        extra_context={
            "sedes": sedes,
            "total_sedes": sedes.count(),
        },
    )


@login_required
@axentra_module_gate(AppIdentifier.ORGANIGRAMA, required_fine_permission="has_access_module")
def dependencia_sub_funcionarios_view(request, pk: uuid.UUID):
    """Subvista de funcionarios adscritos a una dependencia."""

    dependencia = get_object_or_404(
        Dependencia,
        pk=pk,
        is_deleted=False,
    )

    funcionarios = (
        UserProfile.objects
        .filter(
            area__dependencia=dependencia,
            user__is_deleted=False,
        )
        .select_related(
            "user",
            "area",
            "area__dependencia",
            "area__sede_fisica",
        )
        .order_by(
            "user__first_name",
            "user__last_name",
        )
    )

    return render_dependencia_contextual_subview(
        request=request,
        dependencia=dependencia,
        partial_template="organigrama/contextual/partials/dependencia_funcionarios.html",
        current_sub_view="organigrama:dependencia_sub_funcionarios",
        extra_context={
            "funcionarios": funcionarios,
            "total_funcionarios": funcionarios.count(),
        },
    )
    

  

# =========================================================================
# 📍 PILAR 4: SUB-FRAGMENTACIÓN (ÁREAS OPERATIVAS Y OFICINAS INTERNAS)
# =========================================================================
@login_required
@axentra_module_gate(AppIdentifier.ORGANIGRAMA, required_fine_permission="has_access_module")
def area_list_view(request):
    """Inventario administrativo de áreas operativas."""

    is_htmx = str(request.headers.get("HX-Request", "")).strip().lower() == "true"
    target_htmx = request.headers.get("HX-Target", "")

    areas = (
        AreaOperativa.objects
        .filter(is_deleted=False)
        .select_related(
            "dependencia",
            "sede_fisica",
        )
        .order_by(
            "dependencia__nombre",
            "sede_fisica__nombre",
            "nombre",
        )
    )

    context = {
        "areas": areas,
        "total_areas": areas.count(),
        "areas_activas": areas.filter(is_active=True).count(),
        "areas_inactivas": areas.filter(is_active=False).count(),
        "modulo_actual": AppIdentifier.ORGANIGRAMA,
        "show_module_sidebar": False,
    }

    if is_htmx and target_htmx == "workbench":
        return render(
            request,
            "organigrama/workbench/area_list_workbench.html",
            context,
        )

    if is_htmx and target_htmx == "page-content":
        return render(
            request,
            "organigrama/content/area_list_content.html",
            context,
        )

    return render(
        request,
        "organigrama/pages/area_list.html",
        context,
    )
    
    
@login_required
@axentra_module_gate(AppIdentifier.ORGANIGRAMA, required_fine_permission="can_mutate_structure")
def area_create_view(request):
    """Alta de áreas operativas que vinculan dependencia administrativa con sede física."""

    is_htmx = str(request.headers.get("HX-Request", "")).strip().lower() == "true"
    target_htmx = request.headers.get("HX-Target", "")

    if request.method == "POST":
        form = AreaOperativaForm(request.POST)

        if form.is_valid():
            payload = {
                "dependencia_id": form.cleaned_data["dependencia"].id,
                "sede_fisica_id": form.cleaned_data["sede_fisica"].id,
                "nombre": form.cleaned_data["nombre"],
            }

            exito, area, errores = OrganigramaService.crear_area(
                request,
                payload,
            )

            if exito:
                messages.success(
                    request,
                    f"Área operativa '{area.nombre}' registrada correctamente.",
                )

                areas = (
                    AreaOperativa.objects
                    .filter(is_deleted=False)
                    .select_related(
                        "dependencia",
                        "sede_fisica",
                    )
                    .order_by(
                        "dependencia__nombre",
                        "sede_fisica__nombre",
                        "nombre",
                    )
                )

                context_list = {
                    "areas": areas,
                    "total_areas": areas.count(),
                    "areas_activas": areas.filter(is_active=True).count(),
                    "areas_inactivas": areas.filter(is_active=False).count(),
                    "modulo_actual": AppIdentifier.ORGANIGRAMA,
                    "show_module_sidebar": False,
                }

                if is_htmx:
                    response = render(
                        request,
                        "organigrama/htmx/area_list_with_messages.html",
                        context_list,
                    )
                    response["HX-Push-Url"] = reverse("organigrama:area_list")
                    return response

                return redirect("organigrama:area_list")

            error_msg = errores.get(
                "server_error",
                ["Fallo en adscripción"],
            )[0]

            messages.error(request, error_msg)
            form.add_error(None, error_msg)

        else:
            messages.error(
                request,
                "Revisa los campos del formulario antes de guardar el área operativa.",
            )

    else:
        form = AreaOperativaForm()

    context = {
        "form": form,
        "action": "create",
        "area": None,
        "modulo_actual": AppIdentifier.ORGANIGRAMA,
        "show_module_sidebar": False,
    }

    if is_htmx and target_htmx == "page-content":
        return render(
            request,
            "organigrama/htmx/area_form_with_messages.html" if request.method == "POST"
            else "organigrama/content/area_form_content.html",
            context,
        )

    return render(
        request,
        "organigrama/pages/area_form.html",
        context,
    )


@login_required
@axentra_module_gate(AppIdentifier.ORGANIGRAMA, required_fine_permission="can_mutate_structure")
def area_update_view(request, pk: uuid.UUID):
    """Modificación contextual de un área operativa."""

    is_htmx = str(request.headers.get("HX-Request", "")).strip().lower() == "true"
    target_htmx = request.headers.get("HX-Target", "")

    area_instancia = get_object_or_404(
        AreaOperativa.objects.select_related(
            "dependencia",
            "sede_fisica",
        ),
        pk=pk,
        is_deleted=False,
    )

    if request.method == "POST":
        form = AreaOperativaForm(request.POST, instance=area_instancia)

        if form.is_valid():
            payload = {
                "dependencia_id": form.cleaned_data["dependencia"].id,
                "sede_fisica_id": form.cleaned_data["sede_fisica"].id,
                "nombre": form.cleaned_data["nombre"],
            }

            exito, errores = OrganigramaService.actualizar_area(
                request,
                area_instancia,
                payload,
            )

            if exito:
                area_instancia.refresh_from_db()

                messages.success(
                    request,
                    f"Área operativa '{area_instancia.nombre}' actualizada correctamente.",
                )

                funcionarios = (
                    UserProfile.objects
                    .filter(
                        area=area_instancia,
                        user__is_deleted=False,
                    )
                    .select_related(
                        "user",
                        "area",
                        "area__dependencia",
                        "area__sede_fisica",
                    )
                    .order_by(
                        "user__first_name",
                        "user__last_name",
                    )
                )

                context_detail = {
                    "area": area_instancia,
                    "dependencia": area_instancia.dependencia,
                    "sede": area_instancia.sede_fisica,
                    "funcionarios": funcionarios,
                    "total_funcionarios": funcionarios.count(),
                    "modulo_actual": AppIdentifier.ORGANIGRAMA,
                    "show_module_sidebar": True,
                }

                if is_htmx and target_htmx == "page-content":
                    response = render(
                        request,
                        "organigrama/htmx/area_identidad_with_messages.html",
                        context_detail,
                    )
                    response["HX-Push-Url"] = reverse(
                        "organigrama:area_sub_identidad",
                        args=[area_instancia.id],
                    )
                    return response

                if is_htmx and target_htmx == "workbench":
                    response = render(
                        request,
                        "organigrama/workbench/area_detail_workbench_with_messages.html",
                        context_detail,
                    )
                    response["HX-Push-Url"] = reverse(
                        "organigrama:area_sub_identidad",
                        args=[area_instancia.id],
                    )
                    return response

                if is_htmx:
                    response = render(
                        request,
                        "organigrama/htmx/area_identidad_with_messages.html",
                        context_detail,
                    )
                    response["HX-Push-Url"] = reverse(
                        "organigrama:area_sub_identidad",
                        args=[area_instancia.id],
                    )
                    return response

                return redirect(
                    "organigrama:area_detail",
                    pk=area_instancia.id,
                )

            error_msg = errores.get(
                "server_error",
                ["Fallo de actualización"],
            )[0]

            messages.error(request, error_msg)
            form.add_error(None, error_msg)

        else:
            messages.error(
                request,
                "Revisa los campos del formulario antes de actualizar el área operativa.",
            )

    else:
        form = AreaOperativaForm(instance=area_instancia)

    return render_area_contextual_subview(
        request=request,
        area=area_instancia,
        partial_template="organigrama/content/area_form_content.html",
        current_sub_view="organigrama:area_sub_identidad",
        extra_context={
            "form": form,
            "action": "update",
            "area": area_instancia,
            "back_label": "Volver a Ficha de Área",
            "back_target": "#page-content",
        },
    )



@require_POST
@login_required
@axentra_module_gate(AppIdentifier.ORGANIGRAMA, required_fine_permission="can_mutate_structure")
def area_soft_delete_view(request, pk: uuid.UUID):
    """Baja lógica protegida de un área operativa."""

    is_htmx = str(request.headers.get("HX-Request", "")).strip().lower() == "true"
    target_htmx = request.headers.get("HX-Target", "")

    area_instancia = get_object_or_404(
        AreaOperativa.objects.select_related(
            "dependencia",
            "sede_fisica",
        ),
        pk=pk,
        is_deleted=False,
    )

    nombre_area = area_instancia.nombre

    exito, errores = OrganigramaService.eliminar_area(
        request,
        area_instancia,
    )

    if exito:
        messages.warning(
            request,
            f"Área operativa '{nombre_area}' enviada a baja lógica correctamente.",
        )

        areas = (
            AreaOperativa.objects
            .filter(is_deleted=False)
            .select_related(
                "dependencia",
                "sede_fisica",
            )
            .order_by(
                "dependencia__nombre",
                "sede_fisica__nombre",
                "nombre",
            )
        )

        context_list = {
            "areas": areas,
            "total_areas": areas.count(),
            "areas_activas": areas.filter(is_active=True).count(),
            "areas_inactivas": areas.filter(is_active=False).count(),
            "modulo_actual": AppIdentifier.ORGANIGRAMA,
            "show_module_sidebar": False,
        }

        if is_htmx:
            response = render(
                request,
                "organigrama/htmx/area_list_with_messages.html",
                context_list,
            )
            response["HX-Push-Url"] = reverse("organigrama:area_list")
            return response

        return redirect("organigrama:area_list")

    error_msg = errores.get(
        "server_error",
        ["No fue posible dar de baja el área operativa."],
    )[0]

    messages.error(request, error_msg)

    funcionarios = (
        UserProfile.objects
        .filter(
            area=area_instancia,
            user__is_deleted=False,
        )
        .select_related(
            "user",
            "area",
            "area__dependencia",
            "area__sede_fisica",
        )
        .order_by(
            "user__first_name",
            "user__last_name",
        )
    )

    raw_menu = OrganigramaPermissions.AREA_DETAIL_MENU
    detail_menu = []
    current_sub_view = "organigrama:area_sub_identidad"

    for item in raw_menu:
        url_name = item.get("url_name")

        if not url_name:
            continue

        required_perm = item.get("permission")

        tiene_permiso = (
            getattr(request, "axentra_is_root", False)
            or required_perm in getattr(request, "axentra_permissions_list", [])
            or f"{AppIdentifier.ORGANIGRAMA}__{required_perm}" in getattr(request, "axentra_permissions_list", [])
        )

        if not tiene_permiso:
            continue

        href = "#"

        if url_name != "#":
            href = reverse(url_name, args=[area_instancia.id])

        detail_menu.append({
            "icon": item.get("icon", "circle"),
            "title": item.get("title", "Sin título"),
            "href": href,
            "order": item.get("order", 99),
            "provider": item.get("provider", "organigrama"),
            "active": url_name == current_sub_view,
        })

    detail_menu.sort(key=lambda item: item["order"])

    context_detail = {
        "area": area_instancia,
        "dependencia": area_instancia.dependencia,
        "sede": area_instancia.sede_fisica,
        "funcionarios": funcionarios,
        "total_funcionarios": funcionarios.count(),
        "detail_menu": detail_menu,
        "modulo_actual": AppIdentifier.ORGANIGRAMA,
        "show_module_sidebar": True,
    }

    if is_htmx and target_htmx == "workbench":
        return render(
            request,
            "organigrama/workbench/area_detail_workbench_with_messages.html",
            context_detail,
        )

    if is_htmx and target_htmx == "page-content":
        return render(
            request,
            "organigrama/htmx/area_identidad_with_messages.html",
            context_detail,
        )

    return redirect(
        "organigrama:area_detail",
        pk=area_instancia.id,
    )



@require_POST
@login_required
@axentra_module_gate(AppIdentifier.ORGANIGRAMA, required_fine_permission="can_mutate_structure")
def area_toggle_status_view(request, pk: uuid.UUID):
    """
    Alternador protegido de estado operativo para áreas.

    Regla Axentra:
    Inactivar un área operativa no desasigna funcionarios.
    La adscripción de funcionarios debe revisarse explícitamente desde Accounts / Funcionarios.
    """

    is_htmx = str(request.headers.get("HX-Request", "")).strip().lower() == "true"
    target_htmx = request.headers.get("HX-Target", "")

    area_instancia = get_object_or_404(
        AreaOperativa.objects.select_related(
            "dependencia",
            "sede_fisica",
        ),
        pk=pk,
        is_deleted=False,
    )

    estado_anterior = area_instancia.is_active

    funcionarios = (
        UserProfile.objects
        .filter(
            area=area_instancia,
            user__is_deleted=False,
        )
        .select_related(
            "user",
            "area",
            "area__dependencia",
            "area__sede_fisica",
        )
        .order_by(
            "user__first_name",
            "user__last_name",
        )
    )

    total_funcionarios = funcionarios.count()

    with transaction.atomic():
        area_instancia.is_active = not area_instancia.is_active
        area_instancia.save(
            update_fields=[
                "is_active",
                "updated_at",
            ]
        )

        ForensicAuditor.registrar_evento(
            request=request,
            action_type=SecurityAuditLog.ActionTypes.UPDATE,
            module_component="AREAS_MATRIZ",
            action_name="TOGGLE_STATUS_AREA_PROTEGIDO",
            target_scope=(
                f"Actualización protegida del estado operativo para el área "
                f"{area_instancia.nombre}. "
                f"Activo anterior: {estado_anterior}. "
                f"Activo final: {area_instancia.is_active}. "
                "No se modificaron funcionarios adscritos."
            ),
            level=SecurityAuditLog.Levels.INFO,
            search_target=str(area_instancia.id),
            payload={
                "area_id": str(area_instancia.id),
                "area_nombre": area_instancia.nombre,
                "dependencia_id": str(area_instancia.dependencia_id),
                "sede_fisica_id": str(area_instancia.sede_fisica_id),
                "estado_anterior": estado_anterior,
                "estado_nuevo": area_instancia.is_active,
                "funcionarios_adscritos": total_funcionarios,
                "cascade_applied": False,
            },
        )

    if area_instancia.is_active:
        messages.success(
            request,
            f"Área operativa '{area_instancia.nombre}' activada correctamente.",
        )
    else:
        if total_funcionarios > 0:
            messages.warning(
                request,
                (
                    f"Área operativa '{area_instancia.nombre}' inactivada. "
                    f"Tiene {total_funcionarios} funcionario(s) adscrito(s). "
                    "Los funcionarios no fueron modificados automáticamente."
                ),
            )
        else:
            messages.warning(
                request,
                f"Área operativa '{area_instancia.nombre}' inactivada correctamente.",
            )

    logger.info(
        f"⚡ AXENTRA OS: Toggle protegido aplicado sobre Área ID=[{area_instancia.id}] "
        f"Estado=[{estado_anterior} -> {area_instancia.is_active}] "
        f"Funcionarios=[{total_funcionarios}]"
    )

    context_detail = {
        "area": area_instancia,
        "dependencia": area_instancia.dependencia,
        "sede": area_instancia.sede_fisica,
        "funcionarios": funcionarios,
        "total_funcionarios": total_funcionarios,
        "modulo_actual": AppIdentifier.ORGANIGRAMA,
        "show_module_sidebar": True,
    }

    if is_htmx and target_htmx == "page-content":
        return render(
            request,
            "organigrama/htmx/area_identidad_with_messages.html",
            context_detail,
        )

    if is_htmx:
        return render(
            request,
            "organigrama/htmx/area_identidad_with_messages.html",
            context_detail,
        )

    return redirect(
        "organigrama:area_detail",
        pk=area_instancia.id,
    )


def render_area_contextual_subview(
    request,
    area: AreaOperativa,
    partial_template: str,
    current_sub_view: str,
    extra_context: dict | None = None,
):
    """
    Render inteligente para subvistas del expediente contextual de área.

    HTMX:
        devuelve sólo el partial para reemplazar #page-content.

    Normal/F5:
        devuelve página completa con shell + sidebar secundario + partial.
    """

    is_htmx = str(request.headers.get("HX-Request", "")).strip().lower() == "true"

    funcionarios_base = (
        UserProfile.objects
        .filter(
            area=area,
            user__is_deleted=False,
        )
        .select_related(
            "user",
            "area",
            "area__dependencia",
            "area__sede_fisica",
        )
        .order_by("user__first_name", "user__last_name")
    )

    raw_menu = OrganigramaPermissions.AREA_DETAIL_MENU
    detail_menu = []

    for item in raw_menu:
        url_name = item.get("url_name")

        if not url_name:
            continue

        required_perm = item.get("permission")

        tiene_permiso = (
            getattr(request, "axentra_is_root", False)
            or required_perm in getattr(request, "axentra_permissions_list", [])
            or f"{AppIdentifier.ORGANIGRAMA}__{required_perm}" in getattr(request, "axentra_permissions_list", [])
        )

        if not tiene_permiso:
            continue

        href = "#"

        if url_name != "#":
            href = reverse(url_name, args=[area.id])

        detail_menu.append({
            "icon": item.get("icon", "circle"),
            "title": item.get("title", "Sin título"),
            "href": href,
            "order": item.get("order", 99),
            "provider": item.get("provider", "organigrama"),
            "active": url_name == current_sub_view,
        })

    detail_menu.sort(key=lambda item: item["order"])

    context = {
        "area": area,
        "dependencia": area.dependencia,
        "sede": area.sede_fisica,
        "funcionarios": funcionarios_base,
        "total_funcionarios": funcionarios_base.count(),
        "detail_menu": detail_menu,
        "partial_template": partial_template,
        "current_sub_view": current_sub_view,
        "modulo_actual": AppIdentifier.ORGANIGRAMA,
        "show_module_sidebar": True,
    }

    if extra_context:
        context.update(extra_context)

    if is_htmx:
        return render(request, partial_template, context)

    return render(
        request,
        "organigrama/pages/area_subpage.html",
        context,
    )
    
    
@login_required
@axentra_module_gate(AppIdentifier.ORGANIGRAMA, required_fine_permission="has_access_module")
def area_detail_view(request, pk: uuid.UUID):
    """Expediente contextual de un área operativa."""

    is_htmx = str(request.headers.get("HX-Request", "")).strip().lower() == "true"
    target_htmx = request.headers.get("HX-Target", "")

    area = get_object_or_404(
        AreaOperativa.objects.select_related(
            "dependencia",
            "sede_fisica",
        ),
        pk=pk,
        is_deleted=False,
    )

    funcionarios = (
        UserProfile.objects
        .filter(
            area=area,
            user__is_deleted=False,
        )
        .select_related(
            "user",
            "area",
            "area__dependencia",
            "area__sede_fisica",
        )
        .order_by("user__first_name", "user__last_name")
    )

    raw_menu = OrganigramaPermissions.AREA_DETAIL_MENU
    detail_menu = []

    current_sub_view = request.GET.get(
        "sub_view",
        "organigrama:area_sub_identidad",
    )

    for item in raw_menu:
        url_name = item.get("url_name")

        if not url_name:
            continue

        required_perm = item.get("permission")

        tiene_permiso = (
            getattr(request, "axentra_is_root", False)
            or required_perm in getattr(request, "axentra_permissions_list", [])
            or f"{AppIdentifier.ORGANIGRAMA}__{required_perm}" in getattr(request, "axentra_permissions_list", [])
        )

        if not tiene_permiso:
            continue

        href = "#"

        if url_name != "#":
            href = reverse(url_name, args=[area.id])

        detail_menu.append({
            "icon": item.get("icon", "circle"),
            "title": item.get("title", "Sin título"),
            "href": href,
            "order": item.get("order", 99),
            "provider": item.get("provider", "organigrama"),
            "active": url_name == current_sub_view,
        })

    detail_menu.sort(key=lambda item: item["order"])

    context = {
        "area": area,
        "dependencia": area.dependencia,
        "sede": area.sede_fisica,
        "funcionarios": funcionarios,
        "total_funcionarios": funcionarios.count(),
        "detail_menu": detail_menu,
        "modulo_actual": AppIdentifier.ORGANIGRAMA,
        "show_module_sidebar": True,
    }

    if is_htmx and target_htmx == "workbench":
        return render(
            request,
            "organigrama/workbench/area_detail_workbench.html",
            context,
        )

    return render(
        request,
        "organigrama/pages/area_detail.html",
        context,
    )
    

@login_required
@axentra_module_gate(AppIdentifier.ORGANIGRAMA, required_fine_permission="has_access_module")
def area_sub_identidad_view(request, pk: uuid.UUID):
    """Subvista de identidad del expediente contextual de área."""

    area = get_object_or_404(
        AreaOperativa.objects.select_related(
            "dependencia",
            "sede_fisica",
        ),
        pk=pk,
        is_deleted=False,
    )

    return render_area_contextual_subview(
        request=request,
        area=area,
        partial_template="organigrama/contextual/partials/area_identidad.html",
        current_sub_view="organigrama:area_sub_identidad",
    )
    
    
@login_required
@axentra_module_gate(AppIdentifier.ORGANIGRAMA, required_fine_permission="has_access_module")
def area_sub_funcionarios_view(request, pk: uuid.UUID):
    """Subvista de funcionarios adscritos a un área operativa."""

    area = get_object_or_404(
        AreaOperativa.objects.select_related(
            "dependencia",
            "sede_fisica",
        ),
        pk=pk,
        is_deleted=False,
    )

    funcionarios = (
        UserProfile.objects
        .filter(
            area=area,
            user__is_deleted=False,
        )
        .select_related(
            "user",
            "area",
            "area__dependencia",
            "area__sede_fisica",
        )
        .order_by("user__first_name", "user__last_name")
    )

    return render_area_contextual_subview(
        request=request,
        area=area,
        partial_template="organigrama/contextual/partials/area_funcionarios.html",
        current_sub_view="organigrama:area_sub_funcionarios",
        extra_context={
            "funcionarios": funcionarios,
            "total_funcionarios": funcionarios.count(),
        },
    )
    
    






# =========================================================================
# ⚡ PILAR 5: TUBERÍAS REACTIVAS ASÍNCRONAS (HTMX PIPELINES)
# =========================================================================

@login_required
@axentra_module_gate(AppIdentifier.ORGANIGRAMA, required_fine_permission="has_access_module")
def cargar_areas_htmx_view(request):
    """Hidratación en cascada de selectores secundarios dependientes."""
    dependencia_id = request.GET.get('dependencia')
    try:
        areas = AreaOperativa.objects.filter(dependencia_id=uuid.UUID(dependencia_id), is_deleted=False)
    except (ValueError, TypeError):
        areas = []
    return render(request, 'organigrama/htmx/area_options.html', {'areas': areas})


@login_required
@axentra_module_gate(AppIdentifier.ORGANIGRAMA, required_fine_permission="has_access_module")
def vincular_areas_ajax_view(request, dep_id):
    """Despacha la matriz de sub-oficinas de una dependencia usando el accesor premium inverso."""
    dependencia = get_object_or_404(Dependencia, id=dep_id, is_deleted=False)
    areas = dependencia.areas.filter(is_deleted=False).select_related('sede_fisica')
    
    return render(request, 'organigrama/estructura_areas_table.html', {
        'dependencia': dependencia,
        'areas': areas,
        'request': request
    })
