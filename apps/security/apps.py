# apps/security/apps.py
from django.apps import AppConfig
from django.db.models.signals import post_migrate

def sincronizar_entorno_so_axentra(sender, **kwargs):
    """
    Motor de Aprovisionamiento e Integridad de Axentra OS.
    Se ejecuta automáticamente al finalizar 'python manage.py migrate'.
    Siembra aplicativos maestros, usuario raíz y matrices JSON de privilegios.
    """
    try:
        from django.contrib.auth import get_user_model
        from apps.security.models import AppModule, UserAppRole
        from apps.shared.apps_config import AppIdentifier
        from apps.shared.manifest_registry import AxentraOSRegistry
        
        User = get_user_model()
        
        print("\n⚙️  " + "="*76)
        print("🛰️  [AXENTRA OS] INICIANDO PROTOCOLO DE INTEGRIDAD POST-MIGRACIÓN")
        print("="*80)

        # =========================================================================
        # 📦 PASO 1: SEMBRADO DE MÓDULOS EN LA BASE DE DATOS
        # =========================================================================
        print("📋 1. Sincronizando catálogo de aplicativos...")
        modulos_maestros = AppIdentifier.get_choices()
        modulos_db = {}
        
        for slug, nombre in modulos_maestros:
            obj, creado = AppModule.objects.get_or_create(
                slug=slug,
                defaults={'name': nombre, 'is_active': True, 'description': f"Entorno operativo para {nombre}."}
            )
            modulos_db[slug] = obj
            if creado:
                print(f"   ↳ 🟢 Módulo faltante detectado y sembrado: '{slug}'")

        # =========================================================================
        # 👤 PASO 2: SEMBRADO DEL OPERADOR SUPREMO (SUPER-USER & MANAGER)
        # =========================================================================
        print("👥 2. Validando existencia del Operador Supremo...")
        email_root = "owner@g.com"
        
        # Buscamos o creamos al usuario de control utilizando el modelo unificado por Email
        user_root, user_creado = User.objects.get_or_create(
            email=email_root,
            defaults={
                'is_staff': True,
                'is_superuser': True,
                'is_active': True
            }
        )
        
        if user_creado:
            # Seteamos el password por defecto de forma segura encriptándolo en el backend
            user_root.set_password("owner123")
            # Forzamos que tenga el flag de manager para tus cortocircuitos de permisos
            if hasattr(user_root, 'is_manager'):
                setattr(user_root, 'is_manager', True)
            user_root.save()
            print(f"   ↳ 👑 Operador Supremo creado con éxito: [{email_root}] (Pass default: owner123)")
        else:
            # Si ya existía, nos aseguramos de que mantenga sus privilegios de bypass intactos
            modificado = False
            if not user_root.is_superuser:
                user_root.is_superuser = True
                modificado = True
            if hasattr(user_root, 'is_manager') and not getattr(user_root, 'is_manager', False):
                setattr(user_root, 'is_manager', True)
                modificado = True
            if modificado:
                user_root.save()
            print(f"   ↳ ✓ Operador Supremo verificado: [{email_root}] (Flags de bypass asegurados)")

        # =========================================================================
        # 🔑 PASO 3: CONTROL DE LLAVES JSON (USER_APP_ROLE MATRICES)
        # =========================================================================
        print("🔒 3. Re-calculando matriz de privilegios JSON para el Dueño...")
        roles_asignados = 0
        
        for slug, app_obj in modulos_db.items():
            llaves_manifiesto = ["has_access_module", "can_view_dashboard"]
            
            if slug == 'security':
                llaves_manifiesto.extend(["can_edit_matrix", "can_view_logs", "can_configure_tenant"])
            elif slug == 'accounts':
                llaves_manifiesto.extend(["can_view_all_users", "can_create_user", "can_edit_user", "can_delete_user"])
            elif slug == 'organigrama':
                llaves_manifiesto.extend(["can_model_structure", "can_edit_sedes", "can_toggle_nodos"])

            # 🟢 CORRECCIÓN: Ajustamos el string a 'owner' para no superar el max_length=20
            role_obj, role_creado = UserAppRole.objects.get_or_create(
                user=user_root,
                app=app_obj,
                defaults={
                    'role': 'owner',  # ◄── Cambiado de texto largo a clave limpia (5 caracteres)
                    'permissions_list': llaves_manifiesto,
                    'is_active': True
                }
            )
            
            if role_creado:
                roles_asignados += 1
            else:
                # Si la relación ya existía, unificamos las llaves sin duplicar strings
                role_obj.permissions_list = list(set(role_obj.permissions_list + llaves_manifiesto))
                role_obj.save()

        if roles_asignados > 0:
            print(f"   ↳ 🛠️  Aprovisionamiento exitoso: Se enlazaron {roles_asignados} celdas de rol al mapa JSON.")
        else:
            print("   ↳ 🛡️  Matriz inmutable: El operador ostenta todas las llaves JSON actualizadas.")

        print("="*80 + "\n")
            
    except Exception as e:
        print(f"   ↳ ⚠️  Protocolo pospuesto (Tablas del chasis o ORM ausentes en el hilo): {e}\n")


class SecurityConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.security'
    verbose_name = 'Seguridad y Permisos del Sistema'

    def ready(self):
        """Conectamos la señal en la carga del módulo de la aplicación."""
        post_migrate.connect(sincronizar_entorno_so_axentra, sender=self)