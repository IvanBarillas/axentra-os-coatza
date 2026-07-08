# apps/security/views/accounts_views.py
import uuid
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.http import HttpResponse
from django.contrib.auth.forms import SetPasswordForm

from apps.security.models.audit import SecurityAuditLog
from apps.security.permissions import AccountsPermissions
from apps.security.utils.forensic_auditor import ForensicAuditor
from apps.shared.apps_config import AppIdentifier
from apps.security.decorators import axentra_gate_enforcer
from apps.security.models import User, UserProfile
from apps.security.models.organigrama import Dependencia, AreaOperativa, Sede
from apps.security.selectors.accounts_selectors import AccountsDashboardSelectors, FuncionarioSelectors
from apps.security.services.accounts_services import FuncionarioService
from apps.security.forms import (
    StaffUserCreationForm, StaffUserProfileForm, 
    StaffUserChangeForm, StaffUserProfileChangeForm, 
    AdminPasswordChangeForm
)

from apps.shared.utils.telemetry import AxentraRadar

User = get_user_model()
logger = logging.getLogger(__name__)

@login_required
@axentra_gate_enforcer(module_identifier="accounts", required_fine_permission="can_view_analytics")
def accounts_dashboard_view(request):
    """Consola Analítica de Personal."""
    context = AccountsDashboardSelectors.obtener_metricas_plantilla()
    context['cronologia_altas'] = AccountsDashboardSelectors.obtener_cronologia_altas()
    
    # 📡 CONTROL PERIMETRAL DE HTMX (Evita duplicar layouts exteriores en llamadas asíncronas)
    es_htmx = request.headers.get('HX-Request') == 'true' or request.headers.get('hx-request') == 'true'
    context['base_template'] = "layouts/blank_layout.html" if es_htmx else "layouts/dashboard_layout.html"
    
    # 👑 LA JUGADA MAESTRA: Tu bandera de control arquitectónico
    context['sidebar_secundario'] = True 
    context['modulo_actual'] = request.axentra_active_module.upper() # Inyectado por tu decorador
    context['menu_actual'] = request.axentra_sidebar_menu          # Inyectado por tu decorador
    
    return render(request, 'accounts/dashboard/accounts_dashboard.html', context)


