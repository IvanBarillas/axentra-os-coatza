# apps/security/selectors/permission_selectors.py
import importlib
import logging
import traceback  # ◄── Bloque Forense de Extracción de Errores Críticos
from typing import List, Optional
import uuid
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from apps.security.dtos.security_dtos import RoleReadOnlyDTO
from apps.security.models import AppModule, UserAppRole
from apps.security.services.permission_loader import get_app_permissions
from django.db import models as db_models

from apps.shared.apps_config import AppIdentifier

User = get_user_model()
logger = logging.getLogger(__name__)

class PermissionSelectors:
    """Control analítico perimetral de credenciales y gobernanza de la Matriz JSON."""
    
    @staticmethod
    def get_app_metadata_or_404(app_slug: str) -> AppModule:
        return get_object_or_404(AppModule, slug=app_slug, is_active=True)

    @staticmethod
    def get_app_config_modules(app_slug: str):
        """Introspección dinámica: Lee los diccionarios PERMISSIONS y ROLE_MAPPING aislados."""
        fallback_permissions = {'has_access_module': 'Permite el acceso general al módulo.'}
        fallback_mapping = {'viewer': ['has_access_module']}

        try:
            modulo_permisos = importlib.import_module(f"apps.{app_slug}.permissions")
            clase_permisos = None
            for attr_name in dir(modulo_permisos):
                if attr_name.endswith("Permissions"):
                    clase_permisos = getattr(modulo_permisos, attr_name)
                    break
            
            if clase_permisos:
                permissions = getattr(clase_permisos, "PERMISSIONS", fallback_permissions)
                role_mapping = getattr(clase_permisos, "ROLE_MAPPING", fallback_mapping)
            else:
                permissions = fallback_permissions
                role_mapping = fallback_mapping
        except ModuleNotFoundError:
            permissions = fallback_permissions
            role_mapping = fallback_mapping
        except Exception as e:
            logger.error(f"❌ Error crítico de introspección en la app '{app_slug}': {str(e)}\n{traceback.format_exc()}")
            permissions = fallback_permissions
            role_mapping = fallback_mapping

        return permissions, role_mapping

    @staticmethod
    def _mapear_rol_a_dto(obj: UserAppRole) -> RoleReadOnlyDTO:
        return RoleReadOnlyDTO(
            id=obj.id, user_id=obj.user.id, user_email=obj.user.email,
            app_id=obj.app.id, app_name=obj.app.name, app_slug=obj.app.slug,
            role=obj.role, role_display=obj.get_role_display(),
            permissions_list=obj.permissions_list, is_active=obj.is_active
        )

    @classmethod
    def obtener_roles_por_usuario(cls, user_id: uuid.UUID) -> List[RoleReadOnlyDTO]:
        try:
            queryset = UserAppRole.objects.select_related('user', 'app').filter(user_id=user_id, is_active=True)
            return [cls._mapear_rol_a_dto(rol) for rol in queryset]
        except Exception as e:
            logger.error(f"❌ Error en obtener_roles_por_usuario: {str(e)}\n{traceback.format_exc()}")
            return []

    @classmethod
    def get_secured_matrix_data(
        cls,
        app_module: AppModule,
        user_focus_id: Optional[str] = None,
        request_user: Optional[User] = None,
        is_manager_global: bool = False,
    ) -> dict:
        """
        Extrae, cruza y computa la matriz granular de permisos por aplicación.

        Reglas:
        - Los roles salen del manifiesto de permisos de cada app.
        - Los pesos salen del ROLE_WEIGHTS de cada app.
        - is_manager/root puede ver e inyectar owner.
        - owner de app puede gobernar usuarios de su app, pero no modificar owners.
        - Los usuarios ya asignados se administran desde el panel derecho, no se reinyectan.
        """

        try:
            roles_activos = (
                UserAppRole.objects
                .filter(
                    app=app_module,
                    is_deleted=False,
                )
                .select_related("user")
                .order_by(
                    "user__first_name",
                    "user__last_name",
                    "user__email",
                )
            )

            config_app = get_app_permissions(app_module.slug)

            catalogo_permisos = config_app.get("permissions", {}) or {}
            role_mapping = config_app.get("roles", {}) or {}
            weights_map = config_app.get("weights", {}) or {}

            if not role_mapping:
                role_mapping = {
                    "owner": list(catalogo_permisos.keys()),
                    "viewer": ["has_access_module"],
                }

            operador_es_owner_de_app = False
            rol_operador_obj = None
            rol_operador_str = "viewer"
            peso_operador = 0

            if request_user and request_user.is_authenticated:
                rol_operador_obj = (
                    UserAppRole.objects
                    .filter(
                        user=request_user,
                        app=app_module,
                        is_active=True,
                        is_deleted=False,
                    )
                    .first()
                )

                if rol_operador_obj:
                    rol_operador_str = str(rol_operador_obj.role).lower().strip()
                    operador_es_owner_de_app = rol_operador_str == "owner"
                    peso_operador = weights_map.get(rol_operador_str, 0)

            personal_list = []
            usuario_enfocado_data = None

            for r in roles_activos:
                rol_actual = str(r.role or "viewer").lower().strip()

                es_el_seleccionado = str(r.user.id) == str(user_focus_id)

                personal_list.append({
                    "usuario": r.user,
                    "rol_actual": rol_actual,
                    "rol_label": rol_actual.replace("_", " ").title(),
                    "es_el_seleccionado": es_el_seleccionado,
                    "is_suspended": not r.is_active,
                })

                if not es_el_seleccionado:
                    continue

                permisos_raw = r.permissions_list or []

                permisos_usuario_lista = [
                    permiso
                    for permiso in permisos_raw
                    if permiso in catalogo_permisos
                ]

                if rol_actual == "owner":
                    permisos_permitidos_por_rol = list(catalogo_permisos.keys())
                else:
                    permisos_permitidos_por_rol = list(
                        role_mapping.get(
                            rol_actual,
                            ["has_access_module"],
                        )
                    )

                if "has_access_module" not in permisos_permitidos_por_rol:
                    permisos_permitidos_por_rol.append("has_access_module")

                payload_llaves = []

                for code, desc in catalogo_permisos.items():
                    if code not in permisos_permitidos_por_rol:
                        continue

                    obligatorio_by_role = (
                        code == "has_access_module"
                        or rol_actual == "owner"
                    )

                    payload_llaves.append({
                        "llave": code,
                        "descripcion": desc,
                        "concedido_total": (
                            code in permisos_usuario_lista
                            or obligatorio_by_role
                        ),
                        "obligatorio_by_role": obligatorio_by_role,
                    })

                bloqueo_visual = False
                motivo_bloqueo = "none"

                if not is_manager_global and request_user:
                    peso_destino = weights_map.get(rol_actual, 0)

                    if str(r.user.id) == str(request_user.id):
                        bloqueo_visual = True
                        motivo_bloqueo = "auto_lock"

                    elif rol_actual == "owner":
                        bloqueo_visual = True
                        motivo_bloqueo = "owner_lock"

                    elif peso_destino >= peso_operador:
                        bloqueo_visual = True
                        motivo_bloqueo = "weight_lock"

                if not r.is_active:
                    bloqueo_visual = True
                    motivo_bloqueo = "suspended_lock"

                usuario_enfocado_data = {
                    "usuario": r.user,
                    "rol_actual": rol_actual,
                    "rol_label": rol_actual.replace("_", " ").title(),
                    "permisos": payload_llaves,
                    "bloqueo_visual": bloqueo_visual,
                    "motivo_bloqueo": motivo_bloqueo,
                    "is_suspended": not r.is_active,
                    "peso_destino": weights_map.get(rol_actual, 0),
                    "peso_operador": peso_operador,
                }

            puede_gobernar_app = (
                is_manager_global
                or operador_es_owner_de_app
            )

            if puede_gobernar_app:
                usuarios_ya_asignados = (
                    UserAppRole.objects
                    .filter(
                        app=app_module,
                        is_deleted=False,
                    )
                    .values_list("user_id", flat=True)
                )

                usuarios_potenciales = (
                    User.objects
                    .filter(
                        is_active=True,
                        is_deleted=False,
                        is_superuser=False,
                        is_manager=False,
                    )
                    .exclude(id__in=usuarios_ya_asignados)
                    .order_by(
                        "first_name",
                        "last_name",
                        "email",
                    )
                )

                mostrar_buscador = True
            else:
                usuarios_potenciales = User.objects.none()
                mostrar_buscador = False

            roles_grilla = []

            for rol_key in role_mapping.keys():
                rol_limpio = str(rol_key).lower().strip()

                if rol_limpio == "owner" and not is_manager_global:
                    continue

                roles_grilla.append((
                    rol_limpio,
                    rol_limpio.replace("_", " ").title(),
                ))

            return {
                "personal_list": personal_list,
                "usuario_enfocado": usuario_enfocado_data,
                "roles_choices": roles_grilla,
                "role_mapping": role_mapping,
                "weights_map": weights_map,
                "mostrar_buscador": mostrar_buscador,
                "usuarios_potenciales": usuarios_potenciales,
                "puede_gobernar_app": puede_gobernar_app,
                "operador_es_owner_de_app": operador_es_owner_de_app,
            }

        except Exception as e:
            logger.error(
                f"❌ Error crítico en get_secured_matrix_data: {str(e)}\n{traceback.format_exc()}"
            )

            return {
                "personal_list": [],
                "usuario_enfocado": None,
                "roles_choices": [],
                "role_mapping": {},
                "weights_map": {},
                "mostrar_buscador": False,
                "usuarios_potenciales": User.objects.none(),
                "puede_gobernar_app": False,
                "operador_es_owner_de_app": False,
            }
        
        
    @classmethod
    def listar_matriz_forense_global(cls, filtros) -> list:
        """
        Motor forense global.

        Devuelve una matriz de usuarios vs aplicaciones con:
        - accesos_modulos: dict slug_app -> bool
        - owners_modulos: dict slug_app -> bool
        - roles_por_modulo: dict slug_app -> role
        """

        try:
            usuarios_queryset = (
                User.objects
                .filter(is_superuser=False)
                .select_related(
                    "axentra_profile",
                    "axentra_profile__area",
                    "axentra_profile__area__dependencia",
                    "axentra_profile__area__sede_fisica",
                )
                .order_by("-date_joined")
            )

            if filtros.get("q"):
                q_filter = filtros.get("q")

                usuarios_queryset = usuarios_queryset.filter(
                    db_models.Q(email__icontains=q_filter)
                    | db_models.Q(first_name__icontains=q_filter)
                    | db_models.Q(last_name__icontains=q_filter)
                )

            sede_id = filtros.get("sede_id")
            dependencia_id = filtros.get("dependencia_id")
            area_id = filtros.get("area_id")

            if sede_id:
                usuarios_queryset = usuarios_queryset.filter(
                    axentra_profile__area__sede_fisica_id=sede_id,
                )

            if dependencia_id:
                usuarios_queryset = usuarios_queryset.filter(
                    axentra_profile__area__dependencia_id=dependencia_id,
                )

            if area_id:
                usuarios_queryset = usuarios_queryset.filter(
                    axentra_profile__area_id=area_id,
                )

            todos_los_roles = (
                UserAppRole.objects
                .filter(
                    is_deleted=False,
                    app__is_active=True,
                    app__is_deleted=False,
                )
                .select_related("app")
            )

            matriz_seguridad_ram = {}

            for rol in todos_los_roles:
                if rol.user_id not in matriz_seguridad_ram:
                    matriz_seguridad_ram[rol.user_id] = {}

                matriz_seguridad_ram[rol.user_id][rol.app.slug] = {
                    "role": str(rol.role or "").lower().strip(),
                    "permisos": rol.permissions_list or [],
                    "is_active": rol.is_active,
                }

            plantilla_final_funcionarios = []
            particulas_ignorar = {
                "de",
                "la",
                "el",
                "y",
                "los",
                "las",
                "en",
                "para",
            }

            for user in usuarios_queryset:
                roles_usuario = matriz_seguridad_ram.get(user.id, {})

                accesos_modulos = {}
                owners_modulos = {}
                roles_por_modulo = {}
                suspendidos_modulos = {}

                for slug, _ in AppIdentifier.get_choices():
                    if getattr(user, "is_manager", False):
                        accesos_modulos[slug] = True
                        owners_modulos[slug] = False
                        roles_por_modulo[slug] = "manager"
                        suspendidos_modulos[slug] = False
                        continue

                    datos_rol = roles_usuario.get(slug, {})

                    rol_str = str(
                        datos_rol.get("role", "")
                    ).lower().strip()

                    permisos_list = datos_rol.get("permisos", []) or []
                    rol_activo = datos_rol.get("is_active", False)

                    tiene_acceso = (
                        rol_activo
                        and (
                            rol_str == "owner"
                            or "has_access_module" in permisos_list
                        )
                    )

                    accesos_modulos[slug] = tiene_acceso
                    owners_modulos[slug] = rol_activo and rol_str == "owner"
                    roles_por_modulo[slug] = rol_str if tiene_acceso else ""
                    suspendidos_modulos[slug] = bool(rol_str and not rol_activo)

                profile = getattr(user, "axentra_profile", None)
                area = getattr(profile, "area", None) if profile else None
                dependencia = getattr(area, "dependencia", None) if area else None

                if dependencia and getattr(dependencia, "slug", None):
                    palabras = dependencia.slug.split("-")

                    letras_clave = [
                        palabra[0].upper()
                        for palabra in palabras
                        if palabra and palabra not in particulas_ignorar
                    ]

                    dep_siglas = (
                        "".join(letras_clave)
                        if len(letras_clave) > 1
                        else dependencia.slug[:4].upper()
                    )

                else:
                    dep_siglas = "MUNI"

                plantilla_final_funcionarios.append({
                    "id": user.id,
                    "full_name": user.get_full_name() or user.username,
                    "email": user.email,
                    "profile_id": profile.id if profile else None,
                    "is_email_verified": getattr(user, "is_email_verified", False),
                    "is_manager": getattr(user, "is_manager", False),

                    "sede_nombre": (
                        area.sede_fisica.nombre
                        if area and getattr(area, "sede_fisica", None)
                        else ""
                    ),
                    "dependencia_siglas": dep_siglas,
                    "area_nombre": area.nombre if area else "",

                    "accesos_modulos": accesos_modulos,
                    "owners_modulos": owners_modulos,
                    "roles_por_modulo": roles_por_modulo,
                    "suspendidos_modulos": suspendidos_modulos,
                })

            return plantilla_final_funcionarios

        except Exception as e:
            logger.error(
                f"❌ Error masivo en listar_matriz_forense_global: {str(e)}\n{traceback.format_exc()}"
            )
            return []