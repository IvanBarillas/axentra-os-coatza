# apps/security/services/security_services.py
import logging
from typing import List
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model

from apps.security.models import AppModule, UserAppRole

User = get_user_model()
logger = logging.getLogger(__name__)

class PermissionService:
    """Gobernador Mutacional de privilegios y llaves JSON en RAM/PostgreSQL."""

    @staticmethod
    def save_matrix_permissions(target_user: User, app_module: AppModule, nuevo_rol: str, llaves_encendidas: List[str]) -> bool:
        """
        Re-graba de forma atómica el rol jerárquico y el payload de privilegios finos 
        para un funcionario dentro de un aplicativo específico.
        """
        try:
            with transaction.atomic():
                # 🟢 SINCRO ORM: Buscamos la membresía usando el related_name premium 'roles'
                user_role_instancia, created = UserAppRole.objects.get_or_create(
                    user=target_user,
                    app=app_module,
                    defaults={'role': nuevo_rol, 'is_active': True}
                )

                # Si ya existía, mutamos sus metadatos
                if not created:
                    user_role_instancia.role = nuevo_rol
                    user_role_instancia.is_active = True

                # Saneamos y grabamos el arreglo nativo de texto en el campo JSON de Django
                user_role_instancia.permissions_list = [str(perm).strip() for perm in llaves_encendidas if perm]
                user_role_instancia.save()

            logger.info(f"🔒 CIBERSEGURIDAD: Llaves JSON actualizadas para {target_user.email} en App [{app_module.slug}].")
            return True
        except Exception as e:
            logger.error(f"❌ FALLO TRANSACCIONAL (save_matrix_permissions): {str(e)}")
            return False

    @staticmethod
    def authorize_new_user_entry(app_module: AppModule, user_id: str) -> bool:
        """
        Siembra o incorpora de forma limpia a un nuevo funcionario público dentro de la aduana 
        de un aplicativo satélite, otorgándole un rol base de espectador (viewer).
        """
        try:
            target_user = get_object_or_404(User, id=user_id)
            
            with transaction.atomic():
                # 🟢 SINCRO ORM: Evitamos duplicados usando get_or_create sobre la matriz 'roles'
                user_role_instancia, created = UserAppRole.objects.get_or_create(
                    user=target_user,
                    app=app_module,
                    defaults={
                        'role': 'viewer', 
                        'permissions_list': ['has_access_module'], 
                        'is_active': True
                    }
                )
                
                # Si la llave estaba congelada o inactiva, la re-activamos en el acto
                if not created and not user_role_instancia.is_active:
                    user_role_instancia.is_active = True
                    user_role_instancia.save()

            logger.info(f"🟢 CIBERSEGURIDAD: Funcionario {target_user.email} incorporado con éxito a App [{app_module.slug}].")
            return True
        except Exception as e:
            logger.error(f"❌ FALLO TRANSACCIONAL (authorize_new_user_entry): {str(e)}")
            return False