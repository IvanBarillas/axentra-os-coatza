# apps/security/views/organigrama_views.py
import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import HttpResponse

from apps.shared.apps_config import AppIdentifier
from apps.security.decorators import axentra_gate_enforcer
from apps.security.models import Sede, Dependencia, AreaOperativa
from apps.security.selectors import SedeSelectors, DependenciaSelectors, AreaOperativaSelectors
from apps.security.services import OrganigramaService
from apps.security.forms import SedeForm, DependenciaForm, AreaOperativaForm

@login_required
@axentra_gate_enforcer(AppIdentifier.SECURITY, required_fine_permission="has_access_module")
def estructura_list_view(request):
    """Mesa interactiva de dependencias gubernamentales."""
    return render(request, 'organigrama/estructura_list.html', {
        'dependencias': DependenciaSelectors.listar_activas()
    })

@login_required
@axentra_gate_enforcer(AppIdentifier.SECURITY, required_fine_permission="can_manage_infrastructure")
def sede_list_view(request):
    """Inventario geográfico físico de palacios y anexos municipales."""
    return render(request, 'organigrama/sede_list.html', {
        'sedes': SedeSelectors.listar_todas()
    })

@login_required
@axentra_gate_enforcer(AppIdentifier.SECURITY, required_fine_permission="can_manage_infrastructure")
def sede_create_view(request):
    if request.method == 'POST':
        form = SedeForm(request.POST)
        if form.is_valid():
            exito, sede, errores = OrganigramaService.crear_sede(form.cleaned_data)
            if exito: return redirect('security:sede_list')
            form.add_error(None, errores.get('server_error', ['Error de persistencia'])[0])
    else:
        form = SedeForm()
    return render(request, 'organigrama/forms/sede_form.html', {'form': form})

@login_required
@axentra_gate_enforcer(AppIdentifier.SECURITY, required_fine_permission="can_mutate_structure")
def dependencia_create_view(request):
    if request.method == 'POST':
        form = DependenciaForm(request.POST)
        if form.is_valid():
            payload = {
                'nombre': form.cleaned_data['nombre'],
                'encargado_departamento_id': form.cleaned_data['encargado_departamento'].id if form.cleaned_data.get('encargado_departamento') else None
            }
            exito, dep, errores = OrganigramaService.crear_dependencia(payload)
            if exito: return redirect('security:estructura_list')
            form.add_error(None, errores.get('server_error', ['Fallo del Servidor'])[0])
    else:
        form = DependenciaForm()
    return render(request, 'organigrama/forms/dependencia_form.html', {'form': form})

@login_required
@axentra_gate_enforcer(AppIdentifier.SECURITY, required_fine_permission="can_mutate_structure")
def area_create_view(request):
    if request.method == 'POST':
        form = AreaOperativaForm(request.POST)
        if form.is_valid():
            payload = {
                'dependencia_id': form.cleaned_data['dependencia'].id,
                'sede_fisica_id': form.cleaned_data['sede_fisica'].id,
                'nombre': form.cleaned_data['nombre']
            }
            exito, area, errores = OrganigramaService.crear_area(payload)
            if exito: return redirect('security:estructura_list')
            form.add_error(None, errores.get('server_error', ['Fallo en adscripción'])[0])
    else:
        form = AreaOperativaForm()
    return render(request, 'organigrama/forms/area_form.html', {'form': form})

# =========================================================================
# ⚡ SECCIÓN: COMPONENTES REACTIVOS DE ALTA VELOCIDAD (HTMX TUBERÍAS)
# =========================================================================
@login_required
def sede_toggle_status_view(request, pk: uuid.UUID):
    """Alternador AJAX de estatus operativo (OuterHTML swapping)."""
    if not request.user.axentra_profile.is_root_admin and not request.axentra_permissions.get('can_manage_infrastructure'):
        return HttpResponse("No autorizado", status=403)
        
    sede = get_object_or_404(Sede, pk=pk)
    sede.is_active = not sede.is_active
    sede.save()
    
    if list_state := sede.is_active:
        return HttpResponse(f'<button type="button" hx-post="/security/sedes/{sede.id}/toggle/" hx-swap="outerHTML" class="inline-flex items-center px-2.5 py-0.5 rounded-full text-[9px] font-black bg-emerald-50 text-emerald-700 border border-emerald-100 cursor-pointer">● OPERATIVO</button>')
    return HttpResponse(f'<button type="button" hx-post="/security/sedes/{sede.id}/toggle/" hx-swap="outerHTML" class="inline-flex items-center px-2.5 py-0.5 rounded-full text-[9px] font-black bg-amber-50 text-amber-600 border border-amber-200 cursor-pointer">⚠️ INACTIVO</button>')

@login_required
def cargar_areas_htmx_view(request):
    """Hidratación en cascada de selectores secundarios dependientes."""
    dependencia_id = request.GET.get('dependencia')
    areas = AreaOperativaSelectors.listar_por_dependencia(uuid.UUID(dependencia_id)) if dependencia_id and dependencia_id != 'all' else []
    return render(request, 'organigrama/partials/area_options.html', {'areas': areas})

@login_required
def vincular_areas_ajax_view(request, dep_id: uuid.UUID):
    """Inyección reactiva de la rejilla de oficinas en la mesa unificada."""
    dependencia_dto = DependenciaSelectors.obtener_por_id(dep_id)
    areas_dtos = list(AreaOperativaSelectors.listar_por_dependencia(dep_id))
    
    context = {
        'dependencia': dependencia_dto,
        'areas': areas_dtos,
        'total_areas': len(areas_dtos),
        'permisos': request.axentra_permissions
    }
    return render(request, 'organigrama/partials/estructura_areas_table.html', context)