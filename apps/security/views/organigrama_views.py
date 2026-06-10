# apps/security/views/organigrama_views.py
import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import HttpResponse, HttpResponseForbidden
from django.template import Template, Context
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.db import transaction

from apps.shared.apps_config import AppIdentifier
from apps.security.decorators import axentra_gate_enforcer

# Modelos Reales del Ecosistema
from apps.security.models.organigrama import Sede, Dependencia, AreaOperativa
from apps.security.models.audit import SecurityAuditLog  # 🟢 Tu modelo real de auditoría

# Selectores, Services y Formularios Reales
from apps.security.selectors.organigrama_selectors import SedeSelectors, DependenciaSelectors, AreaOperativaSelectors
from apps.security.services.organigrama_services import OrganigramaService
from apps.security.forms import SedeForm, DependenciaForm, AreaOperativaForm

User = get_user_model()

# =========================================================================
# 📊 CONTROLADORES DE CUADRO DE MANDO Y REJILLAS PRINCIPALES
# =========================================================================

@login_required
@axentra_gate_enforcer(AppIdentifier.ORGANIGRAMA, required_fine_permission="has_access_module")
def organigrama_control_view(request):
    """Cuarto de Control General: Enrutador táctico de alta velocidad sin carga analítica."""
    # 🟢 CERO QUERIES PESADAS: Solo renderiza el chasis de navegación segura
    return render(request, 'organigrama/control_panel.html')


@login_required
# 🟢 BLINDAJE: Ahora requiere permisos de auditoría o administración para ver la analítica
@axentra_gate_enforcer(AppIdentifier.ORGANIGRAMA, required_fine_permission="can_manage_infrastructure")
def organigrama_dashboard_view(request):
    """Cabina de mando analítica: Reservada para alta gerencia y auditoría forense."""
    total_sedes = Sede.objects.filter(is_active=True, is_deleted=False).count()
    total_dependencias = Dependencia.objects.filter(is_active=True, is_deleted=False).count()
    total_areas = AreaOperativa.objects.filter(is_active=True, is_deleted=False).count()
    
    funcionarios_sin_area = User.objects.filter(
        is_active=True, axentra_profile__area__isnull=True
    ).count() if hasattr(User, 'axentra_profile') else 0

    logs_reales = SecurityAuditLog.objects.filter(
        target_scope__icontains='organigrama'
    ).order_by('-created_at')[:5]

    context = {
        'total_sedes': total_sedes,
        'total_dependencias': total_dependencias,
        'total_areas': total_areas,
        'funcionarios_sin_area': funcionarios_sin_area,
        'cronologia_mutaciones': logs_reales, 
    }
    return render(request, 'organigrama/dashboard/organigrama_dashboard.html', context)

@login_required
@axentra_gate_enforcer(AppIdentifier.ORGANIGRAMA, required_fine_permission="has_access_module")
def estructura_list_view(request):
    """Mesa interactiva de dependencias gubernamentales."""
    return render(request, 'organigrama/estructura_list.html', {
        'dependencias': DependenciaSelectors.listar_activas()
    })

@login_required
@axentra_gate_enforcer(AppIdentifier.ORGANIGRAMA, required_fine_permission="can_manage_infrastructure")
def sede_list_view(request):
    """Inventario geográfico físico de palacios y anexos municipales."""
    return render(request, 'organigrama/sede_list.html', {
        'sedes': SedeSelectors.listar_todas()
    })

# =========================================================================
# 🏗️ TRANSMUTACIONES DE SEDES (INMUEBLES MUNICIPALES)
# =========================================================================

@login_required
@axentra_gate_enforcer(AppIdentifier.ORGANIGRAMA, required_fine_permission="can_manage_infrastructure")
def sede_create_view(request):
    """Aprovisionamiento de nuevos inmuebles institucionales."""
    if request.method == 'POST':
        form = SedeForm(request.POST)
        if form.is_valid():
            exito, sede, errores = OrganigramaService.crear_sede(form.cleaned_data)
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
            exito, errores = OrganigramaService.actualizar_sede(sede_instancia, form.cleaned_data)
            if exito: return redirect('organigrama:sede_list')
            form.add_error(None, errores.get('server_error', ['Fallo de actualización'])[0])
    else:
        form = SedeForm(instance=sede_instancia)
    return render(request, 'organigrama/forms/sede_form.html', {'form': form, 'action': 'update', 'sede': sede_instancia})