# =========================================================================
# 👤 PILAR UNIQUE: GESTIÓN DE EXPEDIENTES Y SERVIDORES PÚBLICOS
# =========================================================================
@axentra_gate_enforcer(AppIdentifier.ACCOUNTS, required_fine_permission="can_view_list")
def funcionario_list_view(request):
    """
    👥 CONTROLADOR DE PADRÓN DE FUNCIONARIOS

    Tipo de pantalla:
    - Pertenece al módulo ACCOUNTS.
    - No usa sidebar secundario.
    - Click desde sidebar azul reemplaza todo #workbench.
    - Filtros internos reemplazan sólo #funcionario-results.
    """
    is_htmx = str(request.headers.get("HX-Request", "")).strip().lower() == "true"
    target_htmx = request.headers.get("HX-Target", "")

    AxentraRadar.imprimir_auditoria(
        componente="accounts_view",
        request=request,
        titulo="Entrada a funcionario_list_view",
        icono="🛰️",
        extra_data={
            "¿Es petición HTMX?": is_htmx,
            "HX-Target Recibido": target_htmx if target_htmx else "NINGUNO",
            "HX-Current-URL": request.headers.get("HX-Current-URL", "N/A"),
            "Parámetros GET (q)": request.GET.get("q", "Vacío"),
            "Parámetros GET (sede)": request.GET.get("sede", "Vacío"),
            "Parámetros GET (dependencia)": request.GET.get("dependencia", "Vacío"),
        },
    )

    search_query = request.GET.get("q", "").strip()
    sede_id = request.GET.get("sede", "").strip()
    dependencia_id = request.GET.get("dependencia", "").strip()

    funcionarios = FuncionarioSelectors.listar_plantilla_activa(
        search_query=search_query,
        sede_id=sede_id if sede_id.lower() not in ["all", ""] else "",
        dependencia_id=dependencia_id if dependencia_id.lower() not in ["all", ""] else "",
    )

    if request.axentra_is_root or not getattr(request.user, "axentra_profile", None):
        sedes = Sede.objects.filter(is_deleted=False).order_by("nombre")
        dependencias = Dependencia.objects.filter(is_deleted=False).order_by("nombre")
    else:
        profile = request.user.axentra_profile

        sedes = (
            Sede.objects.filter(id=profile.sede.id, is_deleted=False)
            if profile.sede
            else Sede.objects.none()
        )

        dependencias = (
            Dependencia.objects.filter(id=profile.dependencia.id, is_deleted=False)
            if profile.dependencia
            else Dependencia.objects.none()
        )

    if hasattr(funcionarios, "model"):
        total_funcionarios = funcionarios.count()
    else:
        total_funcionarios = len(funcionarios)

    context = {
        "funcionarios": funcionarios,
        "sedes": sedes,
        "dependencias": dependencias,
        "current_q": search_query,
        "current_sede": request.GET.get("sede", ""),
        "current_dep": request.GET.get("dependencia", ""),

        # Contrato Axentra
        "modulo_actual": AppIdentifier.ACCOUNTS,
        "show_module_sidebar": False,
    }

    AxentraRadar.imprimir_auditoria(
        componente="accounts_view",
        request=request,
        titulo="Despacho de Región HTMX",
        icono="📡",
        extra_data={
            "HX-Target": target_htmx if target_htmx else "F5 / URL directa",
            "Módulo": context["modulo_actual"],
            "Sidebar Secundario": context["show_module_sidebar"],
            "Registros": total_funcionarios,
        },
    )

    # 1. Click desde sidebar azul:
    #    reemplaza TODO el workbench, pero SIN sidebar secundario.
    if is_htmx and target_htmx == "workbench":
        return render(
            request,
            "accounts/workbench/funcionario_list_workbench.html",
            context,
        )

    # 2. Si por alguna razón se pide sólo el contenido:
    #    reemplaza únicamente #page-content.
    if is_htmx and target_htmx == "page-content":
        return render(
            request,
            "accounts/pages/funcionario_list_content.html",
            context,
        )

    # 3. Filtros, búsqueda, paginación:
    #    reemplaza sólo la región interna de resultados.
    if is_htmx and target_htmx == "funcionario-results":
        return render(
            request,
            "accounts/htmx/funcionario_hibrido_partial.html",
            context,
        )

    # 4. F5 / URL directa:
    #    carga completa: shell + workbench, pero sin sidebar secundario.
    return render(
        request,
        "accounts/pages/funcionario_list.html",
        context,
    )

@login_required
@axentra_gate_enforcer(AppIdentifier.ACCOUNTS, required_fine_permission="can_view_list")
def funcionario_detail_view(request, pk: uuid.UUID):
    """
    👤 EXPEDIENTE CONTEXTUAL DE FUNCIONARIO

    Tipo de pantalla:
    - Pertenece a ACCOUNTS.
    - Sí usa sidebar secundario.
    - El sidebar secundario es contextual al funcionario.
    - La vista inicial del contenido es Ficha de Identidad.
    """
    is_htmx = str(request.headers.get("HX-Request", "")).strip().lower() == "true"
    target_htmx = request.headers.get("HX-Target", "")

    UserModel = get_user_model()
    funcionario = get_object_or_404(UserModel, id=pk)
    perfil = getattr(funcionario, "axentra_profile", None)

    raw_menu = AccountsPermissions.FUNCIONARIO_DETAIL_MENU

    detail_menu = []

    for icon, title, url_name, order, required_perm in raw_menu:
        tiene_permiso = (
            request.axentra_is_root
            or required_perm in getattr(request, "axentra_permissions_list", [])
            or f"{AppIdentifier.ACCOUNTS}__{required_perm}" in getattr(request, "axentra_permissions_list", [])
        )

        if tiene_permiso:
            detail_menu.append({
                "icon": icon,
                "title": title,
                "href": reverse(url_name, args=[funcionario.id]),
                "order": order,
                "active": url_name == "accounts:funcionario_sub_identidad",
            })

    detail_menu.sort(key=lambda item: item["order"])

    context = {
        "funcionario": funcionario,
        "perfil": perfil,
        "current_funcionario": funcionario,
        "detail_menu": detail_menu,

        # Contrato Axentra
        "modulo_actual": AppIdentifier.ACCOUNTS,
        "show_module_sidebar": True,
    }

    AxentraRadar.imprimir_auditoria(
        componente="accounts_view",
        request=request,
        titulo="Entrada a funcionario_detail_view",
        icono="🧬",
        extra_data={
            "Funcionario": funcionario.email,
            "Funcionario ID": str(funcionario.id),
            "¿Es petición HTMX?": is_htmx,
            "HX-Target": target_htmx if target_htmx else "F5 / URL directa",
            "Sidebar Contextual": True,
            "Items Contextuales": len(detail_menu),
        },
    )

    if is_htmx and target_htmx == "workbench":
        return render(
            request,
            "accounts/workbench/funcionario_detail_workbench.html",
            context,
        )

    return render(
        request,
        "accounts/pages/funcionario_detail.html",
        context,
    )
    
    

