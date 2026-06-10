# apps/security/services/accounts_services.py
import logging
import sys
import os
import traceback
import uuid
from typing import Optional, Tuple, Dict, Any
from django.db import transaction
from django.contrib.auth import get_user_model
from pydantic import ValidationError

from apps.security.models import UserProfile, AreaOperativa
from apps.security.dtos import CrearFuncionarioInputDTO, EditarFuncionarioInputDTO

User = get_user_model()
logger = logging.getLogger(__name__)

class FuncionarioService:
    """Cerebro Transaccional Mutacional de Identidades."""

    @staticmethod
    def crear_funcionario(post_data: Dict[str, Any], raw_password: str = None) -> Tuple[bool, Optional[User], Optional[Dict[str, Any]]]:
        try:
            input_dto = CrearFuncionarioInputDTO(**post_data)
        except ValidationError as e:
            return False, None, {"validation_errors": e.errors()}

        try:
            with transaction.atomic():
                area = AreaOperativa.objects.get(id=input_dto.area_id)
                password_final = raw_password or User.objects.make_random_password()
                
                usuario = User.objects.create_user(
                    email=input_dto.email,
                    password=password_final,
                    first_name=input_dto.first_name,
                    last_name=input_dto.last_name,
                    phone=input_dto.phone
                )

                UserProfile.objects.create(
                    user=usuario,
                    area=area,
                    puesto=input_dto.puesto,
                    telefono_oficina=input_dto.telefono_oficina
                )

            FuncionarioService._imprimir_auditoria_mutacion("ALTA DE FUNCIONARIO", usuario.email, "🟢 ÉXITO ATÓMICO")
            return True, usuario, None
        except AreaOperativa.DoesNotExist:
            return False, None, {"server_error": ["La celda operativa de la matriz especificada no es válida o está inactiva."]}
        except Exception as e:
            logger.error(f"❌ FALLO CRÍTICO EN ALTA DE FUNCIONARIO: {str(e)}")
            return False, None, {"server_error": [str(e)]}

    @staticmethod
    def editar_funcionario(pk: uuid.UUID, post_data: Dict[str, Any]) -> Tuple[bool, Optional[User], Optional[Dict[str, Any]]]:
        try:
            input_dto = EditarFuncionarioInputDTO(**post_data)
        except ValidationError as e:
            return False, None, {"validation_errors": e.errors()}

        try:
            with transaction.atomic():
                # 🟢 OPTIMIZACIÓN: Traemos el usuario y su perfil en un solo impacto SQL mitigando el N+1
                usuario = User.objects.select_related('axentra_profile').get(pk=pk)
                perfil = usuario.axentra_profile
                area = AreaOperativa.objects.get(id=input_dto.area_id)

                usuario.email = input_dto.email
                usuario.first_name = input_dto.first_name
                usuario.last_name = input_dto.last_name
                usuario.phone = input_dto.phone
                usuario.save()

                perfil.area = area
                perfil.puesto = input_dto.puesto
                perfil.telefono_oficina = input_dto.telefono_oficina
                perfil.save()

            FuncionarioService._imprimir_auditoria_mutacion("MODIFICACIÓN DE FICHA", usuario.email, "🟢 ÉXITO ATÓMICO")
            return True, usuario, None
        except User.DoesNotExist:
            return False, None, {"server_error": ["El funcionario objetivo no existe en el padrón."]}
        except UserProfile.DoesNotExist:
            return False, None, {"server_error": ["El funcionario no cuenta con un expediente de adscripción."]}
        except AreaOperativa.DoesNotExist:
            return False, None, {"server_error": ["La nueva celda de la matriz especificada no existe."]}
        except Exception as e:
            return False, None, {"server_error": [str(e)]}

    @staticmethod
    def forzar_reseteo_password(pk: uuid.UUID, nueva_password: str) -> bool:
        try:
            usuario = User.objects.get(pk=pk)
            usuario.set_password(nueva_password)
            usuario.must_change_password = True  
            usuario.save()
            FuncionarioService._imprimir_auditoria_mutacion("RESETEO DE PASSWORD", usuario.email, "⚠️ CREDENCIAL FORZADA")
            return True
        except User.DoesNotExist:
            return False

    @staticmethod
    def tramitar_baja_institucional(pk: uuid.UUID, operador_email: str) -> Tuple[bool, str]:
        try:
            usuario = User.objects.get(pk=pk)
            if usuario.is_manager or usuario.is_superuser:
                return False, "Restricción de Infraestructura: No se pueden alterar cuentas directivas desde el CRUD común."

            usuario.is_active = False  
            usuario.save()

            FuncionarioService._imprimir_auditoria_mutacion("LOCKDOWN / BAJA", usuario.email, "🛑 CUENTA CONGELADA", f"Operador: {operador_email}")
            return True, f"El funcionario {usuario.full_name} ha sido dado de baja de la plantilla activa."
        except User.DoesNotExist:
            return False, "El funcionario enfocado ya no existe."

    @staticmethod
    def _imprimir_auditoria_mutacion(operacion: str, email: str, estatus: str, detalle: str = ""):
        try:
            frame = sys._getframe(2)
            # 🟢 SANEADO COMPATIBILIDAD: os.path.basename extrae el archivo de forma limpia sin importar el OS
            invocado_desde = f"{os.path.basename(frame.f_code.co_filename)} -> {frame.f_code.co_name}()"
        except Exception:
            invocado_desde = "Origen Desconocido"

        print("\n👥 " + "⚡"*25)
        print(f"📡 AXENTRA OS ACCOUNTS SERVICE - TELEMETRÍA DE MUTACIÓN [{operacion}]")
        print(f"👤 Funcionario Afectado: {email}")
        print(f"🎬 Invocador Lógico:     {invocado_desde}")
        print(f"🚨 Estatus de Transacción: {estatus}")
        if detalle:
            print(f"ℹ️  Detalle Técnico:      {detalle}")
        print("-" * 52)
        print("📋 TRACEBACK DE ORQUESTACIÓN ATÓMICA DE PERSONAL:")
        for line in traceback.format_stack()[-4:-1]:
            print(f"   {line.strip()}")
        print("⚡"*26 + "\n")