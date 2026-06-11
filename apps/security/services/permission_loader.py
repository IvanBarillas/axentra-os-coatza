# apps/security/services/permission_loader.py
import logging
import traceback
import sys
from importlib import import_module
from django.contrib.auth import get_user_model
from apps.security.models import UserAppRole

User = get_user_model()
logger = logging.getLogger(__name__)

def get_app_permissions(app_slug):
    """
    Busca en caliente el archivo permissions.py de forma inteligente:
    - Si pertenece al Core unificado, lee 'apps.security.permissions'.
    - Si es una App satélite independiente, lee su ruta nativa desacoplada.
    🟢 REGISTRO DINÁMICO: Incorpora la extracción de ROLE_WEIGHTS soberanos.
    """
    app_slug = str(app_slug).strip().lower()
    
    # Escalafón base del sistema operativo para proteger la retrocompatibilidad
    default_weights = {'owner': 100, 'admin': 80, 'editor': 60, 'reviewer': 40, 'viewer': 20}
    fallback_config = {'permissions': {}, 'roles': {}, 'weights': default_weights}
    
    # 🏛️ CATÁLOGO DE SUBMÓDULOS DEL NÚCLEO CORE (UNIFICADOS EN DISCO)
    CORE_SUBMODULES = ['security', 'accounts', 'organigrama']
    
    try:
        # 🟢 CONMUTADOR COMPUESTO DE INFRAESTRUCTURA:
        if app_slug in CORE_SUBMODULES:
            module_path = "apps.security.permissions"
        else:
            module_path = f"apps.{app_slug}.permissions"
            
        module = import_module(module_path)
        
        # Formateador CamelCase dinámico robusto (Ej: dynamic_forms -> DynamicForms)
        slug_procesado = "".join([word.capitalize() for word in app_slug.split("_")])
        clases_esperadas = [f"{slug_procesado}Permissions", "ModulePermissions"]
        
        for attr_name in clases_esperadas:
            if hasattr(module, attr_name):
                clase_permisos = getattr(module, attr_name)
                return {
                    'permissions': getattr(clase_permisos, 'PERMISSIONS', {}),
                    'roles': getattr(clase_permisos, 'ROLE_MAPPING', {}),
                    'weights': getattr(clase_permisos, 'ROLE_WEIGHTS', default_weights) # ◄── Extracción atómica
                }
                
        # Fallback si el archivo no usa clases y tiene las constantes sueltas
        return {
            'permissions': getattr(module, 'PERMISSIONS', {}),
            'roles': getattr(module, 'ROLE_MAPPING', {}),
            'weights': getattr(module, 'ROLE_WEIGHTS', default_weights)
        }
    except ModuleNotFoundError:
        logger.warning(f"⚠️ El módulo [{app_slug.upper()}] no cuenta con un manifiesto permissions.py activo en '{module_path}'.")
        return fallback_config
    except Exception as e:
        logger.error(f"❌ Error de introspección en el manifiesto de '{app_slug}' bajo la ruta '{module_path}': {str(e)}")
        return fallback_config


def generate_default_permissions(role, app_slug):
    """Extrae la lista de strings de permisos asignados a un rol específico de una app."""
    config = get_app_permissions(app_slug)
    return config['roles'].get(role, [])


