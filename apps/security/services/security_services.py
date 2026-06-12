# apps/security/services/security_services.py
import json
import logging
import sys
import traceback
from typing import List, Dict, Any, Optional, Tuple

# Librerías de Terceros
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

# Infraestructura Django Core
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone


# Modelos y Componentes del Negocio Axentra OS
from apps.security.models import UserAppRole, AppModule
from apps.security.models.audit import SecurityAuditLog
from apps.security.services.permission_loader import get_app_permissions
from apps.security.utils.forensic_auditor import ForensicAuditor
from apps.security.utils.hierarchy_enforcer import HierarchyEnforcer

User = get_user_model()
logger = logging.getLogger(__name__)


class PermissionService:
    """Lógica transaccional centralizada para la inyección, mutación y auditoría de privilegios."""

    @staticmethod
    def authorize_new_user_entry(request, app_module: AppModule, user_id: str, rol_a_inyectar: str = 'viewer') -> bool:
        """
        Incorpora un funcionario al padrón de una aplicación bajo la filosofía Zero Trust.
        🛰️ AUDITORÍA NORMALIZADA: Registra el evento bajo el tipo CREATE en el componente MATRIZ_PERMISOS.
        """
        try:
            target_user = User.objects.get(id=user_id)
            if target_user.is_manager or target_user.is_superuser:
                return False
                
            rol_limpio = str(rol_a_inyectar).lower().strip()

            with transaction.atomic():
                rol_existente = UserAppRole.objects.filter(user=target_user, app=app_module).first()
                if rol_existente and rol_existente.is_active:
                    return False

                if rol_limpio == "owner":
                    config_app = get_app_permissions(app_module.slug)
                    llaves_finales = list(config_app.get('permissions', {}).keys())
                else:
                    llaves_finales = ['has_access_module']

                UserAppRole.objects.update_or_create(
                    user=target_user,
                    app=app_module,
                    defaults={
                        'role': rol_limpio,
                        'permissions_list': llaves_finales,
                        'is_active': True
                    }
                )

            # 🪐 BITÁCORA FORENSE ATÓMICA DE INYECCIÓN
            ForensicAuditor.registrar_evento(
                request=request,
                action_type=SecurityAuditLog.ActionTypes.CREATE,
                module_component="MATRIZ_PERMISOS",
                action_name="INYECCION_PERIMETRAL_FUNCIONARIO",
                target_scope=f"Siembra inicial del funcionario {target_user.email} en {app_module.name} con rol [{rol_limpio.upper()}].",
                level=SecurityAuditLog.Levels.SUCCESS,
                target_user=target_user,
                search_target=target_user.id,
                payload={'initial_role': rol_limpio, 'app_slug': app_module.slug}
            )

            logger.info(f"🟢 CIBERSEGURIDAD: Funcionario {target_user.email} sembrado en [{app_module.slug.upper()}].")
            return True
        except Exception as e:
            logger.error(f"❌ FALLO (authorize_new_user_entry): {str(e)}")
            return False

    @staticmethod
    def save_matrix_permissions(request, target_user: Any, app_module: AppModule, nuevo_rol: str, llaves_encendidas: List[str], is_manager_bypass: bool = False) -> Tuple[bool, str]:
        """
        🚀 REFACTOR MASTER CENTRALIZADO BLINDADO: Sanea, valida jerarquía, calcula deltas y guarda.
        🛡️ ENFOQUE ZERO-TRUST ESTRICTO: Solo 'owner' hereda todos los permisos. ADMIN nace en ceros.
        🛰️ COMPILACIÓN FORENSE AUTÓNOMA: El servicio calcula el delta de forma nativa para blindar el payload_json.
        """
        try:
            rol_limpio = str(nuevo_rol).lower().strip()
            
            # 🪐 SNAPSHOT ANTES: Capturamos el estado actual real de la BD antes de alterarlo
            rol_actual_obj = UserAppRole.objects.filter(user=target_user, app=app_module).first()
            rol_anterior = rol_actual_obj.role if rol_actual_obj else 'ninguno'
            permisos_anteriores = list(rol_actual_obj.permissions_list or []) if rol_actual_obj else []

            # 🛡️ VALIDACIÓN DE ESCALAFÓN DE JERARQUÍA
            config_app = get_app_permissions(app_module.slug)
            weights_map = config_app.get('weights', {})
            permissions_pool = config_app.get('permissions', {})

            tiene_autoridad = HierarchyEnforcer.validar_autoridad_operador(
                request=request, target_user=target_user, app_module=app_module,
                nuevo_rol_slug=rol_limpio, weights_map=weights_map
            )
            if not tiene_autoridad:
                return False, "🚫 Violación de Escalafón: Tus privilegios locales no tienen el peso jerárquico requerido."

            # Saneamiento y filtrado de llaves inyectadas desde el POST contra el manifiesto
            lista_final_json = list(set([str(llave).strip() for llave in llaves_encendidas if llave]))
            if permissions_pool:
                lista_final_json = [l for l in lista_final_json if l in permissions_pool.keys()]

            # Regla de control Zero-Trust: Solo Owner clona la piscina completa
            if rol_limpio == 'owner' and permissions_pool:
                lista_final_json = list(permissions_pool.keys())
            
            # El token mínimo de entrada se amarra por diseño defensivo
            if 'has_access_module' not in lista_final_json:
                lista_final_json.append('has_access_module')

            # 🪐 ANÁLISIS FORENSE DELTA: Calculamos tokens ganados y perdidos de manera autónoma
            payload_delta = {
                'antes': {'role': rol_anterior, 'permissions': permisos_anteriores},
                'despues': {'role': rol_limpio, 'permissions': lista_final_json},
                'delta_cambios': {
                    'tokens_ganados': [p for p in lista_final_json if p not in permisos_anteriores],
                    'tokens_perdidos': [p for p in permisos_anteriores if p not in lista_final_json],
                    'rol_mutado': rol_anterior != rol_limpio
                }
            }

            # Persistencia física atómica en PostgreSQL
            with transaction.atomic():
                UserAppRole.objects.update_or_create(
                    user=target_user, app=app_module,
                    defaults={'role': rol_limpio, 'permissions_list': lista_final_json, 'is_active': True}
                )

            # 🪐 INYECTOR FORENSE CENTRALIZADO CON EL PAYLOAD COMPLETO
            action_code = "MUTACION_MATRIZ_BYPASS" if is_manager_bypass else "MUTACION_MATRIZ_ESTANDAR"
            level_status = SecurityAuditLog.Levels.SUCCESS if is_manager_bypass else SecurityAuditLog.Levels.INFO
            
            ForensicAuditor.registrar_evento(
                request=request,
                action_type=SecurityAuditLog.ActionTypes.ASSIGN,     # 🔤 Verbo Normalizado
                module_component="MATRIZ_PERMISOS",                  # 🗺️ Componente Local
                action_name=action_code,
                target_scope=f"Reconfiguración granular sobre la grilla de {target_user.email} en el módulo de {app_module.name}",
                level=level_status,
                target_user=target_user,
                search_target=target_user.id,
                payload=payload_delta                                # ◄── Guardado impecable en Postgres
            )

            msg = f"🔒 [NIVEL MAESTRO]: Reconfiguración por decreto completada." if is_manager_bypass else f"🔒 Matriz actualizada con éxito."
            return True, msg

        except Exception as e:
            logger.error(f"❌ FALLO TRANSACCIONAL (save_matrix_permissions): {str(e)}\n{traceback.format_exc()}")
            return False, f"Fallo interno de consistencia: {str(e)}"
        
        
    @staticmethod
    def exportar_auditoria_excel(filtros: dict) -> HttpResponse:
        """
        🚀 EXTRACTOR FORENSE ATÓMICO: Genera un reporte inmutable en Excel (.xlsx)
        respetando exactamente los filtros y agregando la carga útil (JSON Payload).
        """
        try:
            import json  # Inyección segura si no está arriba
            
            # 1. Replicamos la lógica exacta de filtrado cronológico/táctico del Selector
            query = Q()
            if filtros.get('fecha_inicio') or filtros.get('fecha_fin'):
                if filtros.get('fecha_inicio'):
                    query &= Q(created_at__date__gte=filtros['fecha_inicio'])
                if filtros.get('fecha_fin'):
                    query &= Q(created_at__date__lte=filtros['fecha_fin'])
            else:
                # Si no hay fechas, por seguridad el Excel descarga el ciclo del día de hoy
                query &= Q(created_at__date=timezone.now().date())

            if filtros.get('app_namespace'):
                query &= Q(app_namespace=filtros['app_namespace'])
            if filtros.get('action_type'):
                query &= Q(action_type=filtros['action_type'])
            if filtros.get('level_status'):
                query &= Q(level_status=filtros['level_status'])
            if filtros.get('search_target'):
                query &= Q(search_target__icontains=filtros['search_target'])
            if filtros.get('operador'):
                query &= Q(operator_user__email__icontains=filtros['operador'])

            # Traemos el QuerySet completo sin límites de paginación
            logs = SecurityAuditLog.objects.filter(query).select_related('operator_user', 'target_user').order_by('-created_at')

            # 2. Inicializamos el libro de OpenPyXL en memoria RAM
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "AXENTRA FORENSIC AUDIT"
            ws.views.sheetView[0].showGridLines = True

            # Estilos de diseño corporativo (Cabecera Azul Oscuro Táctico)
            font_titulo = Font(name="Arial", size=11, bold=True, color="FFFFFF")
            fill_titulo = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
            align_centro = Alignment(horizontal="center", vertical="center", wrap_text=False)

            # 🟢 ENCABEZADOS: Agregamos la columna final para el JSON
            headers = [
                "IDPaquete (UUID)", "Fecha / Hora (UTC)", "Criticidad", 
                "Ecosistema / App", "Verbo (Action)", "Componente / Vista", 
                "Operador (Email)", "Objetivo (Email)", "Descripción de Acción", 
                "Criterio de Negocio (Target)", "Firma de Red (IP)", "Dispositivo / User-Agent",
                "Evidencia Técnica (JSON Payload)" # ◄── NUEVA COLUMNA FORENSE
            ]
            ws.append(headers)

            # Aplicamos los estilos a la fila de la cabecera
            for col_num, header in enumerate(headers, 1):
                cell = ws.cell(row=1, column=col_num)
                cell.font = font_titulo
                cell.fill = fill_titulo
                cell.alignment = align_centro

            # 3. Inyectamos los registros de la base de datos
            for log in logs:
                # Saneamos el JSON: Si por alguna razón está vacío o es un string malformado, devolvemos un objeto plano vacío
                payload_raw = "{}"
                if log.payload_json:
                    if isinstance(log.payload_json, dict):
                        payload_raw = json.dumps(log.payload_json, ensure_ascii=False)
                    else:
                        payload_raw = str(log.payload_json)

                row = [
                    str(log.id),
                    log.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    str(log.level_status),
                    str(log.app_namespace).upper(),
                    str(log.action_type),
                    str(log.module_component),
                    log.operator_user.email if log.operator_user else "SISTEMA",
                    log.target_user.email if log.target_user else "GLOBAL / SISTEMA",
                    str(log.action_name),
                    str(log.search_target or "--"),
                    str(log.ip_address),
                    str(log.user_agent),
                    payload_raw # ◄── INYECTAMOS EL CONTENIDO DEL JSON EN LA FILA
                ]
                ws.append(row)

            # Auto-ajuste inteligente del ancho de las columnas basado en el texto largo
            for col in ws.columns:
                max_len = max(len(str(cell.value or '')) for cell in col)
                col_letter = get_column_letter(col[0].column)
                
                # 🛡️ CONTROL DE ANCHO PARA EL JSON: Evitamos que la columna del JSON crezca miles de caracteres de ancho
                if col[0].value == "Evidencia Técnica (JSON Payload)":
                    ws.column_dimensions[col_letter].width = 45  # Un ancho fijo decente para que no rompa el diseño
                else:
                    ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

            # 4. Empaquetamos el archivo binario en la respuesta HTTP
            response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            response['Content-Disposition'] = f'attachment; filename="axentra_audit_export_{timezone.now().strftime("%Y%m%d_%H%M")}.xlsx"'
            wb.save(response)
            
            return response

        except Exception as e:
            logger.error(f"❌ FALLO AL EXPORTAR AUDITORÍA A EXCEL: {str(e)}")
            return HttpResponse("Error interno al compilar el paquete de evidencia Excel.", status=500)