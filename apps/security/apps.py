# apps/security/apps.py
from django.apps import AppConfig
from django.db.models.signals import post_migrate

def sincronizar_entorno_so_axentra(sender, **kwargs):
    """
    Motor de Aprovisionamiento e Integridad de Axentra OS.
    Se ejecuta automáticamente al finalizar 'python manage.py migrate'.
    Siembra los módulos lógicos, el usuario raíz y las membresías JSON independientes
    descubiertas dinámicamente mediante el Registry de Gobernanza.
    """
    try:
        from django.contrib.auth import get_user_model
        from apps.security.models import AppModule, UserAppRole
        from apps.shared.manifest_registry import AxentraOSRegistry
        
        User = get_user_model()
        
        print("\n⚙️  " + "="*76)
        print("🛰️  [AXENTRA OS] INICIANDO PROTOCOLO DE INTEGRIDAD POST-MIGRACIÓN")
        print("="*80)

        # =========================================================================
        # 👤 PASO 1: SEMBRADO DEL OPERADOR SUPREMO
        # =========================================================================
        print("👥 1. Validando existencia del Operador Supremo...")
        email_root = "owner@axentra.com.mx"
        
        user_root, user_creado = User.objects.get_or_create(
            email=email_root,
            defaults={'is_staff': True, 'is_superuser': True, 'is_active': True}
        )
        
        if user_creado:
            user_root.set_password("1q2w3e4r5t%")
            if hasattr(user_root, 'is_manager'):
                setattr(user_root, 'is_manager', True)
            user_root.save()
            print(f"   ↳ 👑 Operador Supremo creado con éxito: [{email_root}] (Pass default: 1q2w3e4r5t%)")
        else:
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
        # 🔑 PASO 2: CONTROL DESACOPLADO BASADO EN REFLEXIÓN DINÁMICA
        # =========================================================================
        print("🔒 2. Re-calculando matrices de privilegios independientes por App...")
        
        # 🟢 Descubrimiento ciego de manifiestos a través de la topología del disco duro
        manifiestos_detectados = AxentraOSRegistry.get_all_manifests()
        
        roles_modificados = 0
        total_llaves_sembradas = 0
        
        print("-" * 80)
        for slug, clase_manifiesto in manifiestos_detectados.items():
            # 1. Aseguramos la existencia física del aplicativo en la tabla AppModule
            nombre_legible = slug.replace('_', ' ').capitalize()
            app_obj, creado_app = AppModule.objects.get_or_create(
                slug=slug,
                defaults={
                    'name': f"Satélite {nombre_legible}", 
                    'is_active': True, 
                    'description': f"Módulo desacoplado para la gestión de {nombre_legible}."
                }
            )
            
            # 2. Extraemos el mapeo del rol 'owner' declarado en SU PROPIO archivo/clase independiente
            llaves_filtradas_por_app = clase_manifiesto.ROLE_MAPPING.get('owner', [])
            total_llaves_sembradas += len(llaves_filtradas_por_app)

            # 3. Insertamos o actualizamos en Postgres de manera atómica
            role_obj, creado_rol = UserAppRole.objects.get_or_create(
                user=user_root,
                app=app_obj,
                defaults={
                    'role': 'owner',
                    'permissions_list': llaves_filtradas_por_app,
                    'is_active': True
                }
            )
            
            if creado_rol:
                print(f"   🟢 Membresía Sembrada -> App: [{slug:<12}] | Inyectadas: {len(llaves_filtradas_por_app)} llaves JSON.")
                roles_modificados += 1
            else:
                # RE-INJECTOR LAYER: Si hubo cambios en su clase permissions.py, actualiza Postgres en caliente
                if set(role_obj.permissions_list) != set(llaves_filtradas_por_app):
                    role_obj.permissions_list = llaves_filtradas_por_app
                    role_obj.role = 'owner'
                    role_obj.save()
                    print(f"   🛠️  Membresía Sincronizada -> App: [{slug:<12}] | Re-inyectadas: {len(llaves_filtradas_por_app)} llaves JSON.")
                    roles_modificados += 1
                else:
                    print(f"   🛡️  Membresía Verificada -> App: [{slug:<12}] | Contiene: {len(role_obj.permissions_list)} llaves inmutables.")

        print("-" * 80)
        if roles_modificados > 0:
            print(f"   🚀 Aprovisionamiento exitoso: {total_llaves_sembradas} llaves mapeadas en registros desacoplados.")
        else:
            print(f"   ✓ Integridad Perfecta: Las {total_llaves_sembradas} llaves JSON de la BD coinciden con tus Manifiestos Maestros.")

        print("="*80 + "\n")
            
    except Exception as e:
        print(f"   ↳ ⚠️  Protocolo pospuesto (Excepción en el hilo transaccional): {e}\n")


class SecurityConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.security'
    verbose_name = 'Seguridad y Permisos del Sistema'

    def ready(self):
        post_migrate.connect(sincronizar_entorno_so_axentra, sender=self)