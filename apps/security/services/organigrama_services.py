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
        """Aprovisionamiento transaccional de un nuevo inmueble institucional."""
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
    def actualizar_sede(sede_instancia: Sede, payload: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Mutación atómica de los parámetros geográficos de una sede en la base de datos."""
        try:
            nombre = payload.get('nombre')
            direccion = payload.get('direccion', '')

            if not nombre:
                return False, {"validation_errors": [{"msg": "El nombre de la sede no puede estar vacío."}]}

            with transaction.atomic():
                sede_instancia.nombre = nombre
                sede_instancia.direccion = direccion
                # Persistimos el estatus de activación si viene explícito en el payload del formulario
                if 'is_active' in payload:
                    sede_instancia.is_active = payload['is_active']
                sede_instancia.save()

            logger.info(f"🗺️ ORGANIGRAMA: Sede Física ID={sede_instancia.id} modificada correctamente.")
            return True, None
        except Exception as e:
            logger.error(f"❌ TRANSACCIÓN FALLIDA (Actualizar Sede): {str(e)}")
            return False, {"server_error": [str(e)]}

    # =========================================================================
    # 🏛️ OPERACIONES DE ESCRITURA: DEPENDENCIAS
    # =========================================================================
    @staticmethod
    def crear_dependencia(payload: Dict[str, Any]) -> Tuple[bool, Optional[Dependencia], Optional[Dict[str, Any]]]:
        """Inyección de una Dirección General o Secretaría validada por Pydantic DTO."""
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
    def actualizar_dependencia(dep_instancia: Dependencia, payload: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Modificación estructural de nomenclatura o asignación de titulares en una dirección."""
        try:
            input_dto = DependenciaInputDTO(**payload)
        except ValidationError as e:
            return False, {"validation_errors": e.errors()}

        try:
            with transaction.atomic():
                dep_instancia.nombre = input_dto.nombre
                dep_instancia.encargado_departamento_id = input_dto.encargado_departamento_id
                dep_instancia.save()
            logger.info(f"🏛️ ORGANIGRAMA: Dependencia '{dep_instancia.nombre}' actualizada correctamente.")
            return True, None
        except Exception as e:
            logger.error(f"❌ TRANSACCIÓN FALLIDA (Actualizar Dependencia): {str(e)}")
            return False, {"server_error": [str(e)]}

    @staticmethod
    def editar_dependencia(pk: uuid.UUID, payload: Dict[str, Any]) -> Tuple[bool, Optional[Dependencia], Optional[Dict[str, Any]]]:
        """Alias compatible para actualizaciones primitivas de dependencias por ID."""
        try:
            with transaction.atomic():
                dep = Dependencia.objects.get(pk=pk, is_deleted=False)
                exito, errores = OrganigramaService.actualizar_dependencia(dep, payload)
                if not exito:
                    return False, None, errores
            return True, dep, None
        except Dependencia.DoesNotExist:
            return False, None, {"server_error": ["La dependencia solicitada no existe o fue eliminada."]}
        except Exception as e:
            return False, None, {"server_error": [str(e)]}

    # =========================================================================
    # 🎛️ OPERACIONES DE ESCRITURA: ÁREAS OPERATIVAS (LA MATRIZ DE ASIGNACIÓN)
    # =========================================================================
    @staticmethod
    def crear_area(payload: Dict[str, Any]) -> Tuple[bool, Optional[AreaOperativa], Optional[Dict[str, Any]]]:
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
    def actualizar_area(area_instancia: AreaOperativa, payload: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Re-adscripción geográfica y jerárquica total de un departamento activo."""
        try:
            input_dto = AreaOperativaInputDTO(**payload)
        except ValidationError as e:
            return False, {"validation_errors": e.errors()}

        try:
            with transaction.atomic():
                # Validamos de forma síncrona que las entidades a vincular existan en Postgres
                dep = Dependencia.objects.get(id=input_dto.dependencia_id, is_deleted=False)
                sede_fisica = Sede.objects.get(id=input_dto.sede_fisica_id, is_active=True)

                area_instancia.nombre = input_dto.nombre
                area_instancia.dependencia = dep
                area_instancia.sede_fisica = sede_fisica
                area_instancia.save()
                
            logger.info(f"📍 ORGANIGRAMA: Oficinas del nodo ID={area_instancia.id} re-mapeadas con éxito.")
            return True, None
        except Dependencia.DoesNotExist:
            return False, {"server_error": ["La dependencia superior seleccionada no es válida."]}
        except Sede.DoesNotExist:
            return False, {"server_error": ["La sede física seleccionada no existe o está congelada."]}
        except Exception as e:
            logger.error(f"❌ TRANSACCIÓN FALLIDA (Actualizar Área): {str(e)}")
            return False, {"server_error": [str(e)]}

    @staticmethod
    def editar_area(pk: uuid.UUID, payload: Dict[str, Any]) -> Tuple[bool, Optional[AreaOperativa], Optional[Dict[str, Any]]]:
        """Alias compatible para mutaciones por ID de áreas operativas."""
        try:
            with transaction.atomic():
                area = AreaOperativa.objects.get(pk=pk, is_deleted=False)
                exito, errores = OrganigramaService.actualizar_area(area, payload)
                if not exito:
                    return False, None, errores
            return True, area, None
        except AreaOperativa.DoesNotExist:
            return False, None, {"server_error": ["El área operativa solicitada no existe o fue eliminada."]}
        except Exception as e:
            return False, None, {"server_error": [str(e)]}

    # =========================================================================
    # 🗑️ BAJAS LÓGICAS CON INTERPOLACIÓN EN CASCADA (SOFT DELETE)
    # =========================================================================
    @staticmethod
    def eliminar_sede(sede_instancia: Sede) -> None:
        """Baja lógica de instancia: Desactiva el inmueble congelando dependientes."""
        with transaction.atomic():
            sede_instancia.is_deleted = True
            sede_instancia.is_active = False
            sede_instancia.save()
            AreaOperativa.objects.filter(sede_fisica=sede_instancia).update(is_active=False)
        logger.warning(f"⚠️ AUDITORÍA: Soft-Delete instantáneo aplicado sobre Sede Física ID=[{sede_instancia.id}].")

    @staticmethod
    def dar_baja_logica_sede(pk: uuid.UUID) -> Tuple[bool, str]:
        """Baja por ID primitivo: Congela la sede e inhabilita las celdas adscritas."""
        try:
            with transaction.atomic():
                sede = Sede.objects.get(pk=pk)
                OrganigramaService.eliminar_sede(sede)
            return True, f"La sede '{sede.nombre}' fue archivada y sus celdas operativas inactivadas."
        except Sede.DoesNotExist:
            return False, "La sede física solicitada no existe."
        except Exception as e:
            return False, f"Error transaccional: {str(e)}"

    @staticmethod
    def eliminar_dependencia(dep_instancia: Dependencia) -> None:
        """Baja lógica de instancia: Marca is_deleted y arrastra sub-oficinas en cascada."""
        with transaction.atomic():
            dep_instancia.is_active = False
            dep_instancia.is_deleted = True
            dep_instancia.save()
            # Django usa el related_name correspondiente o el fallback del modelo
            if hasattr(dep_instancia, 'areas_operativas_instaladas'):
                dep_instancia.areas_operativas_instaladas.update(is_active=False, is_deleted=True)
            else:
                AreaOperativa.objects.filter(dependencia=dep_instancia).update(is_active=False, is_deleted=True)
        logger.warning(f"⚠️ AUDITORÍA: Soft-Delete instantáneo aplicado en Dependencia ID=[{dep_instancia.id}].")

    @staticmethod
    def dar_baja_logica_dependencia(pk: uuid.UUID) -> Tuple[bool, str]:
        """Baja por ID primitivo: Elimina lógicamente la dirección y sus ramas inferiores."""
        try:
            with transaction.atomic():
                dependencia = Dependencia.objects.get(pk=pk)
                OrganigramaService.eliminar_dependencia(dependencia)
            return True, f"La dependencia '{dependencia.nombre}' y sus oficinas fueron dadas de baja correctamente."
        except Dependencia.DoesNotExist:
            return False, "La dependencia solicitada no existe."
        except Exception as e:
            return False, f"Error interno del servidor: {str(e)}"

    @staticmethod
    def eliminar_area(area_instancia: AreaOperativa) -> None:
        """Baja lógica de instancia: Remueve la oficina de la matriz de adscripción."""
        with transaction.atomic():
            area_instancia.is_active = False
            area_instancia.is_deleted = True
            area_instancia.save()
        logger.info(f"🗑️ AUDITORÍA: Soft-Delete instantáneo aplicado en Área ID=[{area_instancia.id}].")

    @staticmethod
    def dar_baja_logica_area(pk: uuid.UUID) -> Tuple[bool, str]:
        """Baja por ID primitivo: Soft delete sobre un departamento específico."""
        try:
            with transaction.atomic():
                area = AreaOperativa.objects.get(pk=pk)
                OrganigramaService.eliminar_area(area)
            return True, f"El área '{area.nombre}' fue removida con éxito de la matriz."
        except AreaOperativa.DoesNotExist:
            return False, "El área operativa solicitada no existe."
        except Exception as e:
            return False, f"Error transaccional: {str(e)}"