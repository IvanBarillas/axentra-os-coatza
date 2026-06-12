# apps/security/views/organigrama_views.py
import logging
import uuid
import json
from django.db.models import Count
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.db import transaction

from apps.shared.apps_config import AppIdentifier
from apps.security.decorators import axentra_gate_enforcer
from apps.security.models.organigrama import Sede, Dependencia, AreaOperativa
from apps.security.models.audit import SecurityAuditLog
from apps.security.selectors.organigrama_selectors import SedeSelectors, DependenciaSelectors, AreaOperativaSelectors
from apps.security.services.organigrama_services import OrganigramaService
from apps.security.forms import SedeForm, DependenciaForm, AreaOperativaForm
from apps.security.utils.forensic_auditor import ForensicAuditor

User = get_user_model()
logger = logging.getLogger(__name__)


# =========================================================================
# 📊 PILAR 1: CUADROS DE MANDO Y REJILLAS PRINCIPALES (ANALYTICS & CONTROL)
# =========================================================================

@login_required
@axentra_gate_enforcer(AppIdentifier.ORGANIGRAMA, required_fine_permission="has_access_module")
def organigrama_control_view(request):
    """Cuarto de Control General: Enrutador táctico de alta velocidad sin carga analítica."""
    return render(request, 'organigrama/control_panel.html')


@login_required
@axentra_gate_enforcer(AppIdentifier.ORGANIGRAMA, required_fine_permission="can_manage_infrastructure")
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
@axentra_gate_enforcer(AppIdentifier.ORGANIGRAMA, required_fine_permission="has_access_module")
def estructura_list_view(request):
    """Mesa interactiva principal de la estructura orgánica gubernamental."""
    try:
        dependencias_lista = Dependencia.objects.filter(is_deleted=False).prefetch_related('areas__sede_fisica')
    except Exception:
        dependencias_lista = DependenciaSelectors.listar_activas()

    return render(request, 'organigrama/estructura_list.html', {'dependencias': dependencias_lista})


# =========================================================================
# 🏛️ PILAR 2: GESTIÓN GEOGRÁFICA (SEDES E INMUEBLES MUNICIPALES)
# =========================================================================

@login_required
@axentra_gate_enforcer(AppIdentifier.ORGANIGRAMA, required_fine_permission="can_manage_infrastructure")
def sede_list_view(request):
    """Inventario geográfico físico de palacios y anexos municipales."""
    return render(request, 'organigrama/sede_list.html', {'sedes': SedeSelectors.listar_todas()})


@login_required
@axentra_gate_enforcer(AppIdentifier.ORGANIGRAMA, required_fine_permission="can_manage_infrastructure")
def sede_create_view(request):
    """Aprovisionamiento de nuevos inmuebles institucionales."""
    if request.method == 'POST':
        form = SedeForm(request.POST)
        if form.is_valid():
            exito, sede, errores = OrganigramaService.crear_sede(request, form.cleaned_data)
            if exito: return redirect('organigrama:sede_list')
            form.add_error(None, errores.get('server_error', ['Error de persistencia'])[0])
    else:
        form = SedeForm()
    return render(request, 'organigrama/forms/sede_form.html', {'form': form, 'action': 'create'})


@login_required
@axentra_gate_enforcer(AppIdentifier.ORGANIGRAMA, required_fine_permission="can_manage_infrastructure")
def sede_update_view(request, pk: uuid.UUID):
    """Modificación de metadatos geográficos de un inmueble."""
    sede_instancia = get_object_or_404(Sede, pk=pk)
    if request.method == 'POST':
        form = SedeForm(request.POST, instance=sede_instancia)
        if form.is_valid():
            exito, errores = OrganigramaService.actualizar_sede(request, sede_instancia, form.cleaned_data)
            if exito: return redirect('organigrama:sede_list')
            form.add_error(None, errores.get('server_error', ['Fallo de actualización'])[0])
    else:
        form = SedeForm(instance=sede_instancia)
    return render(request, 'organigrama/forms/sede_form.html', {'form': form, 'action': 'update', 'sede': sede_instancia})


