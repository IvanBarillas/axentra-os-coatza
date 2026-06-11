# apps/security/services/permission_services.py
import logging
import sys
import traceback
from importlib import import_module
from django.db import transaction
from django.contrib.auth import get_user_model
from apps.security.models import UserAppRole, AppModule, SecurityAuditLog

User = get_user_model()
logger = logging.getLogger(__name__)

class PermissionService:
    """🔒 TRANSACT_SECURITY CORE ENGINE: Compila y sanea overrides JSONField contra el manifiesto."""

    @classmethod
    @transaction.atomic
    def authorize_new_user_entry(cls, app_module: AppModule, user_id: str) -> bool:
        try:
            target_user = User.objects.get(id=user_id)
            if target_user.is_manager or target_user.is_superuser:
                return False
        except User.DoesNotExist:
            return False

        UserAppRole.objects.update_or_create(
            user=target_user,
            app=app_module,
            defaults={
                'role': 'viewer',  
                'permissions_list': ['has_access_module'],  
                'is_active': True
            }
        )
        return True

    @classmethod
    @transaction.atomic
    def save_matrix_permissions(cls, target_user: User, app_module: AppModule, nuevo_rol: str, llaves_encendidas: list) -> bool:
        """Sanea el POST purgando llaves inexistentes en el manifiesto permissions.py activo."""
        try:
            frame = sys._getframe(1)
            invocado_desde = f"{frame.f_code.co_filename.split('/')[-1]} -> {frame.f_code.co_name}()"
        except Exception:
            invocado_desde = "Origen Desconocido"

        print("\n📥 " + "⚡"*25)
        print("🛠️  DETECTOR AXENTRA OS: SANEAMIENTO Y COMPILACIÓN DE MATRIZ")
        print(f"👤 Servidor Destino:        {target_user.email}")
        print(f"🎬 Invocador Lógico:        {invocado_desde}")
        print(f"📦 Nodo Destino:            [{app_module.slug.upper()}]")
        print(f"📥 Pool Crudo Recibido:     {llaves_encendidas}")

        if target_user.is_manager or target_user.is_superuser:
            print("🛡️  ABORTADO: Cuenta con jerarquía inmune global (Bypass).")
            print("⚡"*26 + "\n")
            return False

        rol_limpio = str(nuevo_rol).lower().strip()
        lista_final_json = list(set([str(llave).strip() for llave in llaves_encendidas if llave]))

        # Introspección polimórfica perimetral
        llaves_validas_manifiesto = set()
        try:
            module = import_module(f'apps.{app_module.slug}.permissions')
            slug_procesado = "".join([word.capitalize() for word in app_module.slug.split("_")])
            clases_esperadas = [f"{slug_procesado}Permissions", "ModulePermissions"]
            
            for attr_name in clases_esperadas:
                if hasattr(module, attr_name):
                    clase_permisos = getattr(module, attr_name)
                    llaves_validas_manifiesto.update(getattr(clase_permisos, 'PERMISSIONS', {}).keys())
            
            if llaves_validas_manifiesto:
                llaves_filtradas = [llave for llave in lista_final_json if llave in llaves_validas_manifiesto]
                llaves_descartadas = [llave for llave in lista_final_json if llave not in llaves_validas_manifiesto]
                if llaves_descartadas:
                    print(f"🗑️  SECURITY FILTER: Purgadas llaves basura inexistentes: {llaves_descartadas}")
                lista_final_json = llaves_filtradas
        except Exception as e:
            print(f"⚠️  Alerta de Introspección: Omitida depuración por manifiesto faltante: {str(e)}")

        # Shield Injector de roles altos legítimos
        if rol_limpio == 'owner':
            llaves_maestras_owner = ['can_assign_roles', 'can_configure_tenant', 'can_manage_users']
            for llave in llaves_maestras_owner:
                if llave in llaves_validas_manifiesto and llave not in lista_final_json:
                    lista_final_json.append(llave)
        elif rol_limpio == 'admin':
            llaves_maestras_admin = ['can_assign_roles', 'can_configure_tenant']
            for llave in llaves_maestras_admin:
                if llave in llaves_validas_manifiesto and llave not in lista_final_json:
                    lista_final_json.append(llave)

        if 'has_access_module' not in lista_final_json:
            lista_final_json.append('has_access_module')

        # Mutación física atómica
        instancia_rol, created = UserAppRole.objects.update_or_create(
            user=target_user, app=app_module,
            defaults={'role': rol_limpio, 'permissions_list': lista_final_json, 'is_active': True}
        )

        accion_log = f"Mutación de Privilegios: Rol asignado [{rol_limpio.upper()}]" if not created else f"Inyección Inicial: Otorgado Rol [{rol_limpio.upper()}]"
        
        # Buffer circular Inmutable (Audit Log)
        SecurityAuditLog.objects.create(
            operator_user=target_user,
            level_status=SecurityAuditLog.Levels.SUCCESS,
            action_name=accion_log,
            target_scope=f"App: {app_module.slug} | Funcionario: {target_user.email}"
        )

        print("\n💾 " + "✅"*25)
        print("📊 RESPUESTA DE RETORNO (POSTGRESQL):")
        print(f"Membresía ID: {instancia_rol.id} | Lista Guardada Físicamente: {instancia_rol.permissions_list}")
        print("✅"*26 + "\n")
        return True

    @classmethod
    @transaction.atomic
    def revoke_all_app_access(cls, target_user, app_module: AppModule) -> bool:
        rol_usuario = UserAppRole.objects.filter(user=target_user, app=app_module, is_active=True).first()
        if rol_usuario:
            rol_usuario.is_active = False
            rol_usuario.save()

            SecurityAuditLog.objects.create(
                operator_user=target_user,
                level_status=SecurityAuditLog.Levels.CRITICAL,
                action_name="Revocación de Credenciales: Membresía Inactivada",
                target_scope=f"App: {app_module.slug} | Funcionario: {target_user.email}"
            )
            return True
        return False