def get_user_permissions_for_app(user, app_slug):
    """
    EL RADAR EN CALIENTE:
    Convierte el JSONField de la BD en banderas booleanas legibles por el HTML,
    las Vistas FBV y los Context Processors del sistema operativo.
    🟢 TELEMETRÍA AVANZADA: Imprime el escalafón jerárquico dinámico en consola.
    """
    app_slug = str(app_slug).strip().lower()
    
    # Bolsa de permisos por defecto (Compatibilidad unificada de llaves viejas y nuevas)
    permisos = {
        'has_access': False,
        'has_access_module': False,
        'llaves': [],
        'permissions_list': []
    }

    if not user or not user.is_authenticated:
        return permisos

    # Telemetría síncrona: Inspección del hilo de ejecución para pintar el origen exacto
    try:
        frame = sys._getframe(1)
        llamado_desde = f"{frame.f_code.co_filename.split('/')[-1]} -> {frame.f_code.co_name}()"
    except Exception:
        llamado_desde = "Origen Desconocido"

    # Jalamos la configuración perimetral de la app (incluyendo su mapa de pesos)
    config_app = get_app_permissions(app_slug)
    weights_map = config_app.get('weights', {})

    print("\n🕵️‍♂️ " + "🔍"*25)
    print(f"📡 RADAR EN CALIENTE AXENTRA OS: EVALUADOR DE PERMISOS [{app_slug.upper()}]")
    print(f"👤 Evaluando a:        {user.email}")
    print(f"🎬 Invocado desde:     {llamado_desde}")
    print(f"👑 Estado is_manager:  {getattr(user, 'is_manager', False)}")

    # =========================================================================
    # 👑 1. BYPASS MAESTRO (IS_MANAGER GLOBAL)
    # =========================================================================
    if getattr(user, 'is_manager', False):
        permisos['has_access'] = True
        permisos['has_access_module'] = True
        
        all_perms = set()
        for perms_list in config_app['roles'].values():
            all_perms.update(perms_list)
            
        lista_maestra = list(all_perms)
        if 'has_access_module' not in lista_maestra:
            lista_maestra.append('has_access_module')
            
        permisos['llaves'] = lista_maestra
        permisos['permissions_list'] = lista_maestra
        
        for permiso in lista_maestra:
            permisos[permiso] = True
            
        print("👑 RESULTADO: Acceso total concedido por regla jerárquica de Manager Supremo [Peso Absoluto: INF].")
        print("🔍"*26 + "\n")
        return permisos

    # =========================================================================
    # 🛡️ 2. FLUJO ORDINARIO SEGURO: Membresía física real en PostgreSQL
    # =========================================================================
    rol = UserAppRole.objects.filter(
        user=user,
        app__slug=app_slug,
        app__is_active=True,
        is_active=True
    ).first()

    print(f"📂 Registro UserAppRole en DB: {'🟢 ENCONTRADO Y ACTIVO' if rol else '❌ NO EXISTE O ESTÁ INACTIVO'}")
    
    if not rol:
        print(f"❌ RESULTADO: Usuario rechazado. Sin membresía activa en el nodo [{app_slug.upper()}].")
        print("-" * 52)
        print("📋 TRACEBACK DEL EVENTO DE SEGURIDAD:")
        for line in traceback.format_stack()[-3:-1]:
            print(f"   {line.strip()}")
        print("🔍"*26 + "\n")
        return permisos

    # Extraemos el peso dinámico del rol leyéndolo desde el manifiesto inyectado
    rol_str = str(rol.role).lower().strip()
    peso_detectado = weights_map.get(rol_str, 0)

    print(f"🎖️ Membresía (role) en DB:   [{rol.role.upper()}] (Peso de Autoridad Local: {peso_detectado})")
    print(f"📦 JSONField guardado en DB:  {rol.permissions_list}")

    # Activamos los flags maestros de entrada general perimetral
    permisos['has_access'] = True
    permisos['has_access_module'] = True
    
    # Extraemos el pool de llaves inyectadas directamente de la columna JSON
    lista_final_llaves = list(rol.permissions_list or [])
    if 'has_access_module' not in lista_final_llaves:
        lista_final_llaves.append('has_access_module')
        
    permisos['llaves'] = lista_final_llaves
    permisos['permissions_list'] = lista_final_llaves

    # Hidratamos el diccionario convirtiendo cada string del JSON en un booleano True en memoria
    for permiso in lista_final_llaves:
        permisos[permiso] = True
        
    # =========================================================================
    # ⚠️ 3. INYECCIÓN HEREDADA EXCLUSIVA PARA OWNERS
    # =========================================================================
    if rol.role in ['owner', 'OWNER']:
        print("⚠ DETECTOR: El usuario tiene rango de OWNER. Analizando inyección heredada...")
        owner_perms = config_app['roles'].get('owner', []) or config_app['roles'].get('OWNER', [])
        
        for p in owner_perms:
            permisos[p] = True
            if p not in permisos['permissions_list']:
                permisos['permissions_list'].append(p)
                permisos['llaves'].append(p)

    llaves_finales_activas = [k for k, v in permisos.items() if v is True and k not in ['has_access', 'has_access_module', 'is_manager']]
    print(f"🚀 LLAVES FINALES ENTREGADAS AL CONTEXTO EN TIEMPO REAL: {llaves_finales_activas}")
    print("🕵️‍♂️ " + "🔍"*25 + "\n")

    return permisos