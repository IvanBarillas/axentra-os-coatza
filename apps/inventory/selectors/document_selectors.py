"""Consultas seguras de documentos y fotografías de Inventory."""

from django.db.models import Q, QuerySet

from apps.inventory.models import (
    Asset,
    AssetDocument,
    AssetIntakeRequest,
    AssetLoan,
    AssetPhoto,
    CustodyAssignment,
    DisposalRequest,
    DocumentAccessLevel,
    DocumentValidationStatus,
    InventoryDocumentOwnerType,
    InventoryMovement,
    PhysicalAuditItem,
    PhysicalAuditSession,
)


class DocumentScope:
    GLOBAL = "GLOBAL"
    DEPARTMENT = "DEPARTMENT"
    OWN = "OWN"

    VALUES = {GLOBAL, DEPARTMENT, OWN}

    @classmethod
    def normalize(cls, value):
        normalized = str(value or "").strip().upper()
        if normalized not in cls.VALUES:
            raise ValueError("El alcance documental no es válido.")
        return normalized


class DocumentSelectors:
    @staticmethod
    def document_base_queryset() -> QuerySet:
        return (
            AssetDocument.objects
            .filter(is_deleted=False)
            .select_related(
                "uploaded_by",
                "validated_by",
            )
        )

    @staticmethod
    def photo_base_queryset() -> QuerySet:
        return (
            AssetPhoto.objects
            .filter(is_deleted=False)
            .select_related(
                "uploaded_by",
                "validated_by",
            )
        )

    @staticmethod
    def _owner_filter(*, scope, actor_id=None, department_id=None):
        """Construye el filtro polimórfico para propietarios internos."""

        normalized_scope = DocumentScope.normalize(scope)
        if normalized_scope == DocumentScope.GLOBAL:
            return Q()

        if normalized_scope == DocumentScope.DEPARTMENT:
            if not department_id:
                return None

            asset_ids = Asset.objects.filter(
                is_deleted=False,
                current_dependencia_id=department_id,
            ).values("id")
            intake_ids = AssetIntakeRequest.objects.filter(
                is_deleted=False,
                requested_dependencia_id=department_id,
            ).values("id")
            custody_ids = CustodyAssignment.objects.filter(
                is_deleted=False,
                dependencia_id=department_id,
            ).values("id")
            movement_ids = InventoryMovement.objects.filter(
                is_deleted=False,
            ).filter(
                Q(from_dependencia_id=department_id)
                | Q(to_dependencia_id=department_id)
            ).values("id")
            loan_ids = AssetLoan.objects.filter(
                is_deleted=False,
                asset__current_dependencia_id=department_id,
            ).values("id")
            disposal_ids = DisposalRequest.objects.filter(
                is_deleted=False,
                asset__current_dependencia_id=department_id,
            ).values("id")
            audit_session_ids = PhysicalAuditSession.objects.filter(
                is_deleted=False,
                dependencia_id=department_id,
            ).values("id")
            audit_item_ids = PhysicalAuditItem.objects.filter(
                is_deleted=False,
                session__dependencia_id=department_id,
            ).values("id")

            return (
                Q(
                    owner_type=InventoryDocumentOwnerType.ASSET,
                    owner_id__in=asset_ids,
                )
                | Q(
                    owner_type=InventoryDocumentOwnerType.INTAKE_REQUEST,
                    owner_id__in=intake_ids,
                )
                | Q(
                    owner_type=(
                        InventoryDocumentOwnerType.CUSTODY_ASSIGNMENT
                    ),
                    owner_id__in=custody_ids,
                )
                | Q(
                    owner_type=InventoryDocumentOwnerType.MOVEMENT,
                    owner_id__in=movement_ids,
                )
                | Q(
                    owner_type=InventoryDocumentOwnerType.LOAN,
                    owner_id__in=loan_ids,
                )
                | Q(
                    owner_type=(
                        InventoryDocumentOwnerType.DISPOSAL_REQUEST
                    ),
                    owner_id__in=disposal_ids,
                )
                | Q(
                    owner_type=(
                        InventoryDocumentOwnerType.PHYSICAL_AUDIT_SESSION
                    ),
                    owner_id__in=audit_session_ids,
                )
                | Q(
                    owner_type=(
                        InventoryDocumentOwnerType.PHYSICAL_AUDIT_ITEM
                    ),
                    owner_id__in=audit_item_ids,
                )
            )

        if not actor_id:
            return None

        asset_ids = Asset.objects.filter(
            is_deleted=False,
            current_custodian_id=actor_id,
        ).values("id")
        intake_ids = AssetIntakeRequest.objects.filter(
            is_deleted=False,
            submitted_by_id=actor_id,
        ).values("id")
        custody_ids = CustodyAssignment.objects.filter(
            is_deleted=False,
            assigned_to_id=actor_id,
        ).values("id")
        movement_ids = InventoryMovement.objects.filter(
            is_deleted=False,
        ).filter(
            Q(performed_by_id=actor_id)
            | Q(from_user_id=actor_id)
            | Q(to_user_id=actor_id)
        ).values("id")
        loan_ids = AssetLoan.objects.filter(
            is_deleted=False,
        ).filter(
            Q(borrower_id=actor_id)
            | Q(requested_by_id=actor_id)
        ).values("id")
        disposal_ids = DisposalRequest.objects.filter(
            is_deleted=False,
            requested_by_id=actor_id,
        ).values("id")
        audit_session_ids = PhysicalAuditSession.objects.filter(
            is_deleted=False,
            started_by_id=actor_id,
        ).values("id")
        audit_item_ids = PhysicalAuditItem.objects.filter(
            is_deleted=False,
            scanned_by_id=actor_id,
        ).values("id")

        return (
            Q(uploaded_by_id=actor_id)
            | Q(
                owner_type=InventoryDocumentOwnerType.ASSET,
                owner_id__in=asset_ids,
            )
            | Q(
                owner_type=InventoryDocumentOwnerType.INTAKE_REQUEST,
                owner_id__in=intake_ids,
            )
            | Q(
                owner_type=InventoryDocumentOwnerType.CUSTODY_ASSIGNMENT,
                owner_id__in=custody_ids,
            )
            | Q(
                owner_type=InventoryDocumentOwnerType.MOVEMENT,
                owner_id__in=movement_ids,
            )
            | Q(
                owner_type=InventoryDocumentOwnerType.LOAN,
                owner_id__in=loan_ids,
            )
            | Q(
                owner_type=InventoryDocumentOwnerType.DISPOSAL_REQUEST,
                owner_id__in=disposal_ids,
            )
            | Q(
                owner_type=(
                    InventoryDocumentOwnerType.PHYSICAL_AUDIT_SESSION
                ),
                owner_id__in=audit_session_ids,
            )
            | Q(
                owner_type=InventoryDocumentOwnerType.PHYSICAL_AUDIT_ITEM,
                owner_id__in=audit_item_ids,
            )
        )

    @classmethod
    def visible_documents(
        cls,
        *,
        scope=DocumentScope.GLOBAL,
        actor_id=None,
        department_id=None,
        include_restricted=False,
    ) -> QuerySet:
        queryset = cls.document_base_queryset()
        owner_filter = cls._owner_filter(
            scope=scope,
            actor_id=actor_id,
            department_id=department_id,
        )

        if owner_filter is None:
            return queryset.none()

        queryset = queryset.filter(owner_filter)

        if not include_restricted:
            queryset = queryset.filter(
                access_level__in=(
                    DocumentAccessLevel.PUBLIC,
                    DocumentAccessLevel.INTERNAL,
                )
            )

        return queryset

    @classmethod
    def documents(
        cls,
        *,
        owner_type=None,
        owner_id=None,
        document_type=None,
        validation_status=None,
        q="",
        scope=DocumentScope.GLOBAL,
        actor_id=None,
        scope_department_id=None,
        include_restricted=False,
    ) -> QuerySet:
        queryset = cls.visible_documents(
            scope=scope,
            actor_id=actor_id,
            department_id=scope_department_id,
            include_restricted=include_restricted,
        )

        if owner_type:
            queryset = queryset.filter(owner_type=owner_type)

        if owner_id:
            queryset = queryset.filter(owner_id=owner_id)

        if document_type:
            queryset = queryset.filter(document_type=document_type)

        if validation_status:
            queryset = queryset.filter(validation_status=validation_status)

        normalized_query = str(q or "").strip()
        if normalized_query:
            queryset = queryset.filter(
                Q(title__icontains=normalized_query)
                | Q(original_filename__icontains=normalized_query)
                | Q(description__icontains=normalized_query)
                | Q(sha256_hash__iexact=normalized_query)
            )

        return queryset.order_by("-uploaded_at", "-created_at")

    @classmethod
    def obtener_documento(
        cls,
        document_id,
        *,
        scope=DocumentScope.GLOBAL,
        actor_id=None,
        department_id=None,
        include_restricted=False,
    ):
        return cls.visible_documents(
            scope=scope,
            actor_id=actor_id,
            department_id=department_id,
            include_restricted=include_restricted,
        ).get(pk=document_id)

    @classmethod
    def asset_documents(
        cls,
        asset_id,
        *,
        scope=DocumentScope.GLOBAL,
        actor_id=None,
        department_id=None,
        include_restricted=False,
    ) -> QuerySet:
        return cls.documents(
            owner_type=InventoryDocumentOwnerType.ASSET,
            owner_id=asset_id,
            scope=scope,
            actor_id=actor_id,
            scope_department_id=department_id,
            include_restricted=include_restricted,
        )

    @classmethod
    def pending_validation(
        cls,
        *,
        scope=DocumentScope.GLOBAL,
        actor_id=None,
        department_id=None,
        include_restricted=False,
    ) -> QuerySet:
        return cls.documents(
            validation_status=DocumentValidationStatus.PENDING,
            scope=scope,
            actor_id=actor_id,
            scope_department_id=department_id,
            include_restricted=include_restricted,
        )

    @classmethod
    def visible_photos(
        cls,
        *,
        scope=DocumentScope.GLOBAL,
        actor_id=None,
        department_id=None,
    ) -> QuerySet:
        queryset = cls.photo_base_queryset()
        owner_filter = cls._owner_filter(
            scope=scope,
            actor_id=actor_id,
            department_id=department_id,
        )

        if owner_filter is None:
            return queryset.none()

        return queryset.filter(owner_filter)

    @classmethod
    def photos(
        cls,
        *,
        owner_type=None,
        owner_id=None,
        photo_type=None,
        scope=DocumentScope.GLOBAL,
        actor_id=None,
        scope_department_id=None,
    ) -> QuerySet:
        queryset = cls.visible_photos(
            scope=scope,
            actor_id=actor_id,
            department_id=scope_department_id,
        )

        if owner_type:
            queryset = queryset.filter(owner_type=owner_type)

        if owner_id:
            queryset = queryset.filter(owner_id=owner_id)

        if photo_type:
            queryset = queryset.filter(photo_type=photo_type)

        return queryset.order_by("-uploaded_at", "-created_at")

    @classmethod
    def obtener_fotografia(
        cls,
        photo_id,
        *,
        scope=DocumentScope.GLOBAL,
        actor_id=None,
        department_id=None,
    ):
        return cls.visible_photos(
            scope=scope,
            actor_id=actor_id,
            department_id=department_id,
        ).get(pk=photo_id)

    @classmethod
    def asset_photos(
        cls,
        asset_id,
        *,
        scope=DocumentScope.GLOBAL,
        actor_id=None,
        department_id=None,
    ) -> QuerySet:
        return cls.photos(
            owner_type=InventoryDocumentOwnerType.ASSET,
            owner_id=asset_id,
            scope=scope,
            actor_id=actor_id,
            scope_department_id=department_id,
        )


__all__ = ["DocumentScope", "DocumentSelectors"]