@login_required
@axentra_gate_enforcer(AppIdentifier.ACCOUNTS, required_fine_permission="can_create_user")
def funcionario_create_view(request):
    """
    👤 CONTROLADOR DE ALTA DE FUNCIONARIOS

    Tipo de pantalla:
    - Pertenece al módulo ACCOUNTS.
    - No usa sidebar secundario.
    - Normalmente se carga dentro de #page-content.
    - En POST exitoso redirige al listado.
    """
    is_htmx = str(request.headers.get("HX-Request", "")).strip().lower() == "true"
    target_htmx = request.headers.get("HX-Target", "")

    AxentraRadar.imprimir_auditoria(
        componente="accounts_view",
        request=request,
        titulo="Entrada a funcionario_create_view",
        icono="🧾",
        extra_data={
            "Método": request.method,
            "¿Es petición HTMX?": is_htmx,
            "HX-Target Recibido": target_htmx if target_htmx else "NINGUNO",
            "HX-Current-URL": request.headers.get("HX-Current-URL", "N/A"),
        },
    )

    if request.method == "POST":
        datos_saneados = request.POST.copy()

        if "area" in datos_saneados and not datos_saneados["area"].strip():
            datos_saneados["area"] = ""

        form = StaffUserCreationForm(datos_saneados)
        profile_form = StaffUserProfileForm(datos_saneados)

        if form.is_valid() and profile_form.is_valid():
            area_instancia = profile_form.cleaned_data.get("area")

            payload = {
                "email": form.cleaned_data.get("email"),
                "first_name": form.cleaned_data.get("first_name"),
                "last_name": form.cleaned_data.get("last_name"),
                "phone": form.cleaned_data.get("phone"),
                "area_id": area_instancia.id if area_instancia else None,
                "puesto": profile_form.cleaned_data.get("puesto"),
                "telefono_oficina": profile_form.cleaned_data.get("telefono_oficina"),
            }

            exito, usuario, errores = FuncionarioService.crear_funcionario(
                request=request,
                post_data=payload,
                raw_password=form.cleaned_data.get("password"),
            )

            if exito and usuario:
                messages.success(
                    request,
                    f"El funcionario {usuario.full_name} ha sido dado de alta con éxito.",
                )

                if is_htmx:
                    response = HttpResponse(status=204)
                    response["HX-Redirect"] = reverse("accounts:funcionario_list")
                    return response

                return redirect("accounts:funcionario_list")

            if errores:
                form.add_error(
                    None,
                    errores.get("server_error", ["Error de consistencia interna"])[0],
                )

    else:
        form = StaffUserCreationForm()
        profile_form = StaffUserProfileForm()

    context = {
        "form": form,
        "profile_form": profile_form,

        # Contrato Axentra
        "modulo_actual": AppIdentifier.ACCOUNTS,
        "show_module_sidebar": False,
    }

    AxentraRadar.imprimir_auditoria(
        componente="accounts_view",
        request=request,
        titulo="Despacho de Formulario de Alta",
        icono="📡",
        extra_data={
            "HX-Target": target_htmx if target_htmx else "F5 / URL directa",
            "Módulo": context["modulo_actual"],
            "Sidebar Secundario": context["show_module_sidebar"],
            "Errores Form": form.errors.as_data() if form.errors else "Sin errores",
            "Errores Profile Form": profile_form.errors.as_data() if profile_form.errors else "Sin errores",
        },
    )

    if is_htmx and target_htmx == "page-content":
        return render(
            request,
            "accounts/forms/funcionario_create_form_content.html",
            context,
        )

    return render(
        request,
        "accounts/forms/funcionario_form.html",
        context,
    )

