"""Consultas de movimientos, préstamos y bajas patrimoniales."""

from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.inventory.models import (
    AssetLoan,
    AssetLoanStatus,
    DisposalRequest,
    InventoryMovement,
)


class RegistryScope:
    """Alcances reutilizados por movimientos, préstamos y bajas."""

    GLOBAL = "GLOBAL"
    DEPARTMENT = "DEPARTMENT"
    OWN = "OWN"

    VALUES = {GLOBAL, DEPARTMENT, OWN}

    @classmethod
    def normalize(cls, value):
        normalized = str(value or "").strip().upper()
        if normalized not in cls.VALUES:
            raise ValueError("El alcance de consulta no es válido.")
        return normalized


class MovementSelectors:
    @staticmethod
    def base_queryset() -> QuerySet:
        return (
            InventoryMovement.objects
            .filter(is_deleted=False)
            .select_related(
                "asset",
                "performed_by",
                "from_dependencia",
                "from_area",
                "from_sede",
                "from_user",
                "to_dependencia",
                "to_area",
                "to_sede",
                "to_user",
            )
        )

    @classmethod
    def visible_queryset(
        cls,
        *,
        scope=RegistryScope.GLOBAL,
        actor_id=None,
        department_id=None,
    ) -> QuerySet:
        normalized_scope = RegistryScope.normalize(scope)
        queryset = cls.base_queryset()

        if normalized_scope == RegistryScope.GLOBAL:
            return queryset

        if normalized_scope == RegistryScope.DEPARTMENT:
            if not department_id:
                return queryset.none()

            return queryset.filter(
                Q(from_dependencia_id=department_id)
                | Q(to_dependencia_id=department_id)
            )

        if not actor_id:
            return queryset.none()

        return queryset.filter(
            Q(performed_by_id=actor_id)
            | Q(from_user_id=actor_id)
            | Q(to_user_id=actor_id)
        )

    @classmethod
    def listar(
        cls,
        *,
        q="",
        asset_id="",
        movement_type="",
        date_from=None,
        date_to=None,
        scope=RegistryScope.GLOBAL,
        actor_id=None,
        scope_department_id=None,
    ) -> QuerySet:
        queryset = cls.visible_queryset(
            scope=scope,
            actor_id=actor_id,
            department_id=scope_department_id,
        )

        normalized_query = str(q or "").strip()
        if normalized_query:
            queryset = queryset.filter(
                Q(
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
                | Q(reason__icontains=normalized_query)
            )

        if asset_id:
            queryset = queryset.filter(asset_id=asset_id)

        if movement_type:
            queryset = queryset.filter(movement_type=movement_type)

        if date_from:
            queryset = queryset.filter(occurred_at__date__gte=date_from)

        if date_to:
            queryset = queryset.filter(occurred_at__date__lte=date_to)

        return queryset.order_by("-occurred_at", "-created_at")

    @classmethod
    def obtener(
        cls,
        movement_id,
        *,
        scope=RegistryScope.GLOBAL,
        actor_id=None,
        department_id=None,
    ):
        return cls.visible_queryset(
            scope=scope,
            actor_id=actor_id,
            department_id=department_id,
        ).get(pk=movement_id)

    @classmethod
    def historial_del_bien(
        cls,
        asset_id,
        *,
        scope=RegistryScope.GLOBAL,
        actor_id=None,
        department_id=None,
    ) -> QuerySet:
        return cls.listar(
            asset_id=asset_id,
            scope=scope,
            actor_id=actor_id,
            scope_department_id=department_id,
        )


class LoanSelectors:
    @staticmethod
    def base_queryset() -> QuerySet:
        return (
            AssetLoan.objects
            .filter(is_deleted=False)
            .select_related(
                "asset",
                "borrower",
                "requested_by",
            )
        )

    @classmethod
    def visible_queryset(
        cls,
        *,
        scope=RegistryScope.GLOBAL,
        actor_id=None,
        department_id=None,
    ) -> QuerySet:
        normalized_scope = RegistryScope.normalize(scope)
        queryset = cls.base_queryset()

        if normalized_scope == RegistryScope.GLOBAL:
            return queryset

        if normalized_scope == RegistryScope.DEPARTMENT:
            if not department_id:
                return queryset.none()

            return queryset.filter(
                Q(origin_dependencia_id=department_id)
                | Q(destination_dependencia_id=department_id)
            )

        if not actor_id:
            return queryset.none()

        return queryset.filter(
            Q(borrower_id=actor_id)
            | Q(requested_by_id=actor_id)
        )

    @classmethod
    def listar(
        cls,
        *,
        q="",
        status="",
        asset_id="",
        borrower_id="",
        overdue=False,
        scope=RegistryScope.GLOBAL,
        actor_id=None,
        scope_department_id=None,
    ) -> QuerySet:
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

        if borrower_id:
            queryset = queryset.filter(borrower_id=borrower_id)

        if overdue:
            queryset = queryset.filter(
                status__in=(
                    AssetLoanStatus.DELIVERED,
                    AssetLoanStatus.OVERDUE,
                    AssetLoanStatus.RETURN_PENDING,
                ),
                due_at__lt=timezone.now(),
            )

        return queryset.order_by("-requested_at", "-created_at")

    @classmethod
    def obtener(
        cls,
        loan_id,
        *,
        scope=RegistryScope.GLOBAL,
        actor_id=None,
        department_id=None,
    ):
        return cls.visible_queryset(
            scope=scope,
            actor_id=actor_id,
            department_id=department_id,
        ).get(pk=loan_id)

    @staticmethod
    def status_choices():
        return AssetLoanStatus.choices


class DisposalSelectors:
    @staticmethod
    def base_queryset() -> QuerySet:
        return (
            DisposalRequest.objects
            .filter(is_deleted=False)
            .select_related(
                "asset",
                "requested_by",
            )
        )

    @classmethod
    def visible_queryset(
        cls,
        *,
        scope=RegistryScope.GLOBAL,
        actor_id=None,
        department_id=None,
    ) -> QuerySet:
        normalized_scope = RegistryScope.normalize(scope)
        queryset = cls.base_queryset()

        if normalized_scope == RegistryScope.GLOBAL:
            return queryset

        if normalized_scope == RegistryScope.DEPARTMENT:
            if not department_id:
                return queryset.none()

            return queryset.filter(
                asset__current_dependencia_id=department_id
            )

        if not actor_id:
            return queryset.none()

        return queryset.filter(requested_by_id=actor_id)

    @classmethod
    def listar(
        cls,
        *,
        q="",
        status="",
        asset_id="",
        reason="",
        scope=RegistryScope.GLOBAL,
        actor_id=None,
        scope_department_id=None,
    ) -> QuerySet:
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
                | Q(description__icontains=normalized_query)
            )

        if status:
            queryset = queryset.filter(status=status)

        if asset_id:
            queryset = queryset.filter(asset_id=asset_id)

        if reason:
            queryset = queryset.filter(reason=reason)

        return queryset.order_by("-requested_at", "-created_at")

    @classmethod
    def obtener(
        cls,
        disposal_id,
        *,
        scope=RegistryScope.GLOBAL,
        actor_id=None,
        department_id=None,
    ):
        return (
            cls.visible_queryset(
                scope=scope,
                actor_id=actor_id,
                department_id=department_id,
            )
            .prefetch_related("approvals")
            .get(pk=disposal_id)
        )


__all__ = [
    "DisposalSelectors",
    "LoanSelectors",
    "MovementSelectors",
    "RegistryScope",
]
