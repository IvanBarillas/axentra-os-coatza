# apps/security/selectors/accounts_selectors.py
import datetime
import uuid
from typing import List, Dict, Any
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.db import models as db_models

from apps.security.dtos import FuncionarioReadOnlyDTO
from apps.shared.apps_config import AppIdentifier  
from apps.security.models import UserAppRole

User = get_user_model()

class AccountsDashboardSelectors:
    """Métricas operativas del personal (Read-Only)."""

    @staticmethod
    def obtener_metricas_plantilla() -> Dict[str, int]:
        return {
            'total_funcionarios': User.objects.filter(is_superuser=False).count(),
            'funcionarios_activos': User.objects.filter(is_active=True, is_superuser=False).count(),
            'funcionarios_baja': User.objects.filter(is_active=False, is_superuser=False).count(),
            'total_managers': User.objects.filter(is_manager=True).count(),
        }

    @staticmethod
    def obtener_cronologia_altas() -> List[Dict[str, Any]]:
        hoy = datetime.date.today()
        cronologia_altas = []
        
        for i in range(3, -1, -1):
            mes_eval = hoy.month - i
            año_eval = hoy.year
            if mes_eval <= 0:
                mes_eval += 12
                año_eval -= 1
                
            fecha_aux = datetime.date(año_eval, mes_eval, 1)
            nombre_mes = fecha_aux.strftime('%b').upper()
            
            conteo_altas = User.objects.filter(
                created_at__year=año_eval,
                created_at__month=mes_eval,
                is_superuser=False
            ).count()
            
            porcentaje_barra = min(100, conteo_altas * 10) if conteo_altas > 0 else 2
            
            cronologia_altas.append({
                'mes': nombre_mes,
                'amount': conteo_altas,
                'cantidad': conteo_altas,
                'porcentaje': porcentaje_barra
            })
            
        return cronologia_altas