@login_required
@axentra_gate_enforcer(AppIdentifier.ACCOUNTS, required_fine_permission="can_edit_user")
def funcionario_editar_view(request, pk: uuid.UUID):
    """
    👤 CONTROLADOR DE EDICIÓN DE FUNCIONARIOS

    Tipo de pantalla:
    - Pertenece al módulo ACCOUNTS.
    - Normalmente se carga dentro de #page-content.
    - Si se guarda por HTMX, regresa a sub_identidad.html.
    - No regresa al listado.
    """
    is_htmx = str(request.headers.get("HX-Request", "")).strip().lower() == "true"
    target_htmx = request.headers.get("HX-Target", "")

    usuario_instance = get_object_or_404(User, id=pk)
    perfil_instance = get_object_or_404(UserProfile, user=usuario_instance)

    AxentraRadar.imprimir_auditoria(
        componente="accounts_view",
        request=request,
        titulo="Entrada a funcionario_editar_view",
        icono="📝",
        extra_data={
            "Método": request.method,
            "Funcionario Target": usuario_instance.email,
            "Funcionario ID": str(usuario_instance.id),
            "¿Es petición HTMX?": is_htmx,
            "HX-Target Recibido": target_htmx if target_htmx else "NINGUNO",
            "HX-Current-URL": request.headers.get("HX-Current-URL", "N/A"),
        },
    )

    if request.method == "POST":
        datos_saneados = request.POST.copy()

        if "area" in datos_saneados and not datos_saneados["area"].strip():
            datos_saneados["area"] = ""

        form_user = StaffUserChangeForm(
            datos_saneados,
            instance=usuario_instance,
        )

        form_profile = StaffUserProfileChangeForm(
            datos_saneados,
            instance=perfil_instance,
        )

        if form_user.is_valid() and form_profile.is_valid():
            area_instancia = form_profile.cleaned_data.get("area")

            payload = {
                "email": form_user.cleaned_data.get("email"),
                "first_name": form_user.cleaned_data.get("first_name"),
                "last_name": form_user.cleaned_data.get("last_name"),
                "phone": form_user.cleaned_data.get("phone"),
                "area_id": area_instancia.id if area_instancia else None,
                "puesto": form_profile.cleaned_data.get("puesto"),
                "telefono_oficina": form_profile.cleaned_data.get("telefono_oficina"),
            }

            exito, usuario, errores = FuncionarioService.editar_funcionario(
                request=request,
                pk=pk,
                post_data=payload,
            )

            if exito:
                messages.success(
                    request,
                    f"La ficha de {usuario.full_name} se actualizó correctamente.",
                )

                if is_htmx:
                    usuario_refrescado = get_object_or_404(User, id=pk)
                    perfil_refrescado = get_object_or_404(UserProfile, user=usuario_refrescado)

                    response = render(
                        request,
                        "accounts/contextual/partials/sub_identidad.html",
                        {
                            "funcionario": usuario_refrescado,
                            "perfil": perfil_refrescado,
                            "modulo_actual": AppIdentifier.ACCOUNTS,
                            "show_module_sidebar": True,
                        },
                    )

                    response["HX-Push-Url"] = reverse(
                        "accounts:funcionario_detail",
                        args=[pk],
                    )

                    return response

                return redirect("accounts:funcionario_detail", pk=pk)

            if errores:
                form_user.add_error(
                    None,
                    errores.get("server_error", ["Fallo del Servidor"])[0],
                )

    else:
        form_user = StaffUserChangeForm(instance=usuario_instance)
        form_profile = StaffUserProfileChangeForm(instance=perfil_instance)

    context = {
        "form_user": form_user,
        "form_profile": form_profile,
        "funcionario": usuario_instance,

        # Contrato Axentra
        "modulo_actual": AppIdentifier.ACCOUNTS,
        "show_module_sidebar": True,
    }

    AxentraRadar.imprimir_auditoria(
        componente="accounts_view",
        request=request,
        titulo="Despacho de Formulario de Edición",
        icono="📡",
        extra_data={
            "HX-Target": target_htmx if target_htmx else "F5 / URL directa",
            "Módulo": context["modulo_actual"],
            "Sidebar Contextual": context["show_module_sidebar"],
            "Funcionario": usuario_instance.email,
            "Errores User Form": form_user.errors.as_data() if form_user.errors else "Sin errores",
            "Errores Profile Form": form_profile.errors.as_data() if form_profile.errors else "Sin errores",
        },
    )

    if is_htmx and target_htmx == "page-content":
        return render(
            request,
            "accounts/forms/funcionario_update_form_content.html",
            context,
        )

    return render(
        request,
        "accounts/forms/funcionario_update_form.html",
        context,
    )