@require_POST
@login_required
@axentra_gate_enforcer(AppIdentifier.ORGANIGRAMA, required_fine_permission="can_manage_infrastructure")
def sede_soft_delete_view(request, pk: uuid.UUID):
    """Baja lógica asíncrona de una sede física mitigando redirecciones de página."""
    sede_instancia = get_object_or_404(Sede, pk=pk)
    OrganigramaService.eliminar_sede(request, sede_instancia)
    
    if request.headers.get('HX-Request'):
        return HttpResponse(status=200, content="")
    return redirect('organigrama:sede_list')


@require_POST
@login_required
@axentra_gate_enforcer(AppIdentifier.ORGANIGRAMA, required_fine_permission="can_manage_infrastructure")
def sede_toggle_status_view(request, pk: uuid.UUID):
    """Alternador AJAX de estatus operativo de Sedes físicas con registro forense manual."""
    sede = get_object_or_404(Sede, pk=pk)
    estado_anterior = sede.is_active
    
    with transaction.atomic():
        sede.is_active = not sede.is_active
        sede.save()
        
    # 🪐 AUDITORÍA MANUAL DE INTERRUPTOR DIRECTO
    ForensicAuditor.registrar_evento(
        request=request,
        action_type=SecurityAuditLog.ActionTypes.UPDATE,
        module_component="SEDES_INFRAESTRUCTURA",
        action_name="TOGGLE_STATUS_SEDE_FISICA",
        target_scope=f"Conmutación del estado operativo para el inmueble {sede.nombre} (Activo final: {sede.is_active}).",
        level=SecurityAuditLog.Levels.INFO,
        search_target=sede.id,
        payload={'anterior': estado_anterior, 'nuevo': sede.is_active}
    )
    
    return render(request, 'common/tags/badge_toggle_activo_inactivo.html', {
        'is_active': sede.is_active,
        'toggle_url': reverse('organigrama:sede_toggle_status', args=[sede.id])
    })


# =========================================================================
# 🏛️ PILAR 3: RAMOS ESTRUCTURALES (DEPENDENCIAS / DIRECCIONES GENERALES)
# =========================================================================

@login_required
@axentra_gate_enforcer(AppIdentifier.ORGANIGRAMA, required_fine_permission="can_mutate_structure")
def dependencia_create_view(request):
    """Modelado e inyección tradicional de dependencias."""
    if request.method == 'POST':
        form = DependenciaForm(request.POST)
        if form.is_valid():
            payload = {
                'nombre': form.cleaned_data['nombre'],
                'encargado_departamento_id': form.cleaned_data['encargado_departamento'].id if form.cleaned_data.get('encargado_departamento') else None
            }
            exito, dep, errores = OrganigramaService.crear_dependencia(request, payload)
            if exito: return redirect('organigrama:estructura_list')
            form.add_error(None, errores.get('server_error', ['Fallo del Servidor'])[0])
    else:
        form = DependenciaForm()
        
    return render(request, 'organigrama/forms/dependencia_form.html', {'form': form, 'action': 'create'})


@login_required
@axentra_gate_enforcer(AppIdentifier.ORGANIGRAMA, required_fine_permission="can_mutate_structure")
def dependencia_update_view(request, pk: uuid.UUID):
    """Modificación de nomenclatura de Direcciones sin choques de unicidad."""
    dep_instancia = get_object_or_404(Dependencia, pk=pk, is_deleted=False)
    
    if request.method == 'POST':
        form = DependenciaForm(request.POST, instance=dep_instancia)
        if form.is_valid():
            payload = {
                'nombre': form.cleaned_data['nombre'],
                'encargado_departamento_id': form.cleaned_data['encargado_departamento'].id if form.cleaned_data.get('encargado_departamento') else None
            }
            exito, errores = OrganigramaService.actualizar_dependencia(request, dep_instancia, payload)
            if exito: return redirect('organigrama:estructura_list')
            form.add_error(None, errores.get('server_error', ['Fallo de actualización'])[0])
    else:
        form = DependenciaForm(instance=dep_instancia)
        
    return render(request, 'organigrama/forms/dependencia_form.html', {
        'form': form, 'action': 'update', 'dependencia': dep_instancia
    })


