"""Consultas de lectura para resguardos patrimoniales."""

from django.db.models import Q, QuerySet

from apps.inventory.models import CustodyAssignment, CustodyStatus


class CustodyScope:
    """Alcances admitidos por los selectores de resguardos."""

    GLOBAL = "GLOBAL"
    DEPARTMENT = "DEPARTMENT"
    OWN = "OWN"

    VALUES = {GLOBAL, DEPARTMENT, OWN}


class CustodySelectors:
    @staticmethod
    def base_queryset() -> QuerySet:
        return (
            CustodyAssignment.objects
            .filter(is_deleted=False)
            .select_related(
                "asset",
                "assigned_to",
                "dependencia",
                "area",
                "sede",
                "prepared_by",
                "authorized_by",
                "delivered_by",
                "accepted_by",
                "rejected_by",
                "return_requested_by",
                "returned_by",
                "received_return_by",
                "cancelled_by",
            )
        )

    @classmethod
    def visible_queryset(
        cls,
        *,
        scope=CustodyScope.GLOBAL,
        actor_id=None,
        department_id=None,
    ) -> QuerySet:
        """
        Aplica el límite de lectura antes de cualquier filtro funcional.

        ``GLOBAL``
            Consulta todos los resguardos no eliminados. Sólo debe solicitarlo
            una vista que ya haya validado permisos patrimoniales globales.

        ``DEPARTMENT``
            Consulta resguardos emitidos para una dependencia concreta.

        ``OWN``
            Consulta únicamente resguardos cuyo resguardatario sea el actor.
            Haber creado el resguardo no concede acceso personal al expediente.
        """

        normalized_scope = str(scope or "").strip().upper()
        if normalized_scope not in CustodyScope.VALUES:
            raise ValueError("El alcance de resguardos no es válido.")

        queryset = cls.base_queryset()

        if normalized_scope == CustodyScope.GLOBAL:
            return queryset

        if normalized_scope == CustodyScope.DEPARTMENT:
            if not department_id:
                return queryset.none()

            return queryset.filter(dependencia_id=department_id)

        if not actor_id:
            return queryset.none()

        return queryset.filter(assigned_to_id=actor_id)

    @classmethod
    def listar(
        cls,
        *,
        q="",
        status="",
        asset_id="",
        assigned_to_id="",
        department_id="",
        scope=CustodyScope.GLOBAL,
        actor_id=None,
        scope_department_id=None,
    ) -> QuerySet:
        """
        Lista resguardos visibles y posteriormente aplica filtros de pantalla.

        ``department_id`` es un filtro elegido por el usuario.
        ``scope_department_id`` es el límite obligatorio de autorización.
        Se mantienen separados para impedir que un parámetro GET amplíe el
        alcance autorizado.
        """

        queryset = cls.visible_queryset(
            scope=scope,
            actor_id=actor_id,
            department_id=scope_department_id,
        )

        normalized_query = str(q or "").strip()
        if normalized_query:
            queryset = queryset.filter(
                Q(folio__icontains=normalized_query)
                | Q(
                    asset__official_inventory_number__icontains=(
                        normalized_query
                    )
                )
                | Q(
                    asset__internal_inventory_number__icontains=(
                        normalized_query
                    )
                )
                | Q(asset__name__icontains=normalized_query)
                | Q(asset__serial_number__icontains=normalized_query)
            )

        if status:
            queryset = queryset.filter(status=status)

        if asset_id:
            queryset = queryset.filter(asset_id=asset_id)

        if assigned_to_id:
            queryset = queryset.filter(assigned_to_id=assigned_to_id)

        if department_id:
            queryset = queryset.filter(dependencia_id=department_id)

        return queryset.order_by("-assigned_at", "-created_at")

    @classmethod
    def obtener(
        cls,
        custody_id,
        *,
        scope=CustodyScope.GLOBAL,
        actor_id=None,
        department_id=None,
    ):
        """Obtiene un resguardo sólo si pertenece al alcance indicado."""

        return (
            cls.visible_queryset(
                scope=scope,
                actor_id=actor_id,
                department_id=department_id,
            )
            .prefetch_related("events")
            .get(pk=custody_id)
        )

    @classmethod
    def activo_del_bien(
        cls,
        asset_id,
        *,
        scope=CustodyScope.GLOBAL,
        actor_id=None,
        department_id=None,
    ):
        """Devuelve el resguardo vigente visible de un activo."""

        return (
            cls.visible_queryset(
                scope=scope,
                actor_id=actor_id,
                department_id=department_id,
            )
            .filter(
                asset_id=asset_id,
                status=CustodyStatus.ACTIVE,
            )
            .order_by("-assigned_at")
            .first()
        )

    @classmethod
    def historial_del_bien(
        cls,
        asset_id,
        *,
        scope=CustodyScope.GLOBAL,
        actor_id=None,
        department_id=None,
    ) -> QuerySet:
        return cls.listar(
            asset_id=asset_id,
            scope=scope,
            actor_id=actor_id,
            scope_department_id=department_id,
        )

    @staticmethod
    def status_choices():
        return CustodyStatus.choices


__all__ = ["CustodyScope", "CustodySelectors"]