@login_required
@axentra_gate_enforcer(AppIdentifier.ACCOUNTS, required_fine_permission="can_change_password")
def funcionario_cambiar_password_view(request, pk: uuid.UUID):
    """
    🔐 CONTROLADOR DE ROTACIÓN ADMINISTRATIVA DE CONTRASEÑAS

    Tipo de pantalla:
    - Pertenece al módulo ACCOUNTS.
    - Normalmente se carga dentro de #page-content.
    - Si se guarda por HTMX, regresa a sub_identidad.html.
    - No regresa al listado.
    """
    is_htmx = str(request.headers.get("HX-Request", "")).strip().lower() == "true"
    target_htmx = request.headers.get("HX-Target", "")

    UserModel = get_user_model()
    usuario_instance = get_object_or_404(UserModel, id=pk)

    AxentraRadar.imprimir_auditoria(
        componente="accounts_view",
        request=request,
        titulo="Entrada a funcionario_cambiar_password_view",
        icono="🔐",
        extra_data={
            "Método": request.method,
            "Funcionario Target": usuario_instance.email,
            "Funcionario ID": str(usuario_instance.id),
            "¿Es petición HTMX?": is_htmx,
            "HX-Target Recibido": target_htmx if target_htmx else "NINGUNO",
            "HX-Current-URL": request.headers.get("HX-Current-URL", "N/A"),
        },
    )

    if request.method == "POST":
        form = SetPasswordForm(
            user=usuario_instance,
            data=request.POST,
        )

        if form.is_valid():
            nueva_password = form.cleaned_data.get("new_password1")

            success = FuncionarioService.forzar_reseteo_password(
                request=request,
                pk=pk,
                nueva_password=nueva_password,
            )

            if success:
                messages.success(
                    request,
                    f"Credenciales restablecidas con éxito para {usuario_instance.full_name}.",
                )

                if is_htmx:
                    usuario_refrescado = get_object_or_404(UserModel, id=pk)
                    perfil_refrescado = getattr(usuario_refrescado, "axentra_profile", None)

                    response = render(
                        request,
                        "accounts/contextual/partials/sub_identidad.html",
                        {
                            "funcionario": usuario_refrescado,
                            "perfil": perfil_refrescado,
                            "modulo_actual": AppIdentifier.ACCOUNTS,
                            "show_module_sidebar": True,
                        },
                    )

                    response["HX-Push-Url"] = reverse(
                        "accounts:funcionario_detail",
                        args=[pk],
                    )

                    return response

                return redirect("accounts:funcionario_detail", pk=pk)

            messages.error(
                request,
                "No se pudo restablecer la credencial en el Core.",
            )

    else:
        form = SetPasswordForm(user=usuario_instance)

    context = {
        "form": form,
        "funcionario": usuario_instance,

        # Contrato Axentra
        "modulo_actual": AppIdentifier.ACCOUNTS,
        "show_module_sidebar": True,
    }

    AxentraRadar.imprimir_auditoria(
        componente="accounts_view",
        request=request,
        titulo="Despacho de Formulario de Rotación de Password",
        icono="📡",
        extra_data={
            "HX-Target": target_htmx if target_htmx else "F5 / URL directa",
            "Módulo": context["modulo_actual"],
            "Sidebar Contextual": context["show_module_sidebar"],
            "Funcionario": usuario_instance.email,
            "Errores Form": form.errors.as_data() if form.errors else "Sin errores",
        },
    )

    if is_htmx and target_htmx == "page-content":
        return render(
            request,
            "accounts/forms/funcionario_password_form_content.html",
            context,
        )

    return render(
        request,
        "accounts/forms/funcionario_password_form.html",
        context,
    )


