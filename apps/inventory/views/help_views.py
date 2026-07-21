"""Centro de ayuda funcional de Inventory, escrito para usuarios finales."""

from django.http import Http404

from apps.security.decorators import axentra_gate_enforcer
from apps.shared.apps_config import AppIdentifier

from .common import render_inventory


WORKFLOWS = {
    "alta": {
        "title": "Registrar un bien",
        "summary": "Desde la solicitud hasta el folio oficial.",
        "icon": "clipboard-plus",
        "steps": (
            ("Captura", "Adquisiciones o Patrimonio registra los datos y evidencias."),
            ("Aceptación", "El titular de la dependencia confirma que recibirá el bien."),
            ("Validación", "Control Patrimonial revisa clasificación, cuenta y documentos."),
            ("Registro", "El sistema genera el folio oficial y abre el expediente."),
        ),
        "important": "Un borrador o solicitud no es todavía un activo oficialmente inventariado.",
    },
    "resguardo": {
        "title": "Asignar un resguardo",
        "summary": "Responsabilidad permanente sobre un bien.",
        "icon": "file-signature",
        "steps": (
            ("Preparación", "Patrimonio selecciona sede, dependencia, área y resguardatario."),
            ("Autorización", "El titular de la dependencia autoriza la asignación."),
            ("Entrega", "Patrimonio registra la entrega física."),
            ("Aceptación", "El servidor público acepta y firma el resguardo."),
        ),
        "important": "El titular autoriza; el resguardatario es quien responde directamente por el bien.",
    },
    "prestamo": {
        "title": "Prestar o recibir un bien",
        "summary": "Custodia temporal sin cambiar la propiedad administrativa.",
        "icon": "handshake",
        "steps": (
            ("Entrega propuesta", "La dependencia propietaria elige el bien y la dependencia receptora."),
            ("Aceptación receptora", "La dependencia receptora define área y responsable."),
            ("Autorización", "Patrimonio valida y autoriza la salida temporal."),
            ("Entrega", "Se registra condición, fecha límite y evidencia."),
            ("Devolución", "Se comprueba la condición y se cierra el préstamo."),
        ),
        "important": "El bien continúa contado dentro de la dependencia propietaria durante todo el préstamo.",
    },
    "movimiento": {
        "title": "Mover o reasignar un bien",
        "summary": "Cambio formal de ubicación, área o adscripción.",
        "icon": "arrow-left-right",
        "steps": (
            ("Solicitud", "Se indica el origen, destino y motivo del cambio."),
            ("Autorización", "Las autoridades correspondientes revisan el movimiento."),
            ("Entrega", "Se documenta la salida de la ubicación anterior."),
            ("Recepción", "El destino recibe el bien y se actualiza su expediente."),
        ),
        "important": "A diferencia del préstamo, una transferencia sí puede cambiar la adscripción permanente.",
    },
    "baja": {
        "title": "Dar de baja un bien",
        "summary": "Desincorporación con evidencia obligatoria.",
        "icon": "archive-x",
        "steps": (
            ("Solicitud", "Se registra motivo y justificación."),
            ("Evidencias", "Se carga denuncia, dictamen o acta según el tipo de baja."),
            ("Aprobación", "Las autoridades revisan y autorizan el expediente."),
            ("Ejecución", "Patrimonio cambia el estado sólo después de la autorización."),
        ),
        "important": "Presionar un botón nunca es suficiente para dar de baja patrimonio municipal.",
    },
    "auditoria": {
        "title": "Realizar una auditoría física",
        "summary": "Comprobar ubicación, responsable y condición.",
        "icon": "scan-line",
        "steps": (
            ("Apertura", "Se define periodo y alcance del levantamiento."),
            ("Congelamiento", "Se conserva una fotografía del inventario esperado."),
            ("Lectura", "Los auditores escanean y documentan los bienes encontrados."),
            ("Conciliación", "Se atienden diferencias y bienes no localizados."),
            ("Cierre", "Se emite el resultado final del periodo."),
        ),
        "important": "Los hallazgos no modifican silenciosamente el inventario; generan acciones auditables.",
    },
    "documentos": {
        "title": "Agregar documentos y fotografías",
        "summary": "Evidencia del expediente patrimonial.",
        "icon": "folder-check",
        "steps": (
            ("Seleccionar expediente", "Abra el bien, préstamo, resguardo o baja correspondiente."),
            ("Cargar", "Indique tipo, descripción y archivo o fotografía."),
            ("Validar", "Un usuario autorizado revisa la evidencia cuando sea obligatorio."),
            ("Conservar", "El archivo queda relacionado con el evento que le dio origen."),
        ),
        "important": "Las fotos de entrega y devolución pertenecen al préstamo; las generales pertenecen al activo.",
    },
    "finanzas": {
        "title": "Depreciación y conciliación",
        "summary": "Control contable y exportación a SIGMAVER.",
        "icon": "landmark",
        "steps": (
            ("Clasificar", "Cada bien se relaciona con su cuenta CONAC."),
            ("Calcular", "Se ejecuta la depreciación según la política vigente."),
            ("Conciliar", "Se compara inventario físico contra balanza contable."),
            ("Exportar", "Se generan reportes y archivos del periodo."),
        ),
        "important": "Una diferencia de centavos debe revisarse antes del cierre contable.",
    },
}


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="has_access_module")
def inventory_help_view(request):
    return render_inventory(request, page="inventory/pages/help.html", content="inventory/content/help_content.html", context={"current_inventory_view": "inventory:help", "workflows": WORKFLOWS})


@axentra_gate_enforcer(AppIdentifier.INVENTORY, required_fine_permission="has_access_module")
def inventory_help_detail_view(request, workflow_code):
    workflow = WORKFLOWS.get(workflow_code)
    if not workflow:
        raise Http404
    return render_inventory(request, page="inventory/pages/help_detail.html", content="inventory/content/help_detail_content.html", context={"current_inventory_view": "inventory:help", "workflow": workflow, "workflow_code": workflow_code})