class FuncionarioSelectors:
    """Mapeador atómico perimetral de la identidad del funcionario público."""

    @classmethod
    def _mapear_a_dto(cls, user, mapa_accesos: dict = None, mapa_owners: dict = None) -> FuncionarioReadOnlyDTO:
        # 🟢 CORRECCIÓN ATÓMICA: Evaluamos usando el nuevo related_name unificado 'axentra_profile'
        profile = getattr(user, 'axentra_profile', None)
        accesos = mapa_accesos or {}
        owners = mapa_owners or {}
        
        apps_criticas = [AppIdentifier.SECURITY]
        tiene_acceso_critico = any(accesos.get(app_slug, False) for app_slug in apps_criticas)
        es_administrador_sistema = user.is_manager or tiene_acceso_critico

        if not profile:
            return FuncionarioReadOnlyDTO(
                id=user.id, email=user.email, first_name=user.first_name, last_name=user.last_name,
                full_name=user.full_name or user.email,
                phone=getattr(user, 'phone', "") or "S/T",
                must_change_password=user.must_change_password,
                is_email_verified=user.is_email_verified, 
                is_manager=user.is_manager, is_active=user.is_active, is_admin_user=es_administrador_sistema,
                area_id=uuid.UUID('00000000-0000-0000-0000-000000000000'),
                profile_id=None, sede_id=None, sede_nombre="DESCONOCIDA",
                dependencia_id=None, dependencia_nombre="⚠️ CRÍTICO: SIN ADSCRIPCIÓN MATRICIAL (NO PROFILE)",
                dependencia_siglas="LIMBO", area_nombre="SIN ÁREA / DESASIGNADO",
                puesto="Cuenta huérfana en la plataforma", telefono_oficina="",
                accesos_modulos=accesos, owners_modulos=owners
            )
            
        area_obj = profile.area  
        return FuncionarioReadOnlyDTO(
            id=user.id, email=user.email, first_name=user.first_name, last_name=user.last_name,
            full_name=user.full_name or user.email,
            phone=getattr(user, 'phone', "") or "S/T",
            must_change_password=user.must_change_password,
            is_email_verified=user.is_email_verified, 
            is_manager=user.is_manager, is_active=user.is_active, is_admin_user=es_administrador_sistema,
            profile_id=profile.id, area_id=profile.area_id, 
            area_nombre=area_obj.nombre if area_obj else "Sin Área Asignada",
            sede_id=area_obj.sede_fisica_id if area_obj else None, 
            sede_nombre=area_obj.sede_fisica.nombre if area_obj else "Sin Sede Asignada",
            dependencia_id=area_obj.dependencia_id if area_obj else None,
            dependencia_nombre=area_obj.dependencia.nombre if area_obj else "Sin Dependencia Asignada",
            dependencia_siglas=area_obj.dependencia.slug.upper() if area_obj else "S/D",
            puesto=profile.puesto, telefono_oficina=profile.telefono_oficina or "",
            accesos_modulos=accesos, owners_modulos=owners
        )

    @classmethod
    def listar_plantilla_activa(cls, search_query: str = "", sede_id: str = "", dependencia_id: str = "", area_id: str = "") -> List[FuncionarioReadOnlyDTO]:
        """
        Extrae la nómina del Ayuntamiento mitigando el N+1 mediante caché en RAM.
        Filtra por dimensiones territoriales y estructurales en una sola transacción SQL.
        """
        # 🟢 REGLA DE INTEGRIDAD DE QA: Se añade is_deleted=False para omitir usuarios dados de baja
        usuarios_queryset = (
            User.objects.filter(is_superuser=False, is_deleted=False)
            .select_related(
                'axentra_profile', 
                'axentra_profile__area', 
                'axentra_profile__area__dependencia', 
                'axentra_profile__area__sede_fisica'
            )
            .order_by('-created_at')
        )
        
        # 1. Filtro por Búsqueda de Texto Abierto
        if search_query:
            usuarios_queryset = usuarios_queryset.filter(
                db_models.Q(email__icontains=search_query) | 
                db_models.Q(first_name__icontains=search_query) | 
                db_models.Q(last_name__icontains=search_query)
            )
            
        # 2. Filtro por Sede Inmobiliaria Física
        if sede_id:
            usuarios_queryset = usuarios_queryset.filter(axentra_profile__area__sede_fisica_id=sede_id)
            
        # 3. Filtro por Dependencia / Dirección General
        if dependencia_id:
            usuarios_queryset = usuarios_queryset.filter(axentra_profile__area__dependencia_id=dependencia_id)
            
        # 4. Filtro por Área Operativa / Oficina
        if area_id:
            usuarios_queryset = usuarios_queryset.filter(axentra_profile__area_id=area_id)
        
        # 🟢 CACHÉ EN RAM DE ROLES (Mantiene tu misma lógica de alto rendimiento)
        todos_los_roles = UserAppRole.objects.filter(is_active=True).select_related('app')
        matriz_seguridad_ram = {}
        for rol in todos_los_roles:
            if rol.user_id not in matriz_seguridad_ram:
                matriz_seguridad_ram[rol.user_id] = {}
            matriz_seguridad_ram[rol.user_id][rol.app.slug] = {
                'role': rol.role,
                'permisos': rol.permissions_list or []
            }

        plantilla_final_dtos = []
        for user in usuarios_queryset:
            roles_usuario = matriz_seguridad_ram.get(user.id, {})
            mapa_accesos_modulo = {}
            mapa_owners_modulo = {}  
            
            for slug, _ in AppIdentifier.get_choices():
                if user.is_manager:
                    mapa_accesos_modulo[slug] = True
                    mapa_owners_modulo[slug] = True  
                else:
                    datos_rol = roles_usuario.get(slug, {})
                    permisos_list = datos_rol.get('permisos', [])
                    rol_str = datos_rol.get('role', '')
                    
                    mapa_accesos_modulo[slug] = rol_str == "owner" or "has_access_module" in permisos_list
                    mapa_owners_modulo[slug] = rol_str == "owner"
            
            dto = cls._mapear_a_dto(user, mapa_accesos=mapa_accesos_modulo, mapa_owners=mapa_owners_modulo)
            plantilla_final_dtos.append(dto)

        return plantilla_final_dtos