@require_POST
@login_required
@axentra_gate_enforcer(AppIdentifier.ACCOUNTS, required_fine_permission="can_delete_user")
def funcionario_soft_delete_view(request, pk: uuid.UUID):
    """
    🗑️ BAJA LÓGICA FORENSE DE FUNCIONARIO

    Tipo de acción:
    - Acción crítica.
    - Se ejecuta desde el expediente del funcionario.
    - Después de aplicar la baja, regresa al listado.
    """
    is_htmx = str(request.headers.get("HX-Request", "")).strip().lower() == "true"
    target_htmx = request.headers.get("HX-Target", "")

    if str(pk) == str(request.user.id):
        if is_htmx:
            return HttpResponse(
                status=403,
                content="Operación denegada sobre su propia sesión.",
            )

        messages.error(
            request,
            "Operación denegada: No puede aplicar una baja sobre su propia sesión.",
        )

        return redirect("accounts:funcionario_detail", pk=pk)

    funcionario = get_object_or_404(User, id=pk)

    AxentraRadar.imprimir_auditoria(
        componente="accounts_view",
        request=request,
        titulo="Solicitud de baja lógica institucional",
        icono="🗑️",
        extra_data={
            "Funcionario Target": funcionario.email,
            "Funcionario ID": str(funcionario.id),
            "Operador": request.user.email,
            "¿Es HTMX?": is_htmx,
            "HX-Target": target_htmx if target_htmx else "NINGUNO",
        },
    )

    exito, mensaje = FuncionarioService.tramitar_baja_institucional(
        request=request,
        pk=pk,
        operador_email=request.user.email,
    )

    if exito:
        messages.warning(request, mensaje)
    else:
        messages.error(request, mensaje)

    if is_htmx:
        response = HttpResponse(status=204)
        response["HX-Redirect"] = reverse("accounts:funcionario_list")
        return response

    return redirect("accounts:funcionario_list")


@require_POST
@login_required
@axentra_gate_enforcer(AppIdentifier.ACCOUNTS, required_fine_permission="can_edit_user")
def funcionario_toggle_status_view(request, pk: uuid.UUID):
    """
    🟢 ALTERNADOR DE ESTATUS OPERATIVO

    Compatibilidad:
    - Si viene desde expediente con hx-target="#page-content":
      devuelve sub_identidad.html completo.
    - Si viene desde un badge compacto con hx-target="this":
      devuelve badge_toggle_activo_inactivo.html.
    """
    is_htmx = str(request.headers.get("HX-Request", "")).strip().lower() == "true"
    target_htmx = request.headers.get("HX-Target", "")

    if str(pk) == str(request.user.id):
        return HttpResponse(
            status=403,
            content="Bloqueo de seguridad: Auto-congelación denegada.",
        )

    funcionario = get_object_or_404(User, id=pk)

    if funcionario.is_deleted:
        return HttpResponse(
            status=400,
            content="No se puede conmutar el estatus de un usuario dado de baja.",
        )

    estado_anterior = funcionario.is_active

    funcionario.is_active = not funcionario.is_active
    funcionario.save(update_fields=["is_active"])

    ForensicAuditor.registrar_evento(
        request=request,
        action_type=SecurityAuditLog.ActionTypes.UPDATE,
        module_component="MATRIZ_PERMISOS",
        action_name="TOGGLE_STATUS_FUNCIONARIO",
        target_scope=(
            f"Conmutación de estatus de cuenta para {funcionario.email} "
            f"(Estado final: {funcionario.is_active})."
        ),
        level=(
            SecurityAuditLog.Levels.INFO
            if funcionario.is_active
            else SecurityAuditLog.Levels.CRITICAL
        ),
        target_user=funcionario,
        search_target=funcionario.id,
        payload={
            "is_active_before": estado_anterior,
            "is_active_after": funcionario.is_active,
        },
    )

    AxentraRadar.imprimir_auditoria(
        componente="accounts_view",
        request=request,
        titulo="Conmutación de estatus de funcionario",
        icono="🟢" if funcionario.is_active else "⚫",
        extra_data={
            "Funcionario": funcionario.email,
            "Funcionario ID": str(funcionario.id),
            "Estado Anterior": "ACTIVO" if estado_anterior else "INACTIVO",
            "Estado Nuevo": "ACTIVO" if funcionario.is_active else "INACTIVO",
            "¿Es HTMX?": is_htmx,
            "HX-Target": target_htmx if target_htmx else "NINGUNO",
        },
    )

    perfil = getattr(funcionario, "axentra_profile", None)

    # Caso nuevo: llamado desde sub_identidad.html
    if is_htmx and target_htmx == "page-content":
        response = render(
            request,
            "accounts/contextual/partials/sub_identidad.html",
            {
                "funcionario": funcionario,
                "perfil": perfil,
                "modulo_actual": AppIdentifier.ACCOUNTS,
                "show_module_sidebar": True,
            },
        )

        response["HX-Push-Url"] = reverse(
            "accounts:funcionario_detail",
            args=[funcionario.id],
        )

        return response

    # Caso viejo: badge compacto, por si todavía lo usas en alguna tabla
    if is_htmx:
        return render(
            request,
            "common/tags/badge_toggle_activo_inactivo.html",
            {
                "is_active": funcionario.is_active,
                "toggle_url": reverse(
                    "accounts:funcionario_toggle_status",
                    args=[funcionario.id],
                ),
            },
        )

    return redirect("accounts:funcionario_detail", pk=pk)



