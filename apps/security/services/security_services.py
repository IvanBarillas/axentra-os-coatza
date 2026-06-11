# apps/security/services/security_services.py
import sys
import logging
import traceback
from typing import List, Dict, Any
from django.db import transaction
from django.contrib.auth import get_user_model
from apps.security.models import UserAppRole, AppModule

# 🛰️ UNIFICACIÓN ESTRUCTURAL: Centraliza la carga de manifiestos dinámicos evitando colisiones en RAM
from apps.security.services.permission_loader import get_app_permissions

User = get_user_model()
logger = logging.getLogger(__name__)


class PermissionService:
    """Lógica transaccional unificada para la inyección, depuración y grabación de privilegios JSON."""

    @staticmethod
    def authorize_new_user_entry(app_module: AppModule, user_id: str, rol_a_inyectar: str = 'viewer') -> bool:
        """
        Incorpora de forma limpia a un nuevo funcionario dentro de la aduana de un aplicativo,
        otorgándole su rol base bajo la filosofía Zero Trust (en ceros, sin permisos fantasma).
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

                # 🟢 ZERO TRUST ENFORCEMENT: Si es 'owner' se lleva el catálogo total dinámico.
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
            logger.info(f"🟢 CIBERSEGURIDAD: Funcionario {target_user.email} sembrado en Módulo [{app_module.slug.upper()}] bajo política Zero Trust.")
            return True
        except Exception as e:
            logger.error(f"❌ FALLO TRANSACCIONAL (authorize_new_user_entry): {str(e)}")
            return False

    @staticmethod
    def save_matrix_permissions(target_user: User, app_module: AppModule, nuevo_rol: str, llaves_encendidas: List[str]) -> bool:
        """
        Compila e inyecta el override JSONField ejecutando un saneamiento estricto:
        Elimina de forma obligatoria cualquier llave guardada que no exista dentro 
        del manifiesto permissions.py activo de la aplicación correspondiente.
        """
        try:
            frame = sys._getframe(1)
            invocado_desde = f"{frame.f_code.co_filename.split('/')[-1]} -> {frame.f_code.co_name}()"
        except Exception:
            invocado_desde = "Origen Desconocido"

        # =========================================================================
        # 🚨 SISTEMA DE DEPURACIÓN EN VIVO (ENTRADA DEL POST)
        # =========================================================================
        print("\n📥 " + "⚡"*25)
        print("🛠️  DETECTOR SERVICE: INICIO DE PERSISTENCIA EN MATRIZ UNIVERSAL")
        print(f"👤 Funcionario Destino:       {target_user.email}")
        print(f"🎬 Controlador Invocador:     {invocado_desde}")
        print(f"📦 Módulo Base de Datos:      [{app_module.slug.upper()}]")
        print(f"📥 Rol Base recibido:         '{nuevo_rol}'")
        print(f"📥 Llaves crudas del POST:    {llaves_encendidas}")

        if target_user.is_manager or target_user.is_superuser:
            print("🛡️  DETECTOR: El usuario objetivo es Manager/Superuser global. Operación ABORTADA.")
            print("⚡"*26 + "\n")
            return False

        rol_limpio = str(nuevo_rol).lower().strip()
        lista_final_json = list(set([str(llave).strip() for llave in llaves_encendidas if llave]))

        # =========================================================================
        # 🛡️ FILTRO DE CONGRUENCIA MULTI-APP: CONSUME EL CARGADOR INTELIGENTE
        # =========================================================================
        llaves_validas_manifiesto = set()
        config_app = get_app_permissions(app_module.slug)
        llaves_validas_manifiesto.update(config_app.get('permissions', {}).keys())
        
        if llaves_validas_manifiesto:
            llaves_filtradas = [llave for llave in lista_final_json if llave in llaves_validas_manifiesto]
            llaves_descartadas = [llave for llave in lista_final_json if llave not in llaves_validas_manifiesto]
            
            if llaves_descartadas:
                print(f"🗑️  AUDITORÍA DE SEGURIDAD: Eliminando llaves basura del JSON: {llaves_descartadas}")
            
            lista_final_json = llaves_filtradas

        # =========================================================================
        # 🎯 BLINDAJE INSTITUCIONAL DE RANGOS ALTOS (SHIELD INJECTOR)
        # =========================================================================
        if rol_limpio == 'owner':
            for llave in ['can_assign_roles', 'can_configure_tenant', 'can_view_matrix', 'can_view_analytics']:
                if llave in llaves_validas_manifiesto and llave not in lista_final_json:
                    lista_final_json.append(llave)
            print("🛡️  SHIELD INJECTOR: Sincronizadas las llaves legítimas del perfil OWNER.")
            
        elif rol_limpio == 'admin':
            for llave in ['can_view_matrix', 'can_view_analytics']:
                if llave in llaves_validas_manifiesto and llave not in lista_final_json:
                    lista_final_json.append(llave)
            print("🛡️  SHIELD INJECTOR: Sincronizadas las llaves legítimas del perfil ADMIN.")

        # Garantizamos la llave de acceso base obligatoria del ecosistema Axentra
        if 'has_access_module' not in lista_final_json:
            lista_final_json.append('has_access_module')

        # =========================================================================
        # 🚀 PERSISTENCIA Y MUTACIÓN FÍSICA TRANSACCIONAL EN POSTGRESQL
        # =========================================================================
        try:
            with transaction.atomic():
                instancia_rol, created = UserAppRole.objects.update_or_create(
                    user=target_user,
                    app=app_module,
                    defaults={
                        'role': rol_limpio,
                        'permissions_list': lista_final_json,
                        'is_active': True
                    }
                )

            # =========================================================================
            # 🚨 CONTROL DE VERIFICACIÓN POST-GUARDADO (RETORNO DE LA DB)
            # =========================================================================
            print("\n💾 " + "✅"*25)
            print("📊 CONFIRMACIÓN DE LA BASE DE DATOS (POSTGRES RETORNO):")
            print(f"¿Se creó un registro nuevo?: {'SÍ 🆕' if created else 'NO (Actualización de registro existente 🔄)'}")
            print(f"ID de la Membresía afectada: {instancia_rol.id}")
            print(f"Rol final guardado:          [{instancia_rol.role}]")
            print(f"JSON final guardado:         {instancia_rol.permissions_list}")
            print("-" * 52)
            print("📋 TRACEBACK DE MUTACIÓN TRANSACCIONAL ATÓMICA:")
            for line in traceback.format_stack()[-3:-1]:
                print(f"   {line.strip()}")
            print("✅"*26 + "\n")
            
            return True
        except Exception as e:
            logger.error(f"❌ FALLO TRANSACCIONAL (save_matrix_permissions): {str(e)}")
            return False