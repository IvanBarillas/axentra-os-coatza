
# apps/inventory/admin/asset_admin.py

from django.contrib import admin

from apps.inventory.models import (
    AccountingAccount,
    AccountingExportBatch,
    Asset,
    AssetCategory,
    AssetDocument,
    AssetModel,
    AssetPhoto,
    AssetRelation,
    Consumable,
    ConsumableMovement,
    Contract,
    CustodyAssignment,
    DepreciationPolicy,
    DepreciationRecord,
    DisposalRequest,
    ImmovableAssetDetail,
    InventoryAuditLog,
    InventoryMovement,
    Manufacturer,
    PhysicalAuditItem,
    PhysicalAuditSession,
    Supplier,
    TechnicalAssetProfile,
)


class InventoryBaseAdmin(admin.ModelAdmin):
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )

    list_filter = (
        "is_active",
        "is_deleted",
    )


@admin.register(AssetCategory)
class AssetCategoryAdmin(InventoryBaseAdmin):
    list_display = (
        "code",
        "name",
        "nature",
        "is_active",
        "is_deleted",
    )
    search_fields = (
        "code",
        "name",
        "description",
    )
    list_filter = (
        "nature",
        "is_active",
        "is_deleted",
    )


@admin.register(AccountingAccount)
class AccountingAccountAdmin(InventoryBaseAdmin):
    list_display = (
        "code",
        "name",
        "category",
        "is_depreciable",
        "default_useful_life_months",
        "default_annual_depreciation_rate",
        "is_active",
    )
    search_fields = (
        "code",
        "name",
        "category__name",
    )
    list_filter = (
        "is_depreciable",
        "category",
        "is_active",
        "is_deleted",
    )


@admin.register(Manufacturer)
class ManufacturerAdmin(InventoryBaseAdmin):
    list_display = (
        "name",
        "is_active",
        "is_deleted",
    )
    search_fields = (
        "name",
    )


@admin.register(AssetModel)
class AssetModelAdmin(InventoryBaseAdmin):
    list_display = (
        "manufacturer",
        "name",
        "is_active",
        "is_deleted",
    )
    search_fields = (
        "manufacturer__name",
        "name",
        "description",
    )
    list_filter = (
        "manufacturer",
        "is_active",
        "is_deleted",
    )


@admin.register(Supplier)
class SupplierAdmin(InventoryBaseAdmin):
    list_display = (
        "razon_social",
        "rfc",
        "contacto_nombre",
        "telefono",
        "email",
        "is_active",
    )
    search_fields = (
        "razon_social",
        "rfc",
        "contacto_nombre",
        "telefono",
        "email",
    )
    list_filter = (
        "is_active",
        "is_deleted",
    )


@admin.register(Contract)
class ContractAdmin(InventoryBaseAdmin):
    list_display = (
        "numero_contrato",
        "nombre",
        "supplier",
        "fecha_inicio",
        "fecha_fin",
        "monto_total",
        "is_active",
    )
    search_fields = (
        "numero_contrato",
        "nombre",
        "supplier__razon_social",
        "supplier__rfc",
    )
    list_filter = (
        "supplier",
        "fecha_inicio",
        "fecha_fin",
        "is_active",
        "is_deleted",
    )


class TechnicalAssetProfileInline(admin.StackedInline):
    model = TechnicalAssetProfile
    extra = 0
    can_delete = True
    show_change_link = True
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )


class ImmovableAssetDetailInline(admin.StackedInline):
    model = ImmovableAssetDetail
    extra = 0
    can_delete = True
    show_change_link = True
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )


class AssetPhotoInline(admin.TabularInline):
    model = AssetPhoto
    extra = 0
    show_change_link = True
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )


class AssetDocumentInline(admin.TabularInline):
    model = AssetDocument
    extra = 0
    show_change_link = True
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )


@admin.register(Asset)
class AssetAdmin(InventoryBaseAdmin):
    list_display = (
        "inventory_number",
        "name",
        "category",
        "control_type",
        "lifecycle_status",
        "physical_condition",
        "is_capitalizable",
        "acquisition_cost",
        "sede",
        "dependencia",
        "area",
        "current_custodian",
        "is_active",
    )

    search_fields = (
        "inventory_number",
        "legacy_inventory_number",
        "name",
        "description",
        "serial_number",
        "manufacturer__name",
        "model__name",
        "supplier__razon_social",
        "current_custodian__email",
        "current_custodian__first_name",
        "current_custodian__last_name",
        "sede__nombre",
        "dependencia__nombre",
        "area__nombre",
    )

    list_filter = (
        "control_type",
        "lifecycle_status",
        "physical_condition",
        "is_capitalizable",
        "category",
        "accounting_account",
        "manufacturer",
        "sede",
        "dependencia",
        "area",
        "is_active",
        "is_deleted",
    )

    readonly_fields = (
        "id",
        "depreciable_base",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            "Identidad patrimonial",
            {
                "fields": (
                    "id",
                    "inventory_number",
                    "legacy_inventory_number",
                    "name",
                    "description",
                )
            },
        ),
        (
            "Clasificación CONAC / control",
            {
                "fields": (
                    "category",
                    "accounting_account",
                    "control_type",
                    "lifecycle_status",
                    "physical_condition",
                    "acquisition_type",
                )
            },
        ),
        (
            "Información financiera",
            {
                "fields": (
                    "acquisition_date",
                    "registration_date",
                    "acquisition_cost",
                    "residual_value",
                    "depreciable_base",
                    "useful_life_months",
                    "is_capitalizable",
                    "capitalization_threshold_amount",
                )
            },
        ),
        (
            "Marca, modelo y proveedor",
            {
                "fields": (
                    "manufacturer",
                    "model",
                    "serial_number",
                    "supplier",
                    "contract",
                )
            },
        ),
        (
            "Ubicación y resguardo",
            {
                "fields": (
                    "sede",
                    "dependencia",
                    "area",
                    "current_custodian",
                    "latitude",
                    "longitude",
                )
            },
        ),
        (
            "Notas y atributos extendidos",
            {
                "fields": (
                    "notes",
                    "extra_attributes",
                )
            },
        ),
        (
            "Control del sistema",
            {
                "fields": (
                    "is_active",
                    "is_deleted",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    inlines = (
        TechnicalAssetProfileInline,
        ImmovableAssetDetailInline,
        AssetPhotoInline,
        AssetDocumentInline,
    )


@admin.register(ImmovableAssetDetail)
class ImmovableAssetDetailAdmin(InventoryBaseAdmin):
    list_display = (
        "asset",
        "cadastral_key",
        "deed_number",
        "surface_m2",
        "legal_status",
        "is_active",
    )
    search_fields = (
        "asset__inventory_number",
        "asset__name",
        "cadastral_key",
        "public_registry_record",
        "deed_number",
        "legal_status",
    )
    list_filter = (
        "is_active",
        "is_deleted",
    )


@admin.register(TechnicalAssetProfile)
class TechnicalAssetProfileAdmin(InventoryBaseAdmin):
    list_display = (
        "asset",
        "technical_type",
        "hostname",
        "ip_address",
        "mac_address",
        "operating_system",
        "warranty_end_date",
        "is_active",
    )
    search_fields = (
        "asset__inventory_number",
        "asset__name",
        "hostname",
        "ip_address",
        "mac_address",
        "operating_system",
        "processor",
        "ssid",
        "extension_number",
        "phone_number",
    )
    list_filter = (
        "technical_type",
        "operating_system",
        "warranty_end_date",
        "is_active",
        "is_deleted",
    )


@admin.register(AssetRelation)
class AssetRelationAdmin(InventoryBaseAdmin):
    list_display = (
        "parent_asset",
        "relation_type",
        "child_asset",
        "is_active",
    )
    search_fields = (
        "parent_asset__inventory_number",
        "parent_asset__name",
        "child_asset__inventory_number",
        "child_asset__name",
        "notes",
    )
    list_filter = (
        "relation_type",
        "is_active",
        "is_deleted",
    )


@admin.register(CustodyAssignment)
class CustodyAssignmentAdmin(InventoryBaseAdmin):
    list_display = (
        "folio",
        "asset",
        "assigned_to",
        "assigned_by",
        "status",
        "dependencia",
        "area",
        "sede",
        "assigned_at",
        "signed_at",
        "returned_at",
        "is_active",
    )
    search_fields = (
        "folio",
        "asset__inventory_number",
        "asset__name",
        "assigned_to__email",
        "assigned_to__first_name",
        "assigned_to__last_name",
        "assigned_by__email",
        "dependencia__nombre",
        "area__nombre",
        "sede__nombre",
        "notes",
    )
    list_filter = (
        "status",
        "dependencia",
        "area",
        "sede",
        "assigned_at",
        "signed_at",
        "returned_at",
        "is_active",
        "is_deleted",
    )


@admin.register(InventoryMovement)
class InventoryMovementAdmin(InventoryBaseAdmin):
    list_display = (
        "asset",
        "movement_type",
        "from_dependencia",
        "to_dependencia",
        "from_user",
        "to_user",
        "performed_by",
        "reference_folio",
        "created_at",
    )
    search_fields = (
        "asset__inventory_number",
        "asset__name",
        "reference_folio",
        "reason",
        "performed_by__email",
        "from_user__email",
        "to_user__email",
    )
    list_filter = (
        "movement_type",
        "from_dependencia",
        "to_dependencia",
        "from_area",
        "to_area",
        "from_sede",
        "to_sede",
        "created_at",
        "is_active",
        "is_deleted",
    )


@admin.register(DisposalRequest)
class DisposalRequestAdmin(InventoryBaseAdmin):
    list_display = (
        "folio",
        "asset",
        "reason",
        "status",
        "requested_by",
        "reviewed_by",
        "approved_by",
        "requested_at",
        "approved_at",
        "executed_at",
        "is_active",
    )
    search_fields = (
        "folio",
        "asset__inventory_number",
        "asset__name",
        "requested_by__email",
        "reviewed_by__email",
        "approved_by__email",
        "description",
        "legal_reference",
    )
    list_filter = (
        "reason",
        "status",
        "requested_at",
        "approved_at",
        "executed_at",
        "is_active",
        "is_deleted",
    )


@admin.register(DepreciationPolicy)
class DepreciationPolicyAdmin(InventoryBaseAdmin):
    list_display = (
        "name",
        "accounting_account",
        "method",
        "frequency",
        "useful_life_months",
        "residual_percentage",
        "is_active",
    )
    search_fields = (
        "name",
        "accounting_account__code",
        "accounting_account__name",
    )
    list_filter = (
        "method",
        "frequency",
        "accounting_account",
        "is_active",
        "is_deleted",
    )


@admin.register(DepreciationRecord)
class DepreciationRecordAdmin(InventoryBaseAdmin):
    list_display = (
        "asset",
        "policy",
        "period_year",
        "period_month",
        "original_value",
        "depreciation_amount",
        "accumulated_depreciation",
        "book_value",
        "calculated_by",
        "calculated_at",
    )
    search_fields = (
        "asset__inventory_number",
        "asset__name",
        "policy__name",
        "calculated_by__email",
    )
    list_filter = (
        "period_year",
        "period_month",
        "policy",
        "calculated_at",
        "is_active",
        "is_deleted",
    )
    readonly_fields = (
        "id",
        "calculated_at",
        "created_at",
        "updated_at",
    )


@admin.register(AccountingExportBatch)
class AccountingExportBatchAdmin(InventoryBaseAdmin):
    list_display = (
        "export_type",
        "period_start",
        "period_end",
        "generated_by",
        "generated_file",
        "created_at",
    )
    search_fields = (
        "generated_by__email",
        "generated_by__first_name",
        "generated_by__last_name",
    )
    list_filter = (
        "export_type",
        "period_start",
        "period_end",
        "created_at",
        "is_active",
        "is_deleted",
    )


@admin.register(AssetDocument)
class AssetDocumentAdmin(InventoryBaseAdmin):
    list_display = (
        "title",
        "document_type",
        "asset",
        "custody_assignment",
        "disposal_request",
        "movement",
        "uploaded_by",
        "created_at",
        "is_active",
    )
    search_fields = (
        "title",
        "asset__inventory_number",
        "asset__name",
        "custody_assignment__folio",
        "disposal_request__folio",
        "movement__reference_folio",
        "uploaded_by__email",
        "sha256_hash",
        "notes",
    )
    list_filter = (
        "document_type",
        "uploaded_by",
        "created_at",
        "is_active",
        "is_deleted",
    )


@admin.register(AssetPhoto)
class AssetPhotoAdmin(InventoryBaseAdmin):
    list_display = (
        "asset",
        "photo_type",
        "caption",
        "uploaded_by",
        "created_at",
        "is_active",
    )
    search_fields = (
        "asset__inventory_number",
        "asset__name",
        "caption",
        "uploaded_by__email",
    )
    list_filter = (
        "photo_type",
        "uploaded_by",
        "created_at",
        "is_active",
        "is_deleted",
    )


@admin.register(PhysicalAuditSession)
class PhysicalAuditSessionAdmin(InventoryBaseAdmin):
    list_display = (
        "folio",
        "name",
        "status",
        "sede",
        "dependencia",
        "area",
        "started_by",
        "closed_by",
        "started_at",
        "closed_at",
        "is_active",
    )
    search_fields = (
        "folio",
        "name",
        "started_by__email",
        "closed_by__email",
        "sede__nombre",
        "dependencia__nombre",
        "area__nombre",
        "notes",
    )
    list_filter = (
        "status",
        "sede",
        "dependencia",
        "area",
        "started_at",
        "closed_at",
        "is_active",
        "is_deleted",
    )


@admin.register(PhysicalAuditItem)
class PhysicalAuditItemAdmin(InventoryBaseAdmin):
    list_display = (
        "session",
        "asset",
        "scanned_inventory_number",
        "result",
        "scanned_by",
        "scanned_at",
        "is_active",
    )
    search_fields = (
        "session__folio",
        "asset__inventory_number",
        "asset__name",
        "scanned_inventory_number",
        "scanned_by__email",
        "notes",
    )
    list_filter = (
        "result",
        "scanned_by",
        "scanned_at",
        "is_active",
        "is_deleted",
    )
    readonly_fields = (
        "id",
        "scanned_at",
        "created_at",
        "updated_at",
    )


@admin.register(InventoryAuditLog)
class InventoryAuditLogAdmin(InventoryBaseAdmin):
    list_display = (
        "action_type",
        "actor",
        "asset",
        "target_model",
        "target_id",
        "summary",
        "created_at",
    )
    search_fields = (
        "action_type",
        "actor__email",
        "asset__inventory_number",
        "asset__name",
        "target_model",
        "target_id",
        "summary",
    )
    list_filter = (
        "action_type",
        "target_model",
        "created_at",
        "is_active",
        "is_deleted",
    )
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )


@admin.register(Consumable)
class ConsumableAdmin(InventoryBaseAdmin):
    list_display = (
        "code",
        "name",
        "dependencia",
        "sede",
        "stock_actual",
        "stock_minimo",
        "unit",
        "is_active",
    )
    search_fields = (
        "code",
        "name",
        "dependencia__nombre",
        "sede__nombre",
    )
    list_filter = (
        "dependencia",
        "sede",
        "unit",
        "is_active",
        "is_deleted",
    )


@admin.register(ConsumableMovement)
class ConsumableMovementAdmin(InventoryBaseAdmin):
    list_display = (
        "consumable",
        "movement_type",
        "quantity",
        "operator",
        "related_asset",
        "reference",
        "created_at",
    )
    search_fields = (
        "consumable__code",
        "consumable__name",
        "operator__email",
        "related_asset__inventory_number",
        "related_asset__name",
        "reference",
        "reason",
    )
    list_filter = (
        "movement_type",
        "operator",
        "created_at",
        "is_active",
        "is_deleted",
    )