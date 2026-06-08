# apps/security/views/organigrama_views.py
import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import HttpResponse
from django.template import Template, Context

from apps.shared.apps_config import AppIdentifier
from apps.security.decorators import axentra_gate_enforcer
from apps.security.models.organigrama import Dependencia, AreaOperativa, Sede
from apps.security.selectors import SedeSelectors, DependenciaSelectors, AreaOperativaSelectors
from apps.security.services import OrganigramaService
from apps.security.forms import SedeForm, DependenciaForm, AreaOperativaForm

@login_required
@axentra_gate_enforcer(AppIdentifier.ORGANIGRAMA, required_fine_permission="has_access")
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

@login_required
@axentra_gate_enforcer(AppIdentifier.ORGANIGRAMA, required_fine_permission="can_manage_infrastructure")
def sede_create_view(request):
    """Aprovisionamiento de nuevos inmuebles institucionales."""
    if request.method == 'POST':
        form = SedeForm(request.POST)
        if form.is_valid():
            exito, sede, errores = OrganigramaService.crear_sede(form.cleaned_data)
            if exito: 
                # 🟢 CORREGIDO: Redirección al namespace legítimo
                return redirect('organigrama:sede_list')
            form.add_error(None, errores.get('server_error', ['Error de persistencia'])[0])
    else:
        form = SedeForm()
    return render(request, 'organigrama/forms/sede_form.html', {'form': form})

@login_required
@axentra_gate_enforcer(AppIdentifier.ORGANIGRAMA, required_fine_permission="can_mutate_structure")
def dependencia_create_view(request):
    """Modelado e inyección de Secretarías o Direcciones Generales."""
    if request.method == 'POST':
        form = DependenciaForm(request.POST)
        if form.is_valid():
            payload = {
                'nombre': form.cleaned_data['nombre'],
                'encargado_departamento_id': form.cleaned_data['encargado_departamento'].id if form.cleaned_data.get('encargado_departamento') else None
            }
            exito, dep, errores = OrganigramaService.crear_dependencia(payload)
            if exito: 
                # 🟢 CORREGIDO: Redirección al namespace legítimo
                return redirect('organigrama:estructura_list')
            form.add_error(None, errores.get('server_error', ['Fallo del Servidor'])[0])
    else:
        form = DependenciaForm()
    return render(request, 'organigrama/forms/dependencia_form.html', {'form': form})

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
            if exito: 
                # 🟢 CORREGIDO: Redirección al namespace legítimo
                return redirect('organigrama:estructura_list')
            form.add_error(None, errores.get('server_error', ['Fallo en adscripción'])[0])
    else:
        form = AreaOperativaForm()
    return render(request, 'organigrama/forms/area_form.html', {'form': form})

# =========================================================================
# ⚡ SECCIÓN: COMPONENTES REACTIVOS DE ALTA VELOCIDAD (HTMX TUBERÍAS)
# =========================================================================
@require_POST
@login_required
def sede_toggle_status_view(request, pk: uuid.UUID):
    """Alternador AJAX de estatus operativo con resolución de ruta nativa."""
    if not request.axentra_is_root and "organigrama__can_manage_infrastructure" not in request.axentra_permissions_list:
        return HttpResponse("No autorizado. Firma criptográfica insuficiente.", status=403)
        
    sede = get_object_or_404(Sede, pk=pk)
    sede.is_active = not sede.is_active
    sede.save()
    
    context_data = Context({'sede': sede})
    if sede.is_active:
        # 🟢 CORREGIDO: El hx-post ahora se resuelve dinámicamente con el namespace 'organigrama:'
        template = Template("""
            <button type="button" hx-post="{% url 'organigrama:sede_toggle' sede.id %}" hx-swap="outerHTML" class="inline-flex items-center px-2.5 py-0.5 rounded-full text-[9px] font-bold font-mono bg-gray-50 text-gray-800 border border-gray-200 cursor-pointer uppercase tracking-wider select-none">
                ● OPERATIVO
            </button>
        """)
    else:
        template = Template("""
            <button type="button" hx-post="{% url 'organigrama:sede_toggle' sede.id %}" hx-swap="outerHTML" class="inline-flex items-center px-2.5 py-0.5 rounded-full text-[9px] font-bold font-mono bg-gray-950 text-gray-400 border border-transparent cursor-pointer uppercase tracking-wider select-none animate-pulse">
                ○ INACTIVO
            </button>
        """)
    return HttpResponse(template.render(context_data))

@login_required
def cargar_areas_htmx_view(request):
    """Hidratación en cascada de selectores secundarios dependientes."""
    dependencia_id = request.GET.get('dependencia')
    try:
        areas = AreaOperativaSelectors.listar_por_dependencia(uuid.UUID(dependencia_id)) if dependencia_id and dependencia_id != 'all' else []
    except (ValueError, TypeError):
        areas = []
    # 🟢 PATRÓN CORREGIDO: Carpeta htmx/ en lugar de partials/
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
    # 🟢 PATRÓN CORREGIDO: Carpeta htmx/ en lugar de partials/
    return render(request, 'organigrama/htmx/estructura_areas_table.html', context)