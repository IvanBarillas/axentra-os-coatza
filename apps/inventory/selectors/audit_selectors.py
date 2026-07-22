"""Consultas de lectura para la toma física de inventario."""

from django.db.models import Count, Q, QuerySet

from apps.inventory.models import (
    Asset,
    AssetPatrimonialStatus,
    PhysicalAuditItem,
    PhysicalAuditResult,
    PhysicalAuditSession,
    PhysicalAuditStatus,
)


class PhysicalAuditVisibilityScope:
    GLOBAL = "GLOBAL"
    DEPARTMENT = "DEPARTMENT"
    OWN = "OWN"

    VALUES = {GLOBAL, DEPARTMENT, OWN}

    @classmethod
    def normalize(cls, value):
        normalized = str(value or "").strip().upper()
        if normalized not in cls.VALUES:
            raise ValueError("El alcance de auditoría física no es válido.")
        return normalized


class PhysicalAuditSelectors:
    @staticmethod
    def eligible_assets(*, site_id=None, department_id=None):
        queryset = Asset.objects.filter(
            is_deleted=False,
            patrimonial_status=AssetPatrimonialStatus.ACTIVE,
        )
        if site_id:
            queryset = queryset.filter(current_sede_id=site_id)
        if department_id:
            queryset = queryset.filter(current_dependencia_id=department_id)
        return queryset

    @staticmethod
    def base_sessions() -> QuerySet:
        return (
            PhysicalAuditSession.objects
            .filter(is_deleted=False)
            .select_related(
                "sede",
                "dependencia",
                "area",
                "started_by",
                "closed_by",
            )
        )

    @staticmethod
    def base_items() -> QuerySet:
        return (
            PhysicalAuditItem.objects
            .filter(is_deleted=False)
            .select_related(
                "session",
                "asset",
                "scanned_by",
            )
        )

    @classmethod
    def visible_sessions(
        cls,
        *,
        scope=PhysicalAuditVisibilityScope.GLOBAL,
        actor_id=None,
        department_id=None,
    ) -> QuerySet:
        normalized_scope = PhysicalAuditVisibilityScope.normalize(scope)
        queryset = cls.base_sessions()

        if normalized_scope == PhysicalAuditVisibilityScope.GLOBAL:
            return queryset

        if normalized_scope == PhysicalAuditVisibilityScope.DEPARTMENT:
            if not department_id:
                return queryset.none()

            return queryset.filter(dependencia_id=department_id)

        if not actor_id:
            return queryset.none()

        return queryset.filter(
            Q(started_by_id=actor_id)
            | Q(closed_by_id=actor_id)
            | Q(items__scanned_by_id=actor_id)
        ).distinct()

    @classmethod
    def sessions(
        cls,
        *,
        q="",
        status="",
        department_id="",
        site_id="",
        fiscal_year="",
        scope=PhysicalAuditVisibilityScope.GLOBAL,
        actor_id=None,
        scope_department_id=None,
    ) -> QuerySet:
        """
        Lista sesiones visibles.

        ``department_id`` es sólo un filtro de pantalla.
        ``scope_department_id`` es el límite organizacional obligatorio.
        """

        queryset = cls.visible_sessions(
            scope=scope,
            actor_id=actor_id,
            department_id=scope_department_id,
        )

        normalized_query = str(q or "").strip()
        if normalized_query:
            queryset = queryset.filter(
                Q(folio__icontains=normalized_query)
                | Q(name__icontains=normalized_query)
                | Q(notes__icontains=normalized_query)
            )

        if status:
            queryset = queryset.filter(status=status)

        if department_id:
            queryset = queryset.filter(dependencia_id=department_id)

        if site_id:
            queryset = queryset.filter(sede_id=site_id)

        if fiscal_year:
            queryset = queryset.filter(fiscal_year=fiscal_year)

        return queryset.order_by("-created_at")

    @classmethod
    def session_detail(
        cls,
        session_id,
        *,
        scope=PhysicalAuditVisibilityScope.GLOBAL,
        actor_id=None,
        department_id=None,
    ):
        return (
            cls.visible_sessions(
                scope=scope,
                actor_id=actor_id,
                department_id=department_id,
            )
            .prefetch_related("items")
            .get(pk=session_id)
        )

    @classmethod
    def visible_items(
        cls,
        *,
        scope=PhysicalAuditVisibilityScope.GLOBAL,
        actor_id=None,
        department_id=None,
    ) -> QuerySet:
        visible_session_ids = cls.visible_sessions(
            scope=scope,
            actor_id=actor_id,
            department_id=department_id,
        ).values("id")

        return cls.base_items().filter(session_id__in=visible_session_ids)

    @classmethod
    def items(
        cls,
        *,
        session_id,
        result="",
        asset_id="",
        scanned_by_id="",
        scope=PhysicalAuditVisibilityScope.GLOBAL,
        actor_id=None,
        scope_department_id=None,
    ) -> QuerySet:
        queryset = cls.visible_items(
            scope=scope,
            actor_id=actor_id,
            department_id=scope_department_id,
        ).filter(session_id=session_id)

        if result:
            queryset = queryset.filter(result=result)

        if asset_id:
            queryset = queryset.filter(asset_id=asset_id)

        if scanned_by_id:
            queryset = queryset.filter(scanned_by_id=scanned_by_id)

        return queryset.order_by("-scanned_at", "-created_at")

    @classmethod
    def item_detail(
        cls,
        item_id,
        *,
        scope=PhysicalAuditVisibilityScope.GLOBAL,
        actor_id=None,
        department_id=None,
    ):
        return cls.visible_items(
            scope=scope,
            actor_id=actor_id,
            department_id=department_id,
        ).get(pk=item_id)

    @classmethod
    def result_totals(
        cls,
        session_id,
        *,
        scope=PhysicalAuditVisibilityScope.GLOBAL,
        actor_id=None,
        department_id=None,
    ) -> QuerySet:
        return (
            cls.visible_items(
                scope=scope,
                actor_id=actor_id,
                department_id=department_id,
            )
            .filter(session_id=session_id)
            .values("result")
            .annotate(total=Count("id"))
            .order_by("result")
        )

    @staticmethod
    def status_choices():
        return PhysicalAuditStatus.choices

    @staticmethod
    def result_choices():
        return PhysicalAuditResult.choices


__all__ = [
    "PhysicalAuditSelectors",
    "PhysicalAuditVisibilityScope",
]