@login_required
@axentra_gate_enforcer(AppIdentifier.ACCOUNTS, required_fine_permission="can_edit_user")
def funcionario_sub_identidad_view(request, pk: uuid.UUID):
    funcionario = get_object_or_404(User, id=pk)
    perfil = getattr(funcionario, "axentra_profile", None)

    return render(
        request,
        "accounts/contextual/partials/sub_identidad.html",
        {
            "funcionario": funcionario,
            "perfil": perfil,
            "modulo_actual": AppIdentifier.ACCOUNTS,
            "show_module_sidebar": True,
        },
    )


@login_required
@axentra_gate_enforcer(AppIdentifier.ACCOUNTS, required_fine_permission="can_edit_user")
def funcionario_sub_hardware_view(request, pk: uuid.UUID):
    funcionario = get_object_or_404(User, id=pk)

    activos_simulados = [
        {
            "codigo_inventario": "AXN-HW-2026-0891",
            "nombre": "Laptop ThinkPad L14 Gen 4",
            "categoria": "Cómputo Portátil",
            "estado": "Asignado / Excelente",
            "fecha_resguardo": "15 Ene 2026",
        },
        {
            "codigo_inventario": 'AXN-HW-2026-1044',
            "nombre": 'Monitor Dell 24" P2422H',
            "categoria": "Periféricos de Video",
            "estado": "Asignado / Operativo",
            "fecha_resguardo": "20 Ene 2026",
        },
    ]

    return render(
        request,
        "accounts/contextual/partials/sub_hardware.html",
        {
            "funcionario": funcionario,
            "activos": activos_simulados,
            "modulo_actual": AppIdentifier.ACCOUNTS,
            "show_module_sidebar": True,
        },
    )


@login_required
@axentra_gate_enforcer(AppIdentifier.ACCOUNTS, required_fine_permission="can_edit_user")
def funcionario_sub_telefonia_view(request, pk: uuid.UUID):
    funcionario = get_object_or_404(User, id=pk)

    extensiones_simuladas = [
        {
            "numero_extension": "4502",
            "tipo_linea": "IP / Conmutador Central",
            "modelo_aparato": "Cisco IP Phone 7821",
            "estatus": "Activa",
            "perfil_marcado": "Nacional / Celular",
        }
    ]

    return render(
        request,
        "accounts/contextual/partials/sub_telefonia.html",
        {
            "funcionario": funcionario,
            "extensiones": extensiones_simuladas,
            "modulo_actual": AppIdentifier.ACCOUNTS,
            "show_module_sidebar": True,
        },
    )