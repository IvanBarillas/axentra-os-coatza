# apps/security/services/organigrama_services.py
import logging
from django.utils import timezone
import uuid
import sys
import os
import traceback
from typing import Tuple, Optional, Dict, Any
from django.db import transaction
from pydantic import ValidationError

from apps.security.dtos.organigrama_dtos import AreaOperativaInputDTO, DependenciaInputDTO
from apps.security.models import Dependencia, AreaOperativa, Sede
from apps.security.models.accounts import UserProfile
from apps.security.models.audit import SecurityAuditLog
from apps.security.utils.forensic_auditor import ForensicAuditor

logger = logging.getLogger(__name__)

class OrganigramaService:
    """Gobernador Transaccional e Inyector Forense de la Infraestructura de Axentra OS."""

    # =========================================================================
    # 🗺️ OPERACIONES DE ESCRITURA: SEDES FÍSICAS (INMUEBLES)
    # =========================================================================
    @staticmethod
    def crear_sede(request, payload: Dict[str, Any]) -> Tuple[bool, Optional[Sede], Optional[Dict[str, Any]]]:
        """Aprovisionamiento transaccional de un nuevo inmueble institucional con bitácora forense."""
        try:
            nombre = payload.get('nombre', '').strip()
            direccion = payload.get('direccion', '').strip()

            if not nombre:
                return False, None, {"validation_errors": [{"msg": "El nombre de la sede es obligatorio."}]}

            with transaction.atomic():
                nueva_sede = Sede.objects.create(
                    nombre=nombre,
                    direccion=direccion,
                    is_active=True
                )

            # 🪐 PERSISTENCIA EN BITÁCORA FORENSE NORMALIZADA
            ForensicAuditor.registrar_evento(
                request=request,
                action_type=SecurityAuditLog.ActionTypes.CREATE,
                module_component="SEDES_INFRAESTRUCTURA",
                action_name="ALTA_SEDE_FISICA",
                target_scope=f"Aprovisionamiento del inmueble municipal: {nueva_sede.nombre}.",
                level=SecurityAuditLog.Levels.SUCCESS,
                search_target=nueva_sede.id,
                payload={'nombre_sede': nueva_sede.nombre, 'direccion': nueva_sede.direccion}
            )

            logger.info(f"🗺️ ORGANIGRAMA: Sede Física '{nueva_sede.nombre}' registrada exitosamente.")
            return True, nueva_sede, None
        except Exception as e:
            logger.error(f"❌ TRANSACCIÓN FALLIDA (Crear Sede): {str(e)}")
            return False, None, {"server_error": [str(e)]}

    @staticmethod
    def actualizar_sede(request, sede_instancia: Sede, payload: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Mutación atómica de los parámetros geográficos calculando snapshot analítico."""
        try:
            nombre = payload.get('nombre', '').strip()
            direccion = payload.get('direccion', '').strip()

            if not nombre:
                return False, {"validation_errors": [{"msg": "El nombre de la sede no puede estar vacío."}]}

            # Snapshot previo
            snapshot_anterior = {
                'nombre': sede_instancia.nombre,
                'direccion': sede_instancia.direccion,
                'is_active': sede_instancia.is_active
            }

            with transaction.atomic():
                sede_instancia.nombre = nombre
                sede_instancia.direccion = direccion
                if 'is_active' in payload:
                    sede_instancia.is_active = payload['is_active']
                sede_instancia.save()

            snapshot_nuevo = {
                'nombre': sede_instancia.nombre,
                'direccion': sede_instancia.direccion,
                'is_active': sede_instancia.is_active
            }

            # 🪐 COMPILACIÓN DEL DELTA FORENSE
            payload_delta = {
                'estado_anterior': snapshot_anterior,
                'estado_nuevo': snapshot_nuevo,
                'campos_alterados': [k for k, v in snapshot_anterior.items() if snapshot_nuevo[k] != v]
            }

            ForensicAuditor.registrar_evento(
                request=request,
                action_type=SecurityAuditLog.ActionTypes.UPDATE,
                module_component="SEDES_INFRAESTRUCTURA",
                action_name="ACTUALIZACION_METADATOS_SEDE",
                target_scope=f"Modificación de parámetros geográficos o nomenclatura de la sede: {sede_instancia.nombre}.",
                level=SecurityAuditLog.Levels.INFO,
                search_target=sede_instancia.id,
                payload=payload_delta
            )

            logger.info(f"🗺️ ORGANIGRAMA: Sede Física ID={sede_instancia.id} modificada correctamente.")
            return True, None
        except Exception as e:
            logger.error(f"❌ TRANSACCIÓN FALLIDA (Actualizar Sede): {str(e)}")
            return False, {"server_error": [str(e)]}

    # =========================================================================
    # 🏛️ OPERACIONES DE ESCRITURA: DEPENDENCIAS (DIRECCIONES GENERALES)
    # =========================================================================
    @staticmethod
    def crear_dependencia(
        request,
        payload: Dict[str, Any],
    ) -> Tuple[bool, Optional[Dependencia], Optional[Dict[str, Any]]]:
        """
        Inyección de una dependencia administrativa validada por Pydantic DTO
        con soporte de jerarquía parent y bitácora forense.
        """

        try:
            input_dto = DependenciaInputDTO(**payload)

        except ValidationError as e:
            return False, None, {
                "validation_errors": e.errors(),
            }

        try:
            with transaction.atomic():
                nueva_dep = Dependencia.objects.create(
                    nombre=input_dto.nombre,
                    parent_id=input_dto.parent_id,
                    encargado_departamento_id=input_dto.encargado_departamento_id,
                    is_active=True,
                    is_deleted=False,
                )

                ForensicAuditor.registrar_evento(
                    request=request,
                    action_type=SecurityAuditLog.ActionTypes.CREATE,
                    module_component="DEPENDENCIAS_RAIZ",
                    action_name="ALTA_DEPENDENCIA_ORGANICA",
                    target_scope=(
                        f"Alta de dependencia administrativa en organigrama: "
                        f"{nueva_dep.nombre}."
                    ),
                    level=SecurityAuditLog.Levels.SUCCESS,
                    search_target=str(nueva_dep.id),
                    payload={
                        "dependencia_id": str(nueva_dep.id),
                        "nombre_dependencia": nueva_dep.nombre,
                        "parent_id": (
                            str(nueva_dep.parent_id)
                            if nueva_dep.parent_id
                            else None
                        ),
                        "encargado_id": (
                            str(nueva_dep.encargado_departamento_id)
                            if nueva_dep.encargado_departamento_id
                            else None
                        ),
                        "is_root_node": nueva_dep.parent_id is None,
                    },
                )

            logger.info(
                f"🏛️ AXENTRA OS: Dependencia '{nueva_dep.nombre}' dada de alta exitosamente. "
                f"Parent=[{nueva_dep.parent_id}]"
            )

            return True, nueva_dep, None

        except Exception as e:
            logger.error(
                f"❌ TRANSACCIÓN FALLIDA (Crear Dependencia): {str(e)}"
            )

            return False, None, {
                "server_error": [str(e)],
            }

    @staticmethod
    def actualizar_dependencia(
        request,
        dep_instancia: Dependencia,
        payload: Dict[str, Any],
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Modificación estructural de nomenclatura, jerarquía o titular
        de una dependencia administrativa.
        """

        try:
            snapshot_anterior = {
                "nombre": dep_instancia.nombre,
                "parent_id": (
                    str(dep_instancia.parent_id)
                    if dep_instancia.parent_id
                    else None
                ),
                "encargado_id": (
                    str(dep_instancia.encargado_departamento_id)
                    if dep_instancia.encargado_departamento_id
                    else None
                ),
            }

            with transaction.atomic():
                dep_instancia.nombre = payload.get("nombre")
                dep_instancia.parent_id = payload.get("parent_id")
                dep_instancia.encargado_departamento_id = payload.get(
                    "encargado_departamento_id"
                )

                dep_instancia.save()

                dep_instancia.refresh_from_db()

                snapshot_nuevo = {
                    "nombre": dep_instancia.nombre,
                    "parent_id": (
                        str(dep_instancia.parent_id)
                        if dep_instancia.parent_id
                        else None
                    ),
                    "encargado_id": (
                        str(dep_instancia.encargado_departamento_id)
                        if dep_instancia.encargado_departamento_id
                        else None
                    ),
                }

                payload_delta = {
                    "estado_anterior": snapshot_anterior,
                    "estado_nuevo": snapshot_nuevo,
                    "campos_alterados": [
                        campo
                        for campo, valor_anterior in snapshot_anterior.items()
                        if snapshot_nuevo[campo] != valor_anterior
                    ],
                }

                ForensicAuditor.registrar_evento(
                    request=request,
                    action_type=SecurityAuditLog.ActionTypes.UPDATE,
                    module_component="DEPENDENCIAS_RAIZ",
                    action_name="MUTACION_ESTRUCTURAL_DEPENDENCIA",
                    target_scope=(
                        f"Modificación estructural de dependencia administrativa: "
                        f"{dep_instancia.nombre}."
                    ),
                    level=SecurityAuditLog.Levels.INFO,
                    search_target=str(dep_instancia.id),
                    payload=payload_delta,
                )

            logger.info(
                f"🏛️ AXENTRA OS: Dependencia '{dep_instancia.nombre}' actualizada correctamente. "
                f"Parent=[{dep_instancia.parent_id}]"
            )

            return True, None

        except Exception as e:
            logger.error(
                f"❌ TRANSACCIÓN FALLIDA (Actualizar Dependencia): {str(e)}"
            )

            return False, {
                "server_error": [str(e)],
            }

    # =========================================================================
    # 🎛️ OPERACIONES DE ESCRITURA: ÁREAS OPERATIVAS (OFICINAS INTERNAS)
    # =========================================================================
    @staticmethod
    def crear_area(request, payload: Dict[str, Any]) -> Tuple[bool, Optional[AreaOperativa], Optional[Dict[str, Any]]]:
        """Instalación de una oficina interna o departamento en el mapa orgánico."""
        try:
            input_dto = AreaOperativaInputDTO(**payload)
        except ValidationError as e:
            return False, None, {"validation_errors": e.errors()}

        try:
            with transaction.atomic():
                dep = Dependencia.objects.get(id=input_dto.dependencia_id, is_deleted=False)
                sede_fisica = Sede.objects.get(id=input_dto.sede_fisica_id, is_active=True)

                nueva_area = AreaOperativa.objects.create(
                    dependencia=dep,
                    sede_fisica=sede_fisica,
                    nombre=input_dto.nombre,  
                )

            # 🪐 PERSISTENCIA FORENSE
            ForensicAuditor.registrar_evento(
                request=request,
                action_type=SecurityAuditLog.ActionTypes.CREATE,
                module_component="AREAS_MATRIZ",
                action_name="ALTA_NODO_MATRIZ_OPERATIVA",
                target_scope=f"Aprovisionamiento de sub-oficina interna: {nueva_area.nombre} adscrita a {dep.nombre}.",
                level=SecurityAuditLog.Levels.SUCCESS,
                search_target=nueva_area.id,
                payload={
                    'nombre_area': nueva_area.nombre,
                    'dependencia_id': str(dep.id),
                    'sede_fisica_id': str(sede_fisica.id)
                }
            )

            logger.info(f"📍 ORGANIGRAMA: Matriz Actualizada. Oficina '{nueva_area.nombre}' instalada.")
            return True, nueva_area, None
        except Dependencia.DoesNotExist:
            return False, None, {"server_error": ["La dependencia superior no existe o está inactiva."]}
        except Sede.DoesNotExist:
            return False, None, {"server_error": ["La sede física asignada no existe o está dada de baja."]}
        except Exception as e:
            logger.error(f"❌ TRANSACCIÓN FALLIDA (Crear Área en Matriz): {str(e)}")
            return False, None, {"server_error": [str(e)]}

    @staticmethod
    def actualizar_area(request, area_instancia: AreaOperativa, payload: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Re-adscripción geográfica y jerárquica total de un departamento activo."""
        try:
            input_dto = AreaOperativaInputDTO(**payload)
        except ValidationError as e:
            return False, {"validation_errors": e.errors()}

        try:
            snapshot_anterior = {
                'nombre': area_instancia.nombre,
                'dependencia_id': str(area_instancia.dependencia.id),
                'sede_fisica_id': str(area_instancia.sede_fisica.id)
            }

            with transaction.atomic():
                dep = Dependencia.objects.get(id=input_dto.dependencia_id, is_deleted=False)
                sede_fisica = Sede.objects.get(id=input_dto.sede_fisica_id, is_active=True)

                area_instancia.nombre = input_dto.nombre
                area_instancia.dependencia = dep
                area_instancia.sede_fisica = sede_fisica
                area_instancia.save()

            snapshot_nuevo = {
                'nombre': area_instancia.nombre,
                'dependencia_id': str(area_instancia.dependencia.id),
                'sede_fisica_id': str(area_instancia.sede_fisica.id)
            }

            payload_delta = {
                'estado_anterior': snapshot_anterior,
                'estado_nuevo': snapshot_nuevo,
                'campos_alterados': [k for k, v in snapshot_anterior.items() if snapshot_nuevo[k] != v]
            }

            # 🪐 BITÁCORA FORENSE
            ForensicAuditor.registrar_evento(
                request=request,
                action_type=SecurityAuditLog.ActionTypes.UPDATE,
                module_component="AREAS_MATRIZ",
                action_name="RE_ADSCRIPCION_NODO_OPERATIVO",
                target_scope=f"Actualización de adscripción territorial o denominación de la sub-oficina: {area_instancia.nombre}.",
                level=SecurityAuditLog.Levels.INFO,
                search_target=area_instancia.id,
                payload=payload_delta
            )
                
            logger.info(f"📍 ORGANIGRAMA: Oficinas del nodo ID={area_instancia.id} re-mapeadas con éxito.")
            return True, None
        except Dependencia.DoesNotExist:
            return False, {"server_error": ["La dependencia superior seleccionada no es válida."]}
        except Sede.DoesNotExist:
            return False, {"server_error": ["La sede física seleccionada no existe o está congelada."]}
        except Exception as e:
            logger.error(f"❌ TRANSACCIÓN FALLIDA (Actualizar Área): {str(e)}")
            return False, {"server_error": [str(e)]}

    # =========================================================================
    # 🗑️ BAJAS LÓGICAS CON INTERPOLACIÓN EN CASCADA (SOFT DELETE)
    # =========================================================================
    @staticmethod
    def eliminar_sede(request, sede_instancia: Sede) -> tuple[bool, dict]:
        """
        Baja lógica protegida de sede física.

        Regla Axentra:
        Una sede sólo puede darse de baja si no tiene áreas operativas vivas.
        Las dependencias no se apagan al borrar una sede; las áreas deben reubicarse
        o darse de baja explícitamente antes de eliminar el inmueble.
        """
        areas_activas = AreaOperativa.objects.filter(sede_fisica=sede_instancia, is_deleted=False).count()
        dependencias_vinculadas = Dependencia.objects.filter(areas__sede_fisica=sede_instancia, areas__is_deleted=False, is_deleted=False).distinct().count()

        if areas_activas > 0:
            return False, {
                "server_error": [
                    f"No se puede dar de baja la sede '{sede_instancia.nombre}' porque tiene {areas_activas} área(s) operativa(s) vinculada(s) y {dependencias_vinculadas} dependencia(s) presente(s). Primero reubica o da de baja esas áreas."
                ]
            }

        with transaction.atomic():
            sede_instancia.is_deleted = True
            sede_instancia.is_active = False
            
            campos = ["is_deleted", "is_active", "updated_at"]
            if hasattr(sede_instancia, "deleted_at"):
                sede_instancia.deleted_at = timezone.now()
                campos.append("deleted_at")
                
            sede_instancia.save(update_fields=campos)

            ForensicAuditor.registrar_evento(
                request=request,
                action_type=SecurityAuditLog.ActionTypes.DELETE,
                module_component="SEDES_INFRAESTRUCTURA",
                action_name="SOFT_DELETE_SEDE_INFRAESTRUCTURA",
                target_scope=f"Baja lógica protegida del inmueble {sede_instancia.nombre}. No existían áreas operativas vivas vinculadas al momento de la baja.",
                level=SecurityAuditLog.Levels.CRITICAL,
                search_target=str(sede_instancia.id),
                payload={
                    "sede_id": str(sede_instancia.id),
                    "sede_nombre": sede_instancia.nombre,
                    "is_deleted": True,
                    "is_active": False,
                    "areas_activas": areas_activas,
                    "dependencias_vinculadas": dependencias_vinculadas,
                },
            )

        logger.warning(f"⚠️ AUDITORÍA: Soft-Delete protegido aplicado sobre Sede Física ID=[{sede_instancia.id}].")
        return True, {}

    @staticmethod
    def eliminar_dependencia(request, dep_instancia: Dependencia) -> tuple[bool, dict]:
        """
        Baja lógica protegida de dependencia administrativa.

        Regla Axentra:
        Una dependencia sólo puede darse de baja si no tiene áreas operativas vivas.
        Las áreas no se apagan ni se eliminan automáticamente; deben reubicarse
        o darse de baja explícitamente antes de eliminar la dependencia.
        """

        areas_activas = (
            AreaOperativa.objects
            .filter(
                dependencia=dep_instancia,
                is_deleted=False,
            )
            .count()
        )

        sedes_vinculadas = (
            Sede.objects
            .filter(
                areas__dependencia=dep_instancia,
                areas__is_deleted=False,
                is_deleted=False,
            )
            .distinct()
            .count()
        )

        if areas_activas > 0:
            return False, {
                "server_error": [
                    (
                        f"No se puede dar de baja la dependencia '{dep_instancia.nombre}' "
                        f"porque tiene {areas_activas} área(s) operativa(s) vinculada(s) "
                        f"en {sedes_vinculadas} sede(s). "
                        "Primero reubica o da de baja esas áreas."
                    )
                ]
            }

        with transaction.atomic():
            dep_instancia.is_active = False
            dep_instancia.is_deleted = True

            if hasattr(dep_instancia, "deleted_at"):
                dep_instancia.deleted_at = timezone.now()
                dep_instancia.save(
                    update_fields=[
                        "is_active",
                        "is_deleted",
                        "deleted_at",
                        "updated_at",
                    ]
                )
            else:
                dep_instancia.save(
                    update_fields=[
                        "is_active",
                        "is_deleted",
                        "updated_at",
                    ]
                )

            ForensicAuditor.registrar_evento(
                request=request,
                action_type=SecurityAuditLog.ActionTypes.DELETE,
                module_component="DEPENDENCIAS_RAIZ",
                action_name="SOFT_DELETE_DEPENDENCIA_PROTEGIDA",
                target_scope=(
                    f"Baja lógica protegida de la dependencia {dep_instancia.nombre}. "
                    "No existían áreas operativas vivas vinculadas al momento de la baja."
                ),
                level=SecurityAuditLog.Levels.CRITICAL,
                search_target=str(dep_instancia.id),
                payload={
                    "dependencia_id": str(dep_instancia.id),
                    "dependencia_nombre": dep_instancia.nombre,
                    "is_active": False,
                    "is_deleted": True,
                    "areas_activas": areas_activas,
                    "sedes_vinculadas": sedes_vinculadas,
                },
            )

        logger.warning(
            f"⚠️ AUDITORÍA: Soft-Delete protegido aplicado sobre Dependencia ID=[{dep_instancia.id}]."
        )

        return True, {}

    @staticmethod
    def eliminar_area(request, area_instancia: AreaOperativa) -> tuple[bool, dict]:
        """
        Baja lógica protegida de un área operativa.

        Regla Axentra:
        Un área no puede darse de baja si todavía tiene funcionarios adscritos.
        Primero se deben reubicar o desasignar esos funcionarios.
        """

        funcionarios_adscritos = (
            UserProfile.objects
            .filter(
                area=area_instancia,
                user__is_deleted=False,
            )
            .count()
        )

        if funcionarios_adscritos > 0:
            return False, {
                "server_error": [
                    (
                        f"No se puede dar de baja el área operativa '{area_instancia.nombre}' "
                        f"porque tiene {funcionarios_adscritos} funcionario(s) adscrito(s). "
                        "Primero reubica o desasigna a esos funcionarios."
                    )
                ]
            }

        with transaction.atomic():
            area_instancia.is_active = False
            area_instancia.is_deleted = True

            if hasattr(area_instancia, "deleted_at"):
                area_instancia.deleted_at = timezone.now()
                area_instancia.save(
                    update_fields=[
                        "is_active",
                        "is_deleted",
                        "deleted_at",
                        "updated_at",
                    ]
                )
            else:
                area_instancia.save(
                    update_fields=[
                        "is_active",
                        "is_deleted",
                        "updated_at",
                    ]
                )

            ForensicAuditor.registrar_evento(
                request=request,
                action_type=SecurityAuditLog.ActionTypes.DELETE,
                module_component="AREAS_MATRIZ",
                action_name="SOFT_DELETE_AREA_PROTEGIDO",
                target_scope=(
                    f"Baja lógica protegida del área operativa: {area_instancia.nombre}. "
                    "No existían funcionarios adscritos al momento de la baja."
                ),
                level=SecurityAuditLog.Levels.CRITICAL,
                search_target=str(area_instancia.id),
                payload={
                    "area_id": str(area_instancia.id),
                    "area_nombre": area_instancia.nombre,
                    "dependencia_id": str(area_instancia.dependencia_id),
                    "sede_fisica_id": str(area_instancia.sede_fisica_id),
                    "funcionarios_adscritos": funcionarios_adscritos,
                },
            )

        logger.warning(
            f"🗑️ AUDITORÍA: Soft-Delete protegido aplicado en Área ID=[{area_instancia.id}] "
            f"Nombre=[{area_instancia.nombre}] Funcionarios=[{funcionarios_adscritos}]"
        )

        return True, {}