# apps/security/utils/hierarchy_enforcer.py
from django.shortcuts import get_object_or_404
from apps.security.models import UserAppRole

class HierarchyEnforcer:
    
    @staticmethod
    def validar_autoridad_operador(request, target_user, app_module, nuevo_rol_slug, weights_map) -> bool:
        """
        🛡️ GUARDIÁN DE ESCALAFÓN DE AUTORIDAD:
        Determina si un operador tiene permitido alterar a un usuario o asignar un nuevo rol
        basándose en pesos jerárquicos y banderas globales del sistema.
        
        Devuelve True si la acción está permitida; False si es una violación de jerarquía.
        """
        # 👑 REGLA MAESTRA SUPREMA: Si es Mánager Global o SuperAdmin Root, ignora el escalafón local.
        is_manager_global = getattr(request.user, 'is_manager', False) or (
            hasattr(request.user, 'axentra_profile') and request.user.axentra_profile.is_root_admin
        )
        if is_manager_global:
            return True

        # 🪐 Flujo estándar de validación por pesos locales de la App
        rol_operador_obj = UserAppRole.objects.filter(user=request.user, app=app_module, is_active=True).first()
        rol_operador_str = rol_operador_obj.role if rol_operador_obj else 'viewer'
        
        rol_actual_target_obj = UserAppRole.objects.filter(user=target_user, app=app_module).first()
        rol_actual_target_str = rol_actual_target_obj.role if rol_actual_target_obj else 'viewer'

        # Extracción analítica de pesos desde el mapa dinámico de la aplicación
        peso_operador = weights_map.get(str(rol_operador_str).lower().strip(), 0)
        peso_actual_target = weights_map.get(str(rol_actual_target_str).lower().strip(), 0)
        peso_nuevo_target = weights_map.get(str(nuevo_rol_slug).lower().strip(), 0)

        # 🚫 REGLA DE ORO DEFENSIVA:
        # El operador NO puede alterar a alguien de su mismo peso o superior.
        # El operador NO puede promover a alguien a un peso igual o superior al suyo.
        if peso_actual_target >= peso_operador or peso_nuevo_target >= peso_operador:
            return False

        return True