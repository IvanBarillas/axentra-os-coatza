# apps/security/services/organigrama_services.py
import logging
import uuid
from typing import Tuple, Optional, Dict, Any
from django.db import transaction
from pydantic import ValidationError

from apps.security.models import Dependencia, AreaOperativa, Sede
from apps.security.dtos import DependenciaInputDTO, AreaOperativaInputDTO

logger = logging.getLogger(__name__)

class OrganigramaService:
    """Gobernador Transaccional para la infraestructura orgánica de Axentra OS."""

    # =========================================================================
    # 🗺️ OPERACIONES DE ESCRITURA: SEDES FÍSICAS
    # =========================================================================
    @staticmethod
    def crear_sede(payload: Dict[str, Any]) -> Tuple[bool, Optional[Sede], Optional[Dict[str, Any]]]:
        try:
            nombre = payload.get('nombre')
            direccion = payload.get('direccion', '')

            if not nombre:
                return False, None, {"validation_errors": [{"msg": "El nombre de la sede es obligatorio."}]}

            with transaction.atomic():
                nueva_sede = Sede.objects.create(
                    nombre=nombre,
                    direccion=direccion,
                    is_active=True
                )

            logger.info(f"🗺️ ORGANIGRAMA: Sede Física '{nueva_sede.nombre}' registrada exitosamente.")
            return True, nueva_sede, None
        except Exception as e:
            logger.error(f"❌ TRANSACCIÓN FALLIDA (Crear Sede): {str(e)}")
            return False, None, {"server_error": [str(e)]}

    @staticmethod
    def editar_sede(pk: uuid.UUID, payload: Dict[str, Any]) -> Tuple[bool, Optional[Sede], Optional[Dict[str, Any]]]:
        try:
            nombre = payload.get('nombre')
            direccion = payload.get('direccion', '')

            if not nombre:
                return False, None, {"validation_errors": [{"msg": "El nombre de la sede no puede estar vacío."}]}

            with transaction.atomic():
                sede = Sede.objects.get(pk=pk)
                sede.nombre = nombre
                sede.direccion = direccion
                sede.save()

            logger.info(f"🗺️ ORGANIGRAMA: Sede Física ID={pk} modificada correctamente.")
            return True, sede, None
        except Sede.DoesNotExist:
            return False, None, {"server_error": ["La sede física solicitada no existe."]}
        except Exception as e:
            logger.error(f"❌ TRANSACCIÓN FALLIDA (Editar Sede): {str(e)}")
            return False, None, {"server_error": [str(e)]}

    # =========================================================================
    # 🏛️ OPERACIONES DE ESCRITURA: DEPENDENCIAS
    # =========================================================================
    @staticmethod
    def crear_dependencia(payload: Dict[str, Any]) -> Tuple[bool, Optional[Dependencia], Optional[Dict[str, Any]]]:
        try:
            input_dto = DependenciaInputDTO(**payload)
        except ValidationError as e:
            return False, None, {"validation_errors": e.errors()}

        try:
            with transaction.atomic():
                nueva_dep = Dependencia.objects.create(
                    nombre=input_dto.nombre,
                    encargado_departamento_id=input_dto.encargado_departamento_id
                )
            logger.info(f"🏛️ ORGANIGRAMA: Dependencia '{nueva_dep.nombre}' dada de alta exitosamente.")
            return True, nueva_dep, None
        except Exception as e:
            logger.error(f"❌ TRANSACCIÓN FALLIDA (Crear Dependencia): {str(e)}")
            return False, None, {"server_error": [str(e)]}

    @staticmethod
    def editar_dependencia(pk: uuid.UUID, payload: Dict[str, Any]) -> Tuple[bool, Optional[Dependencia], Optional[Dict[str, Any]]]:
        try:
            input_dto = DependenciaInputDTO(**payload)
        except ValidationError as e:
            return False, None, {"validation_errors": e.errors()}

        try:
            with transaction.atomic():
                dep = Dependencia.objects.get(pk=pk, is_deleted=False)
                dep.nombre = input_dto.nombre
                dep.encargado_departamento_id = input_dto.encargado_departamento_id
                dep.save()
            logger.info(f"🏛️ ORGANIGRAMA: Dependencia '{dep.nombre}' actualizada correctamente.")
            return True, dep, None
        except Dependencia.DoesNotExist:
            return False, None, {"server_error": ["La dependencia solicitada no existe o fue eliminada."]}
        except Exception as e:
            logger.error(f"❌ TRANSACCIÓN FALLIDA (Editar Dependencia): {str(e)}")
            return False, None, {"server_error": [str(e)]}

    # =========================================================================
    # 🎛️ OPERACIONES DE ESCRITURA: ÁREAS OPERATIVAS (LA MATRIZ DE ASIGNACIÓN)
    # =========================================================================
    @staticmethod
    def crear_area(payload: Dict[str, Any]) -> Tuple[bool, Optional[AreaOperativa], Optional[Dict[str, Any]]]:
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
    def editar_area(pk: uuid.UUID, payload: Dict[str, Any]) -> Tuple[bool, Optional[AreaOperativa], Optional[Dict[str, Any]]]:
        try:
            input_dto = AreaOperativaInputDTO(**payload)
        except ValidationError as e:
            return False, None, {"validation_errors": e.errors()}

        try:
            with transaction.atomic():
                area = AreaOperativa.objects.get(pk=pk, is_deleted=False)
                area.nombre = input_dto.nombre
                area.save()
            logger.info(f"📍 ORGANIGRAMA: Parámetros descriptivos de la oficina ID={pk} actualizados.")
            return True, area, None
        except AreaOperativa.DoesNotExist:
            return False, None, {"server_error": ["El área operativa solicitada no existe o fue eliminada."]}
        except Exception as e:
            logger.error(f"❌ TRANSACCIÓN FALLIDA (Editar Área): {str(e)}")
            return False, None, {"server_error": [str(e)]}

    # =========================================================================
    # 🗑️ BAJAS LÓGICAS CON INTERPOLACIÓN EN CASCADA (SOFT DELETE)
    # =========================================================================
    @staticmethod
    def dar_baja_logica_sede(pk: uuid.UUID) -> Tuple[bool, str]:
        try:
            with transaction.atomic():
                sede = Sede.objects.get(pk=pk)
                sede.is_active = False
                sede.save()
                AreaOperativa.objects.filter(sede_fisica=sede).update(is_active=False)
            logger.warning(f"⚠️ AUDITORÍA: Soft-Delete aplicado en Sede Física ID=[{pk}].")
            return True, f"La sede '{sede.nombre}' fue archivada y sus celdas operativas inactivadas."
        except Sede.DoesNotExist:
            return False, "La sede física solicitada no existe."
        except Exception as e:
            return False, f"Error transaccional: {str(e)}"

    @staticmethod
    def dar_baja_logica_dependencia(pk: uuid.UUID) -> Tuple[bool, str]:
        try:
            with transaction.atomic():
                dependencia = Dependencia.objects.get(pk=pk)
                dependencia.is_active = False
                dependencia.is_deleted = True
                dependencia.save()
                dependencia.areas_operativas_instaladas.update(is_active=False, is_deleted=True)
            logger.warning(f"⚠️ AUDITORÍA: Soft-Delete aplicado en Dependencia ID=[{pk}] y dependientes.")
            return True, f"La dependencia '{dependencia.nombre}' y sus oficinas fueron dadas de baja correctamente."
        except Dependencia.DoesNotExist:
            return False, "La dependencia solicitada no existe."
        except Exception as e:
            return False, f"Error interno del servidor: {str(e)}"

    @staticmethod
    def dar_baja_logica_area(pk: uuid.UUID) -> Tuple[bool, str]:
        try:
            with transaction.atomic():
                area = AreaOperativa.objects.get(pk=pk)
                area.is_active = False
                area.is_deleted = True
                area.save()
            logger.info(f"🗑️ AUDITORÍA: Soft-Delete en Área ID=[{pk}].")
            return True, f"El área '{area.nombre}' fue removida con éxito de la matriz."
        except AreaOperativa.DoesNotExist:
            return False, "El área operativa solicitada no existe."
        except Exception as e:
            return False, f"Error transaccional: {str(e)}"