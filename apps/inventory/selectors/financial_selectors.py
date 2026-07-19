"""Consultas financieras y contables de Inventory."""

from django.db.models import Q, QuerySet

from apps.inventory.models import (
    AccountingExportBatch,
    AccountingReconciliation,
    DepreciationPolicy,
    DepreciationRecord,
    DepreciationRun,
)


class FinancialScope:
    GLOBAL = "GLOBAL"
    DEPARTMENT = "DEPARTMENT"
    OWN = "OWN"

    VALUES = {GLOBAL, DEPARTMENT, OWN}

    @classmethod
    def normalize(cls, value):
        normalized = str(value or "").strip().upper()
        if normalized not in cls.VALUES:
            raise ValueError("El alcance financiero no es válido.")
        return normalized


class FinancialSelectors:
    @staticmethod
    def depreciation_policies() -> QuerySet:
        """Las políticas son catálogos, no contienen saldos patrimoniales."""

        return (
            DepreciationPolicy.objects
            .filter(is_active=True, is_deleted=False)
            .select_related("accounting_account")
            .order_by("name")
        )

    @staticmethod
    def _global_only(queryset, *, scope):
        """
        Impide exponer procesos municipales sin dimensión departamental.

        DepreciationRun, AccountingExportBatch y AccountingReconciliation no
        conservan una FK de dependencia. Un JSON de filtros no constituye una
        frontera de autorización confiable.
        """

        normalized_scope = FinancialScope.normalize(scope)
        if normalized_scope != FinancialScope.GLOBAL:
            return queryset.none()
        return queryset

    @classmethod
    def depreciation_runs(
        cls,
        *,
        q="",
        status="",
        period_year=None,
        scope=FinancialScope.GLOBAL,
    ) -> QuerySet:
        queryset = (
            DepreciationRun.objects
            .filter(is_deleted=False)
            .select_related(
                "initiated_by",
                "completed_by",
                "posted_by",
            )
        )
        queryset = cls._global_only(queryset, scope=scope)

        normalized_query = str(q or "").strip()
        if normalized_query:
            queryset = queryset.filter(
                Q(folio__icontains=normalized_query)
                | Q(notes__icontains=normalized_query)
                | Q(error_message__icontains=normalized_query)
            )

        if status:
            queryset = queryset.filter(status=status)

        if period_year:
            queryset = queryset.filter(period_year=period_year)

        return queryset.order_by("-created_at")

    @classmethod
    def depreciation_run_detail(
        cls,
        run_id,
        *,
        scope=FinancialScope.GLOBAL,
    ):
        return (
            cls.depreciation_runs(scope=scope)
            .prefetch_related("records")
            .get(pk=run_id)
        )

    @staticmethod
    def visible_depreciation_records(
        *,
        scope=FinancialScope.GLOBAL,
        actor_id=None,
        department_id=None,
    ) -> QuerySet:
        normalized_scope = FinancialScope.normalize(scope)
        queryset = (
            DepreciationRecord.objects
            .filter(is_deleted=False)
            .select_related(
                "run",
                "asset",
                "policy",
                "calculated_by",
            )
        )

        if normalized_scope == FinancialScope.GLOBAL:
            return queryset

        if normalized_scope == FinancialScope.DEPARTMENT:
            if not department_id:
                return queryset.none()
            return queryset.filter(
                asset__current_dependencia_id=department_id
            )

        if not actor_id:
            return queryset.none()

        return queryset.filter(asset__current_custodian_id=actor_id)

    @classmethod
    def depreciation_records(
        cls,
        *,
        q="",
        asset_id=None,
        period_year=None,
        run_id=None,
        scope=FinancialScope.GLOBAL,
        actor_id=None,
        scope_department_id=None,
    ) -> QuerySet:
        queryset = cls.visible_depreciation_records(
            scope=scope,
            actor_id=actor_id,
            department_id=scope_department_id,
        )

        normalized_query = str(q or "").strip()
        if normalized_query:
            queryset = queryset.filter(
                Q(asset_folio_snapshot__icontains=normalized_query)
                | Q(asset_name_snapshot__icontains=normalized_query)
                | Q(
                    accounting_account_code_snapshot__icontains=(
                        normalized_query
                    )
                )
            )

        if asset_id:
            queryset = queryset.filter(asset_id=asset_id)

        if period_year:
            queryset = queryset.filter(period_year=period_year)

        if run_id:
            queryset = queryset.filter(run_id=run_id)

        return queryset.order_by(
            "-period_year",
            "-period_month",
            "asset_folio_snapshot",
        )

    @classmethod
    def depreciation_record_detail(
        cls,
        record_id,
        *,
        scope=FinancialScope.GLOBAL,
        actor_id=None,
        department_id=None,
    ):
        return cls.visible_depreciation_records(
            scope=scope,
            actor_id=actor_id,
            department_id=department_id,
        ).get(pk=record_id)

    @classmethod
    def export_batches(
        cls,
        *,
        q="",
        export_type="",
        status="",
        scope=FinancialScope.GLOBAL,
    ) -> QuerySet:
        queryset = (
            AccountingExportBatch.objects
            .filter(is_deleted=False)
            .select_related(
                "requested_by",
                "completed_by",
            )
        )
        queryset = cls._global_only(queryset, scope=scope)

        normalized_query = str(q or "").strip()
        if normalized_query:
            queryset = queryset.filter(
                Q(folio__icontains=normalized_query)
                | Q(destination_system__icontains=normalized_query)
                | Q(generated_filename__icontains=normalized_query)
                | Q(generated_file_hash__iexact=normalized_query)
            )

        if export_type:
            queryset = queryset.filter(export_type=export_type)

        if status:
            queryset = queryset.filter(status=status)

        return queryset.order_by("-created_at")

    @classmethod
    def export_batch_detail(
        cls,
        batch_id,
        *,
        scope=FinancialScope.GLOBAL,
    ):
        return cls.export_batches(scope=scope).get(pk=batch_id)

    @classmethod
    def reconciliations(
        cls,
        *,
        q="",
        status="",
        date_from=None,
        date_to=None,
        scope=FinancialScope.GLOBAL,
    ) -> QuerySet:
        queryset = (
            AccountingReconciliation.objects
            .filter(is_deleted=False)
            .select_related(
                "created_by",
                "processed_by",
                "reviewed_by",
            )
        )
        queryset = cls._global_only(queryset, scope=scope)

        normalized_query = str(q or "").strip()
        if normalized_query:
            queryset = queryset.filter(
                Q(folio__icontains=normalized_query)
                | Q(source_system__icontains=normalized_query)
                | Q(source_filename__icontains=normalized_query)
                | Q(source_file_hash__iexact=normalized_query)
            )

        if status:
            queryset = queryset.filter(status=status)

        if date_from:
            queryset = queryset.filter(period_end__gte=date_from)

        if date_to:
            queryset = queryset.filter(period_start__lte=date_to)

        return queryset.order_by("-created_at")

    @classmethod
    def reconciliation_detail(
        cls,
        reconciliation_id,
        *,
        scope=FinancialScope.GLOBAL,
    ):
        return (
            cls.reconciliations(scope=scope)
            .prefetch_related("items")
            .get(pk=reconciliation_id)
        )


__all__ = ["FinancialScope", "FinancialSelectors"]

