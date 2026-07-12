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
    Contract,
    CustodyAssignment,
    DepreciationPolicy,
    DepreciationRecord,
    DisposalRequest,
    ImmovableAssetDetail,
    InventoryAuditLog,
    InventoryFolioSequence,
    InventoryMovement,
    Manufacturer,
    PhysicalAuditItem,
    PhysicalAuditSession,
    Supplier,
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
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
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
        "category__code",
        "category__name",
    )
    list_filter = (
        "is_depreciable",
        "category",
        "is_active",
        "is_deleted",
    )
    autocomplete_fields = (
        "category",
    )
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
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
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
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
    autocomplete_fields = (
        "manufacturer",
    )
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
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
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
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
    autocomplete_fields = (
        "supplier",
    )
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )


@admin.register(InventoryFolioSequence)
class InventoryFolioSequenceAdmin(InventoryBaseAdmin):
    list_display = (
        "municipality_code",
        "year",
        "conac_code",
        "dependency_code",
        "asset_type_code",
        "current_number",
        "sequence_preview",
        "is_active",
    )
    search_fields = (
        "municipality_code",
        "conac_code",
        "dependency_code",
        "asset_type_code",
    )
    list_filter = (
        "municipality_code",
        "year",
        "conac_code",
        "dependency_code",
        "asset_type_code",
        "is_active",
        "is_deleted",
    )
    fields = (
        "id",
        "municipality_code",
        "year",
        "conac_code",
        "dependency_code",
        "asset_type_code",
        "current_number",
        "is_active",
        "is_deleted",
        "created_at",
        "updated_at",
    )
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )

    def sequence_preview(self, obj):
        return str(obj)

    sequence_preview.short_description = "Vista previa"


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
        "display_inventory_number",
        "official_inventory_number",
        "internal_inventory_number",
        "legacy_inventory_number",
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
        "official_inventory_number",
        "internal_inventory_number",
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

    autocomplete_fields = (
        "category",
        "accounting_account",
        "manufacturer",
        "model",
        "supplier",
        "contract",
        "sede",
        "dependencia",
        "area",
        "current_custodian",
    )

    readonly_fields = (
        "id",
        "display_inventory_number",
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
                    "display_inventory_number",
                    "official_inventory_number",
                    "internal_inventory_number",
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
        ImmovableAssetDetailInline,
        AssetPhotoInline,
        AssetDocumentInline,
    )


@admin.register(ImmovableAssetDetail)
class ImmovableAssetDetailAdmin(InventoryBaseAdmin):
    list_display = (
        "asset",
        "asset_folio",
        "cadastral_key",
        "deed_number",
        "surface_m2",
        "legal_status",
        "is_active",
    )
    search_fields = (
        "asset__official_inventory_number",
        "asset__internal_inventory_number",
        "asset__legacy_inventory_number",
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
    autocomplete_fields = (
        "asset",
    )
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )

    def asset_folio(self, obj):
        return obj.asset.display_inventory_number if obj.asset else "SIN-FOLIO"

    asset_folio.short_description = "Folio"


@admin.register(CustodyAssignment)
class CustodyAssignmentAdmin(InventoryBaseAdmin):
    list_display = (
        "folio",
        "asset_folio",
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
        "asset__official_inventory_number",
        "asset__internal_inventory_number",
        "asset__legacy_inventory_number",
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
    autocomplete_fields = (
        "asset",
        "assigned_to",
        "assigned_by",
        "dependencia",
        "area",
        "sede",
    )
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )

    def asset_folio(self, obj):
        return obj.asset.display_inventory_number if obj.asset else "SIN-FOLIO"

    asset_folio.short_description = "Folio activo"


@admin.register(InventoryMovement)
class InventoryMovementAdmin(InventoryBaseAdmin):
    list_display = (
        "asset_folio",
        "asset",
        "movement_type",
        "from_dependencia",
        "to_dependencia",
        "from_user",
        "to_user",
        "performed_by",
        "reference_folio",
        "created_at",
        "is_active",
    )
    search_fields = (
        "asset__official_inventory_number",
        "asset__internal_inventory_number",
        "asset__legacy_inventory_number",
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
    autocomplete_fields = (
        "asset",
        "from_dependencia",
        "to_dependencia",
        "from_area",
        "to_area",
        "from_sede",
        "to_sede",
        "from_user",
        "to_user",
        "performed_by",
    )
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )

    def asset_folio(self, obj):
        return obj.asset.display_inventory_number if obj.asset else "SIN-FOLIO"

    asset_folio.short_description = "Folio"