@require_POST
@login_required
@axentra_gate_enforcer(AppIdentifier.ORGANIGRAMA, required_fine_permission="can_mutate_structure")
def dependencia_soft_delete_view(request, pk: uuid.UUID):
    """Baja lógica asíncrona de una dependencia superior."""
    dep_instancia = get_object_or_404(Dependencia, pk=pk, is_deleted=False)
    OrganigramaService.eliminar_dependencia(request, dep_instancia)
    
    if request.headers.get('HX-Request') or request.headers.get('hx-request'):
        return HttpResponse(status=200, content="")
    return redirect('organigrama:estructura_list')


@require_POST
@login_required
@axentra_gate_enforcer(AppIdentifier.ORGANIGRAMA, required_fine_permission="can_mutate_structure")
def dependencia_toggle_status_view(request, pk):
    """Alternador de estado operativo para dependencias con inyector forense manual."""
    dep_instancia = get_object_or_404(Dependencia, pk=pk, is_deleted=False)
    estado_anterior = dep_instancia.is_active
    
    with transaction.atomic():
        dep_instancia.is_active = not dep_instancia.is_active
        dep_instancia.save()

    ForensicAuditor.registrar_evento(
        request=request,
        action_type=SecurityAuditLog.ActionTypes.UPDATE,
        module_component="DEPENDENCIAS_RAIZ",
        action_name="TOGGLE_STATUS_DEPENDENCIA",
        target_scope=f"Conmutación del estado operativo para la Dirección {dep_instancia.nombre} (Activo final: {dep_instancia.is_active}).",
        level=SecurityAuditLog.Levels.INFO,
        search_target=dep_instancia.id,
        payload={'anterior': estado_anterior, 'nuevo': dep_instancia.is_active}
    )
        
    return render(request, 'common/tags/badge_toggle_activo_inactivo.html', {
        'is_active': dep_instancia.is_active,
        'toggle_url': reverse('organigrama:dependencia_toggle_status', args=[dep_instancia.id])
    })


# =========================================================================
# 📍 PILAR 4: SUB-FRAGMENTACIÓN (ÁREAS OPERATIVAS Y OFICINAS INTERNAS)
# =========================================================================

@login_required
@axentra_gate_enforcer(AppIdentifier.ORGANIGRAMA, required_fine_permission="can_mutate_structure")
def area_create_view(request):
    """Aprovisionamiento de oficinas internas en pantalla completa dedicada."""
    if request.method == 'POST':
        form = AreaOperativaForm(request.POST)
        if form.is_valid():
            payload = {
                'dependencia_id': form.cleaned_data['dependencia'].id,
                'sede_fisica_id': form.cleaned_data['sede_fisica'].id,
                'nombre': form.cleaned_data['nombre']
            }
            exito, area, errores = OrganigramaService.crear_area(request, payload)
            if exito: return redirect('organigrama:estructura_list')
            form.add_error(None, errores.get('server_error', ['Fallo en adscripción'])[0])
    else:
        form = AreaOperativaForm()
        
    return render(request, 'organigrama/forms/area_form.html', {'form': form, 'action': 'create'})


