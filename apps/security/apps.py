# apps/security/apps.py
from django.apps import AppConfig
from django.db.models.signals import post_migrate

def sincronizar_entorno_so_axentra(sender, **kwargs):
    """
    Motor de Aprovisionamiento e Integridad de Axentra OS.
    Se ejecuta automáticamente al finalizar 'python manage.py migrate'.
    Siembra los módulos lógicos, el usuario raíz y las membresías JSON independientes
    para garantizar el desacoplamiento total de cada aplicación satélite.
    """
    try:
        from django.contrib.auth import get_user_model
        from apps.security.models import AppModule, UserAppRole
        
        # Importación del Manifiesto Maestro de Gobernanza unificado
        from apps.security.permissions import SecurityPermissions
        
        User = get_user_model()
        
        print("\n⚙️  " + "="*76)
        print("🛰️  [AXENTRA OS] INICIANDO PROTOCOLO DE INTEGRIDAD POST-MIGRACIÓN")
        print("="*80)

        # =========================================================================
        # 👤 PASO 1: SEMBRADO DEL OPERADOR SUPREMO (SUPER-USER & MANAGER)
        # =========================================================================
        print("👥 1. Validando existencia del Operador Supremo...")
        email_root = "owner@g.com"
        
        user_root, user_creado = User.objects.get_or_create(
            email=email_root,
            defaults={
                'is_staff': True,
                'is_superuser': True,
                'is_active': True
            }
        )
        
        if user_creado:
            user_root.set_password("owner123")
            if hasattr(user_root, 'is_manager'):
                setattr(user_root, 'is_manager', True)
            user_root.save()
            print(f"   ↳ 👑 Operador Supremo creado con éxito: [{email_root}] (Pass default: owner123)")
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
        # 🔑 PASO 2: CONTROL DESACOPLADO DE LLAVES JSON POR APLICACIÓN
        # =========================================================================
        print("🔒 2. Re-calculando matrices de privilegios independientes por App...")
        
        # Leemos el catálogo completo definido físicamente para el 'owner'
        llaves_maestras_owner = SecurityPermissions.ROLE_MAPPING.get('owner', [])
        
        # Identificamos los prefijos/módulos únicos presentes en las llaves usando un set dinámico
        # Esto extraerá automáticamente de los strings: ['security', 'accounts', 'organigrama']
        modulos_detectados = list(set([permiso.split('__')[0] for permiso in llaves_maestras_owner if '__' in permiso]))
        
        roles_modificados = 0
        total_llaves_sembradas = 0
        
        print("-" * 80)
        for slug in modulos_detectados:
            # 1. Aseguramos de manera independiente la existencia física de la App en la tabla AppModule
            # Esto desacopla las apps y les da su propio id e historial autonómo en la BD
            nombre_legible = slug.replace('_', ' ').capitalize()
            app_obj, creado_app = AppModule.objects.get_or_create(
                slug=slug,
                defaults={
                    'name': f"Satélite {nombre_legible}", 
                    'is_active': True, 
                    'description': f"Módulo desacoplado para la gestión de {nombre_legible}."
                }
            )
            
            # 2. Filtramos de forma estricta las llaves que le pertenecen únicamente a este módulo
            llaves_filtradas_por_app = [
                permiso for permiso in llaves_maestras_owner 
                if permiso.startswith(f"{slug}__")
            ]
            
            total_llaves_sembradas += len(llaves_filtradas_por_app)

            # 3. Intentamos buscar o crear la membresía relacional en la base de datos
            role_obj, creado_rol = UserAppRole.objects.get_or_create(
                user=user_root,
                app=app_obj,
                defaults={
                    'role': 'owner', # Cumple con el max_length=20 de tu Postgres
                    'permissions_list': llaves_filtradas_por_app,
                    'is_active': True
                }
            )
            
            if creado_rol:
                print(f"   🟢 Membresía Sembrada -> App: [{slug:<12}] | Inyectadas: {len(llaves_filtradas_por_app)} llaves JSON.")
                roles_modificados += 1
            else:
                # RE-INJECTOR LAYER DESACOPLADO: Si ya existía la membresía, forzamos la actualización si cambiaste el manifiesto
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
            print(f"   🚀 Aprovisionamiento exitoso: {total_llaves_sembradas} llaves mapeadas en {len(modulos_detectados)} registros desacoplados.")
        else:
            print(f"   ✓ Integridad Perfecta: Las {total_llaves_sembradas} llaves JSON de la BD coinciden con tu Manifiesto Maestro.")

        print("="*80 + "\n")
            
    except Exception as e:
        print(f"   ↳ ⚠️  Protocolo pospuesto (Excepción en el hilo transaccional): {e}\n")


class SecurityConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.security'
    verbose_name = 'Seguridad y Permisos del Sistema'

    def ready(self):
        """Conectamos la señal en la carga del módulo de la aplicación."""
        post_migrate.connect(sincronizar_entorno_so_axentra, sender=self)