@admin.register(DisposalRequest)
class DisposalRequestAdmin(InventoryBaseAdmin):
    list_display = (
        "folio",
        "asset_folio",
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
        "asset__official_inventory_number",
        "asset__internal_inventory_number",
        "asset__legacy_inventory_number",
        "asset__name",
        "requested_by__email",
        "reviewed_by__email",
        "approved_by__email",
        "description",
        "legal_reference",
        #"source_app",
        "source_model",
        "source_object_id",
    )
    list_filter = (
        "reason",
        "status",
        "requested_at",
        "approved_at",
        "executed_at",
        #"source_app",
        "is_active",
        "is_deleted",
    )
    autocomplete_fields = (
        "asset",
        "requested_by",
        "reviewed_by",
        "approved_by",
    )
    readonly_fields = (
        "id",
        "requested_at",
        "created_at",
        "updated_at",
    )

    def asset_folio(self, obj):
        return obj.asset.display_inventory_number if obj.asset else "SIN-FOLIO"

    asset_folio.short_description = "Folio"


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
    autocomplete_fields = (
        "accounting_account",
    )
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )


@admin.register(DepreciationRecord)
class DepreciationRecordAdmin(InventoryBaseAdmin):
    list_display = (
        "asset_folio",
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
        "asset__official_inventory_number",
        "asset__internal_inventory_number",
        "asset__legacy_inventory_number",
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
    autocomplete_fields = (
        "asset",
        "policy",
        "calculated_by",
    )
    readonly_fields = (
        "id",
        "calculated_at",
        "created_at",
        "updated_at",
    )

    def asset_folio(self, obj):
        return obj.asset.display_inventory_number if obj.asset else "SIN-FOLIO"

    asset_folio.short_description = "Folio"


@admin.register(AccountingExportBatch)
class AccountingExportBatchAdmin(InventoryBaseAdmin):
    list_display = (
        "export_type",
        "period_start",
        "period_end",
        "generated_by",
        "generated_file",
        "created_at",
        "is_active",
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
    autocomplete_fields = (
        "generated_by",
    )
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )


@admin.register(AssetDocument)
class AssetDocumentAdmin(InventoryBaseAdmin):
    list_display = (
        "title",
        "document_type",
        "asset_folio",
        "asset",
        "custody_assignment",
        "disposal_request",
        "movement",
        "uploaded_by",
        #"source_app",
        "created_at",
        "is_active",
    )
    search_fields = (
        "title",
        "asset__official_inventory_number",
        "asset__internal_inventory_number",
        "asset__legacy_inventory_number",
        "asset__name",
        "custody_assignment__folio",
        "disposal_request__folio",
        "movement__reference_folio",
        "uploaded_by__email",
        "sha256_hash",
        #"source_app",
        "source_model",
        "source_object_id",
        "notes",
    )
    list_filter = (
        "document_type",
        "uploaded_by",
        #"source_app",
        "created_at",
        "is_active",
        "is_deleted",
    )
    autocomplete_fields = (
        "asset",
        "custody_assignment",
        "disposal_request",
        "movement",
        "uploaded_by",
    )
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )

    def asset_folio(self, obj):
        return obj.asset.display_inventory_number if obj.asset else "SIN-FOLIO"

    asset_folio.short_description = "Folio"


@admin.register(AssetPhoto)
class AssetPhotoAdmin(InventoryBaseAdmin):
    list_display = (
        "asset_folio",
        "asset",
        "photo_type",
        "caption",
        "uploaded_by",
        "created_at",
        "is_active",
    )
    search_fields = (
        "asset__official_inventory_number",
        "asset__internal_inventory_number",
        "asset__legacy_inventory_number",
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
    autocomplete_fields = (
        "asset",
        "uploaded_by",
    )
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )

    def asset_folio(self, obj):
        return obj.asset.display_inventory_number if obj.asset else "SIN-FOLIO"

    asset_folio.short_description = "Folio"


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
    autocomplete_fields = (
        "sede",
        "dependencia",
        "area",
        "started_by",
        "closed_by",
    )
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )


@admin.register(PhysicalAuditItem)
class PhysicalAuditItemAdmin(InventoryBaseAdmin):
    list_display = (
        "session",
        "asset_folio",
        "asset",
        "scanned_inventory_number",
        "result",
        "scanned_by",
        "scanned_at",
        "is_active",
    )
    search_fields = (
        "session__folio",
        "asset__official_inventory_number",
        "asset__internal_inventory_number",
        "asset__legacy_inventory_number",
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
    autocomplete_fields = (
        "session",
        "asset",
        "scanned_by",
    )
    readonly_fields = (
        "id",
        "scanned_at",
        "created_at",
        "updated_at",
    )

    def asset_folio(self, obj):
        if obj.asset:
            return obj.asset.display_inventory_number

        return obj.scanned_inventory_number or "SIN-FOLIO"

    asset_folio.short_description = "Folio"


@admin.register(InventoryAuditLog)
class InventoryAuditLogAdmin(InventoryBaseAdmin):
    list_display = (
        "action_type",
        "actor",
        "asset_folio",
        "asset",
        "target_model",
        "target_id",
        "summary",
        "created_at",
    )
    search_fields = (
        "action_type",
        "actor__email",
        "asset__official_inventory_number",
        "asset__internal_inventory_number",
        "asset__legacy_inventory_number",
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
    autocomplete_fields = (
        "actor",
        "asset",
    )
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )

    def asset_folio(self, obj):
        return obj.asset.display_inventory_number if obj.asset else "SIN-FOLIO"

    asset_folio.short_description = "Folio"
    