@login_required
@axentra_gate_enforcer(AppIdentifier.ORGANIGRAMA, required_fine_permission="can_mutate_structure")
def area_update_view(request, pk: uuid.UUID):
    """Re-adscripción de palacio físico o cambio nominativo de una sub-oficina."""
    area_instancia = get_object_or_404(AreaOperativa, pk=pk, is_deleted=False)
    if request.method == 'POST':
        form = AreaOperativaForm(request.POST, instance=area_instancia)
        if form.is_valid():
            payload = {
                'dependencia_id': form.cleaned_data['dependencia'].id,
                'sede_fisica_id': form.cleaned_data['sede_fisica'].id,
                'nombre': form.cleaned_data['nombre']
            }
            exito, errores = OrganigramaService.actualizar_area(request, area_instancia, payload)
            if exito: return redirect('organigrama:estructura_list')
            form.add_error(None, errores.get('server_error', ['Fallo de actualización'])[0])
    else:
        form = AreaOperativaForm(instance=area_instancia)
    return render(request, 'organigrama/forms/area_form.html', {'form': form, 'action': 'update', 'area': area_instancia})


@require_POST
@login_required
@axentra_gate_enforcer(AppIdentifier.ORGANIGRAMA, required_fine_permission="can_mutate_structure")
def area_soft_delete_view(request, pk: uuid.UUID):
    """Desvinculación lógica asíncrona de una oficina interna."""
    area_instancia = get_object_or_404(AreaOperativa, pk=pk)
    OrganigramaService.eliminar_area(request, area_instancia)
    return HttpResponse(status=200, content="")


@require_POST
@login_required
@axentra_gate_enforcer(AppIdentifier.ORGANIGRAMA, required_fine_permission="can_mutate_structure")
def area_toggle_status_view(request, pk: uuid.UUID):
    """Invierte el estado operativo (is_active) de una oficina o departamento con inyección forense."""
    area_instancia = get_object_or_404(AreaOperativa, pk=pk, is_deleted=False)
    estado_anterior = area_instancia.is_active
    
    with transaction.atomic():
        area_instancia.is_active = not area_instancia.is_active
        area_instancia.save()
        
    ForensicAuditor.registrar_evento(
        request=request,
        action_type=SecurityAuditLog.ActionTypes.UPDATE,
        module_component="AREAS_MATRIZ",
        action_name="TOGGLE_STATUS_NODO_OPERATIVO",
        target_scope=f"Conmutación del estado operativo para la sub-oficina {area_instancia.nombre} (Activo final: {area_instancia.is_active}).",
        level=SecurityAuditLog.Levels.INFO,
        search_target=area_instancia.id,
        payload={'anterior': estado_anterior, 'nuevo': area_instancia.is_active}
    )
    
    logger.info(f"⚡ AXENTRA OS: Área '{area_instancia.nombre}' mutó a is_active={area_instancia.is_active}")
    
    return render(request, 'common/tags/badge_toggle_activo_inactivo.html', {
        'is_active': area_instancia.is_active,
        'toggle_url': reverse('organigrama:area_toggle_status', args=[area_instancia.id])
    })


# =========================================================================
# ⚡ PILAR 5: TUBERÍAS REACTIVAS ASÍNCRONAS (HTMX PIPELINES)
# =========================================================================

@login_required
@axentra_gate_enforcer(AppIdentifier.ORGANIGRAMA, required_fine_permission="has_access_module")
def cargar_areas_htmx_view(request):
    """Hidratación en cascada de selectores secundarios dependientes."""
    dependencia_id = request.GET.get('dependencia')
    try:
        areas = AreaOperativa.objects.filter(dependencia_id=uuid.UUID(dependencia_id), is_deleted=False)
    except (ValueError, TypeError):
        areas = []
    return render(request, 'organigrama/htmx/area_options.html', {'areas': areas})


@login_required
@axentra_gate_enforcer(AppIdentifier.ORGANIGRAMA, required_fine_permission="has_access_module")
def vincular_areas_ajax_view(request, dep_id):
    """Despacha la matriz de sub-oficinas de una dependencia usando el accesor premium inverso."""
    dependencia = get_object_or_404(Dependencia, id=dep_id, is_deleted=False)
    areas = dependencia.areas.filter(is_deleted=False).select_related('sede_fisica')
    
    return render(request, 'organigrama/estructura_areas_table.html', {
        'dependencia': dependencia,
        'areas': areas,
        'request': request
    })