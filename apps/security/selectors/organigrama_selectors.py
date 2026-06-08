# apps/security/selectors/organigrama_selectors.py
import uuid
from typing import List, Dict, Any
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.db.models import Count

from apps.security.models import Sede, Dependencia, AreaOperativa, AppDependencyCapability
from apps.security.dtos import (
    SedeReadOnlyDTO, 
    DependenciaReadOnlyDTO, 
    AreaOperativaReadOnlyDTO,
    CapabilityReadOnlyDTO
)

User = get_user_model()

class OrganigramaDashboardSelector:
    """Encapsula la inteligencia analítica del organigrama inyectando datos limpios al Core OS."""
    
    @classmethod
    def obtener_metricas_core(cls) -> Dict[str, int]:
        return {
            'total_sedes': Sede.objects.filter(is_active=True).count(),
            'total_dependencias': Dependencia.objects.filter(is_active=True, is_deleted=False).count(),
            'total_areas': AreaOperativa.objects.filter(is_active=True, is_deleted=False).count(),
            'total_capacidades': AppDependencyCapability.objects.count(), 
        }
        
    @classmethod
    def obtener_analitica_graficas(cls) -> Dict[str, Any]:
        """Calcula la distribución de oficinas operativas por Dependencia mitigando el N+1."""
        analytics_qs = Dependencia.objects.filter(
            is_active=True, 
            is_deleted=False
        ).annotate(
            num_oficinas=Count('areas_operativas_instaladas')  
        ).order_by('-num_oficinas')[:10]
        
        return {
            'labels': [dep.nombre.upper() for dep in analytics_qs],
            'valores': [dep.num_oficinas for dep in analytics_qs]
        }


class SedeSelectors:
    """Consultas optimizadas para el dominio de Sedes / Inmuebles."""
    
    @staticmethod
    def _mapear_a_dto(sede: Sede) -> SedeReadOnlyDTO:
        encargado_name = "Sin Líder Asignado"
        if sede.encargado_sede:
            encargado_name = f"{sede.encargado_sede.first_name} {sede.encargado_sede.last_name}".strip() or sede.encargado_sede.email

        return SedeReadOnlyDTO(
            id=sede.id,
            nombre=sede.nombre,
            direccion=sede.direccion or "Sin Dirección Física Registrada",
            encargado_sede_id=sede.encargado_sede.id if sede.encargado_sede else None,
            encargado_sede_name=encargado_name,
            is_active=sede.is_active
        )

    @classmethod
    def listar_todas(cls) -> List[SedeReadOnlyDTO]:
        queryset = Sede.objects.select_related('encargado_sede').filter(is_active=True).order_by('nombre')
        return [cls._mapear_a_dto(sede) for sede in queryset]


class DependenciaSelectors:
    """Consultas optimizadas para Direcciones Generales reduciendo la fricción en RAM."""

    @staticmethod
    def _mapear_a_dto(dep: Dependencia) -> DependenciaReadOnlyDTO:
        titular_name = "Titular No Asignado"
        if dep.encargado_departamento:
            titular_name = f"{dep.encargado_departamento.first_name} {dep.encargado_departamento.last_name}".strip() or dep.encargado_departamento.email

        # Interpolación matricial en RAM por prefetch_related
        sedes_nombres = [
            ao.sede_fisica.nombre for ao in dep.areas_operativas_instaladas.all()
            if ao.is_active and not ao.is_deleted
        ]

        return DependenciaReadOnlyDTO(
            id=dep.id,
            nombre=dep.nombre,
            slug=dep.slug,
            encargado_departamento_id=dep.encargado_departamento.id if dep.encargado_departamento else None,
            encargado_departamento_name=titular_name,
            is_active=dep.is_active,
            is_deleted=dep.is_deleted,
            sedes_asignadas_nombres=list(set(sedes_nombres))
        )

    @classmethod
    def listar_activas(cls) -> List[DependenciaReadOnlyDTO]:
        queryset = (
            Dependencia.objects.select_related('encargado_departamento')
            .prefetch_related('areas_operativas_instaladas__sede_fisica')
            .filter(is_active=True, is_deleted=False)
            .order_by('nombre')
        )
        return [cls._mapear_a_dto(dep) for dep in queryset]

    @classmethod
    def obtener_por_id(cls, pk: uuid.UUID) -> DependenciaReadOnlyDTO:
        dep = get_object_or_404(
            Dependencia.objects.select_related('encargado_departamento')
            .prefetch_related('areas_operativas_instaladas__sede_fisica'), 
            pk=pk
        )
        return cls._mapear_a_dto(dep)


class AreaOperativaSelectors:
    """Consultas de cruce matricial para la grilla interna de adscripciones y HTMX."""

    @staticmethod
    def _mapear_a_dto(area: AreaOperativa) -> AreaOperativaReadOnlyDTO:
        return AreaOperativaReadOnlyDTO(
            id=area.id,
            nombre=area.nombre,
            slug=area.slug,
            dependencia_id=area.dependencia.id,
            dependencia_nombre=area.dependencia.nombre,
            sede_fisica_id=area.sede_fisica.id,
            sede_fisica_nombre=area.sede_fisica.nombre,
            is_active=area.is_active,
            is_deleted=area.is_deleted
        )

    @classmethod
    def listar_por_dependencia(cls, dependencia_id: uuid.UUID) -> List[AreaOperativaReadOnlyDTO]:
        """🎯 PIPELINE HTMX: Filtra las oficinas adscritas a un nodo directivo."""
        queryset = (
            AreaOperativa.objects.select_related('dependencia', 'sede_fisica')
            .filter(dependencia_id=dependencia_id, is_active=True, is_deleted=False)
            .order_by('nombre')
        )
        return [cls._mapear_a_dto(area) for area in queryset]