@require_POST  # 🟢 BLINDAJE: Rechaza peticiones GET de bots o URLs manuales en el navegador
@login_required
@axentra_gate_enforcer(AppIdentifier.ORGANIGRAMA, required_fine_permission="can_manage_infrastructure")
def sede_soft_delete_view(request, pk: uuid.UUID):
    """Baja lógica asíncrona de una sede física mitigando redirecciones de página."""
    sede_instancia = get_object_or_404(Sede, pk=pk)
    
    # Ejecutamos la desactivación en cascada en la base de datos
    OrganigramaService.eliminar_sede(sede_instancia)
    
    # 🚀 RESPUESTA REACTIVA: Si la petición viene de HTMX, devolvemos un string vacío
    # con estatus 200. HTMX se encargará de borrar la tarjeta del DOM de inmediato.
    if request.headers.get('HX-Request'):
        return HttpResponse(
            status=200, 
            content=""
        )
        
    # Fallback por si se dispara desde un formulario tradicional
    return redirect('organigrama:sede_list')

# =========================================================================
# 📁 TRANSMUTACIONES DE DEPENDENCIAS (SECRETARÍAS Y DIRECCIONES)
# =========================================================================

@login_required
@axentra_gate_enforcer(AppIdentifier.ORGANIGRAMA, required_fine_permission="can_mutate_structure")
def dependencia_create_view(request):
    """Modelado e inyección tradicional en pantalla completa."""
    if request.method == 'POST':
        form = DependenciaForm(request.POST)
        if form.is_valid():
            payload = {
                'nombre': form.cleaned_data['nombre'],
                'encargado_departamento_id': form.cleaned_data['encargado_departamento'].id if form.cleaned_data.get('encargado_departamento') else None
            }
            exito, dep, errores = OrganigramaService.crear_dependencia(payload)
            if exito: 
                return redirect('organigrama:estructura_list')
            form.add_error(None, errores.get('server_error', ['Fallo del Servidor'])[0])
    else:
        form = DependenciaForm()
        
    return render(request, 'organigrama/forms/dependencia_form.html', {
        'form': form, 
        'action': 'create'
    })


@login_required
@axentra_gate_enforcer(AppIdentifier.ORGANIGRAMA, required_fine_permission="can_mutate_structure")
def dependencia_update_view(request, pk: uuid.UUID):
    """Modificación de nomenclatura en pantalla completa sin choques de unicidad."""
    # Obtenemos el registro que se pretende modificar
    dep_instancia = get_object_or_404(Dependencia, pk=pk, is_deleted=False)
    
    if request.method == 'POST':
        # 🟢 CORRECCIÓN DE UNICIDAD: Le pasamos la instance=dep_instancia en el POST.
        # Esto le permite a Django ignorar el error de "ya existe este nombre" para sí mismo.
        form = DependenciaForm(request.POST, instance=dep_instancia)
        
        if form.is_valid():
            payload = {
                'nombre': form.cleaned_data['nombre'],
                'encargado_departamento_id': form.cleaned_data['encargado_departamento'].id if form.cleaned_data.get('encargado_departamento') else None
            }
            
            # Forzamos que la actualización corra estrictamente a través de tu Service Layer
            exito, errores = OrganigramaService.actualizar_dependencia(dep_instancia, payload)
            if exito: 
                return redirect('organigrama:estructura_list')
                
            form.add_error(None, errores.get('server_error', ['Fallo de actualización'])[0])
    else:
        # Carga inicial (GET) idéntica
        form = DependenciaForm(instance=dep_instancia)
        
    return render(request, 'organigrama/forms/dependencia_form.html', {
        'form': form, 
        'action': 'update', 
        'dependencia': dep_instancia
    })
    

@require_POST
@login_required
@axentra_gate_enforcer(AppIdentifier.ORGANIGRAMA, required_fine_permission="can_mutate_structure")
def dependencia_soft_delete_view(request, pk: uuid.UUID):
    """Baja lógica asíncrona de una dependencia mitigando redirecciones de página."""
    dep_instancia = get_object_or_404(Dependencia, pk=pk, is_deleted=False)
    
    # Ejecutamos la baja en cascada
    OrganigramaService.eliminar_dependencia(dep_instancia)
    
    # 🚀 RESPUESTA REACTIVA: HTMX remueve la tarjeta del DOM instantáneamente
    if request.headers.get('HX-Request') or request.headers.get('hx-request'):
        return HttpResponse(status=200, content="")
        
    return redirect('organigrama:estructura_list')


@require_POST
@login_required
@axentra_gate_enforcer(AppIdentifier.ORGANIGRAMA, required_fine_permission="can_mutate_structure")
def dependencia_toggle_status_view(request, pk):
    """Invierte el estado operativo e inyecta de vuelta el mismo badge toggle."""
    dep_instancia = get_object_or_404(Dependencia, pk=pk, is_deleted=False)
    
    with transaction.atomic():
        dep_instancia.is_active = not dep_instancia.is_active
        dep_instancia.save()
        
    return render(request, 'common/tags/badge_toggle_activo_inactivo.html', {
        'is_active': dep_instancia.is_active,
        'toggle_url': reverse('organigrama:dependencia_toggle_status', args=[dep_instancia.id])
    })

