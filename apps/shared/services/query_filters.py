# apps/shared/services/query_filters.py
from django.db import models as db_models
from apps.shared.dtos.filter_dtos import OrganizationalFilterDTO

class OrganizationalQueryEngine:
    """
    🚀 ENGINE CENTINELA TRANSVERSAL:
    Aplica filtros atómicos basándose en la topología orgánica.
    El DTO garantiza que los filtros ya vengan como objetos UUID legítimos o como None.
    """

    @classmethod
    def filtrar_entidades(
        cls, 
        queryset: db_models.QuerySet, 
        filtros: OrganizationalFilterDTO,
        profile_path: str = "profile"
    ) -> db_models.QuerySet:
        
        prefix = f"{profile_path}__" if profile_path else ""

        # Si el DTO interceptó un "all", lo transformó en None, por lo que el bloque IF se salta de forma segura.
        if filtros.sede_id:
            queryset = queryset.filter(**{f"{prefix}area__sede_fisica_id": filtros.sede_id})

        if filtros.dependencia_id:
            queryset = queryset.filter(**{f"{prefix}area__dependencia_id": filtros.dependencia_id})

        if filtros.area_id:
            queryset = queryset.filter(**{f"{prefix}area_id": filtros.area_id})

        if profile_path:
            queryset = queryset.filter(
                **{
                    f"{prefix}area__is_active": True,
                    f"{prefix}area__is_deleted": False,
                    f"{prefix}area__dependencia__is_active": True,
                    f"{prefix}area__dependencia__is_deleted": False,
                    f"{prefix}area__sede_fisica__is_active": True
                }
            ).distinct()
            
        return queryset