# =========================================================================
# 📍 TRANSMUTACIONES DE ÁREAS OPERATIVAS (DEPARTAMENTOS / OFICINAS)
# =========================================================================

@login_required
@axentra_gate_enforcer(AppIdentifier.ORGANIGRAMA, required_fine_permission="can_mutate_structure")
def area_create_view(request):
    """Sub-fragmentación operativa de oficinas internas."""
    if request.method == 'POST':
        form = AreaOperativaForm(request.POST)
        if form.is_valid():
            payload = {
                'dependencia_id': form.cleaned_data['dependencia'].id,
                'sede_fisica_id': form.cleaned_data['sede_fisica'].id,
                'nombre': form.cleaned_data['nombre']
            }
            exito, area, errores = OrganigramaService.crear_area(payload)
            if exito: return redirect('organigrama:estructura_list')
            form.add_error(None, errores.get('server_error', ['Fallo en adscripción'])[0])
    else:
        form = AreaOperativaForm()
    return render(request, 'organigrama/forms/area_form.html', {'form': form, 'action': 'create'})

@login_required
@axentra_gate_enforcer(AppIdentifier.ORGANIGRAMA, required_fine_permission="can_mutate_structure")
def area_update_view(request, pk: uuid.UUID):
    """Re-adscripción de palacio físico o cambio de nombre de una sub-oficina."""
    area_instancia = get_object_or_404(AreaOperativa, pk=pk, is_deleted=False)
    if request.method == 'POST':
        form = AreaOperativaForm(request.POST, instance=area_instancia)
        if form.is_valid():
            payload = {
                'dependencia_id': form.cleaned_data['dependencia'].id,
                'sede_fisica_id': form.cleaned_data['sede_fisica'].id,
                'nombre': form.cleaned_data['nombre']
            }
            exito, errores = OrganigramaService.actualizar_area(area_instancia, payload)
            if exito: return redirect('organigrama:estructura_list')
            form.add_error(None, errores.get('server_error', ['Fallo de actualización'])[0])
    else:
        form = AreaOperativaForm(instance=area_instancia)
    return render(request, 'organigrama/forms/area_form.html', {'form': form, 'action': 'update', 'area': area_instancia})

@login_required
@axentra_gate_enforcer(AppIdentifier.ORGANIGRAMA, required_fine_permission="can_mutate_structure")
def area_soft_delete_view(request, pk: uuid.UUID):
    """Desvinculación lógica de una oficina interna del Ayuntamiento."""
    area_instancia = get_object_or_404(AreaOperativa, pk=pk)
    OrganigramaService.eliminar_area(area_instancia)
    return redirect('organigrama:estructura_list')

# =========================================================================
# ⚡ SECCIÓN: COMPONENTES REACTIVOS DE ALTA VELOCIDAD (HTMX TUBERÍAS)
# =========================================================================

@require_POST
@login_required
@axentra_gate_enforcer(AppIdentifier.ORGANIGRAMA, required_fine_permission="can_manage_infrastructure")
def sede_toggle_status_view(request, pk: uuid.UUID):
    """Alternador AJAX de estatus operativo unificado con seguridad perimetral."""
    
    # 🟢 REMOCIÓN CRÍTICA: Eliminamos el 'if' manual que causaba el AttributeError.
    # El decorador '@axentra_gate_enforcer' ya validó si el mánager tiene 'can_manage_infrastructure'.
    
    sede = get_object_or_404(Sede, pk=pk)
    sede.is_active = not sede.is_active
    sede.save()
    
    # Renderizamos el componente usando el nuevo inclusion_tag limpio
    return render(request, 'common/tags/badge_toggle_activo_inactivo.html', {
        'is_active': sede.is_active,
        'toggle_url': reverse('organigrama:sede_toggle_status', args=[sede.id])
    })

@login_required
def cargar_areas_htmx_view(request):
    """Hidratación en cascada de selectores secundarios dependientes."""
    dependencia_id = request.GET.get('dependencia')
    try:
        areas = AreaOperativaSelectors.listar_por_dependencia(uuid.UUID(dependencia_id)) if dependencia_id and dependencia_id != 'all' else []
    except (ValueError, TypeError):
        areas = []
    return render(request, 'organigrama/htmx/area_options.html', {'areas': areas})

@login_required
def vincular_areas_ajax_view(request, dep_id: uuid.UUID):
    """Inyección reactiva de la rejilla de oficinas en la mesa unificada."""
    dependencia_dto = DependenciaSelectors.obtener_por_id(dep_id)
    areas_dtos = list(AreaOperativaSelectors.listar_por_dependencia(dep_id))
    
    context = {
        'dependencia': dependencia_dto,
        'areas': areas_dtos,
        'total_areas': len(areas_dtos),
    }
    return render(request, 'organigrama/htmx/estructura_areas_table.html', context)