# apps/inventory/management/commands/seed_inventory_catalogs.py

from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.inventory.models import (
    AccountingAccount,
    AccountingAccountType,
    AssetCategory,
    AssetModel,
    AssetNature,
    CapitalizationRule,
    DepreciationFrequency,
    DepreciationMethod,
    DepreciationPolicy,
    ExpenditureObject,
    InventoryAssetTypeCode,
    InventoryFolioPolicy,
    Manufacturer,
    UmaValue,
)


class Command(BaseCommand):
    help = (
        "Siembra catálogos base de Inventory de forma idempotente. "
        "No crea activos ni operaciones patrimoniales de prueba."
    )

    MUNICIPALITY_CODE = "039"
    MUNICIPALITY_NAME = "COATZACOALCOS"
    BASE_YEAR = 2026
    UMA_DAILY_VALUE = Decimal("117.3100")

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "\n=== INVENTORY: CATÁLOGOS BASE ==="
            )
        )

        categories = self._seed_categories()
        accounts = self._seed_accounting_accounts(categories)
        self._seed_expenditure_objects(categories, accounts)
        self._seed_uma_values()
        self._seed_manufacturers_and_models()
        self._seed_folio_policy()
        self._seed_depreciation_policies(categories, accounts)

        self.stdout.write(
            self.style.SUCCESS(
                "\nCatálogos de Inventory sembrados correctamente.\n"
            )
        )

    def _upsert(self, model, lookup, defaults):
        """
        Crea o actualiza un catálogo y reactiva registros eliminados
        lógicamente. Ejecuta las validaciones del modelo antes de guardar.
        """

        initial_defaults = {
            **defaults,
            "is_active": True,
            "is_deleted": False,
            "deleted_at": None,
        }

        obj, created = model.objects.get_or_create(
            **lookup,
            defaults=initial_defaults,
        )

        for field_name, value in defaults.items():
            setattr(obj, field_name, value)

        obj.is_active = True
        obj.is_deleted = False
        obj.deleted_at = None
        obj.full_clean()
        obj.save()

        action = "creado" if created else "actualizado"
        self.stdout.write(
            f"  - {model._meta.verbose_name}: {obj} ({action})"
        )

        return obj

    def _seed_categories(self):
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "\n1. Categorías patrimoniales"
            )
        )

        rows = [
            {
                "code": "COMPUTO_TI",
                "name": "EQUIPO DE CÓMPUTO Y TECNOLOGÍAS DE INFORMACIÓN",
                "nature": AssetNature.MOVABLE,
                "description": (
                    "Computadoras, servidores, periféricos y equipo "
                    "relacionado con tecnologías de información."
                ),
                "requires_serial_number": True,
                "requires_photographic_evidence": True,
                "requires_custody_assignment": True,
            },
            {
                "code": "MOBILIARIO",
                "name": "MOBILIARIO Y EQUIPO DE ADMINISTRACIÓN",
                "nature": AssetNature.MOVABLE,
                "description": (
                    "Muebles de oficina, estantería y equipo "
                    "administrativo."
                ),
                "requires_serial_number": False,
                "requires_photographic_evidence": True,
                "requires_custody_assignment": True,
            },
            {
                "code": "VEHICULOS",
                "name": "VEHÍCULOS Y EQUIPO DE TRANSPORTE",
                "nature": AssetNature.MOVABLE,
                "description": (
                    "Vehículos terrestres y equipo de transporte."
                ),
                "requires_serial_number": True,
                "requires_photographic_evidence": True,
                "requires_custody_assignment": True,
            },
            {
                "code": "INMUEBLES",
                "name": "BIENES INMUEBLES",
                "nature": AssetNature.IMMOVABLE,
                "description": (
                    "Terrenos, edificios y demás bienes inmuebles."
                ),
                "requires_serial_number": False,
                "requires_photographic_evidence": True,
                "requires_custody_assignment": False,
            },
            {
                "code": "SOFTWARE",
                "name": "SOFTWARE Y ACTIVOS INTANGIBLES",
                "nature": AssetNature.INTANGIBLE,
                "description": (
                    "Licencias, derechos de uso y otros activos "
                    "intangibles identificables."
                ),
                "requires_serial_number": True,
                "requires_photographic_evidence": False,
                "requires_custody_assignment": True,
            },
        ]

        categories = {}

        for row in rows:
            code = row["code"]
            categories[code] = self._upsert(
                AssetCategory,
                {"code": code},
                {key: value for key, value in row.items() if key != "code"},
            )

        return categories

    def _seed_accounting_accounts(self, categories):
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "\n2. Cuentas contables"
            )
        )

        rows = [
            {
                "code": "1.2.4.1.3",
                "name": (
                    "EQUIPO DE CÓMPUTO Y DE TECNOLOGÍAS "
                    "DE LA INFORMACIÓN"
                ),
                "account_type": AccountingAccountType.ASSET,
                "category": categories["COMPUTO_TI"],
                "is_depreciable": True,
                "default_useful_life_months": 36,
                "default_annual_depreciation_rate": Decimal("33.333"),
                "external_system_code": "1.2.4.1.3",
            },
            {
                "code": "1.2.4.1.1",
                "name": "MUEBLES DE OFICINA Y ESTANTERÍA",
                "account_type": AccountingAccountType.ASSET,
                "category": categories["MOBILIARIO"],
                "is_depreciable": True,
                "default_useful_life_months": 120,
                "default_annual_depreciation_rate": Decimal("10.000"),
                "external_system_code": "1.2.4.1.1",
            },
        ]

        accounts = {}

        for row in rows:
            code = row["code"]
            accounts[code] = self._upsert(
                AccountingAccount,
                {"code": code},
                {key: value for key, value in row.items() if key != "code"},
            )

        return accounts

    def _seed_expenditure_objects(self, categories, accounts):
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "\n3. Clasificador por Objeto del Gasto"
            )
        )

        rows = [
            {
                "code": "5151",
                "name": (
                    "EQUIPO DE CÓMPUTO Y DE TECNOLOGÍAS "
                    "DE LA INFORMACIÓN"
                ),
                "description": (
                    "Objeto del gasto asociado a equipo de cómputo "
                    "y tecnologías de información."
                ),
                "category": categories["COMPUTO_TI"],
                "accounting_account": accounts["1.2.4.1.3"],
                "default_asset_type_code": InventoryAssetTypeCode.BM,
                "capitalization_rule": CapitalizationRule.UMA_THRESHOLD,
                "uma_multiplier": Decimal("70.00"),
                "requires_inventory_control": True,
                "requires_accounting_reconciliation": True,
                "external_system_code": "5151",
            },
            {
                "code": "5111",
                "name": "MUEBLES DE OFICINA Y ESTANTERÍA",
                "description": (
                    "Objeto del gasto asociado a mobiliario y "
                    "equipo de administración."
                ),
                "category": categories["MOBILIARIO"],
                "accounting_account": accounts["1.2.4.1.1"],
                "default_asset_type_code": InventoryAssetTypeCode.BM,
                "capitalization_rule": CapitalizationRule.UMA_THRESHOLD,
                "uma_multiplier": Decimal("70.00"),
                "requires_inventory_control": True,
                "requires_accounting_reconciliation": True,
                "external_system_code": "5111",
            },
        ]

        for row in rows:
            code = row["code"]
            self._upsert(
                ExpenditureObject,
                {"code": code},
                {key: value for key, value in row.items() if key != "code"},
            )

    def _seed_uma_values(self):
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "\n4. Valores UMA"
            )
        )

        self._upsert(
            UmaValue,
            {"year": self.BASE_YEAR},
            {
                "daily_value": self.UMA_DAILY_VALUE,
                "effective_from": date(self.BASE_YEAR, 1, 1),
                "effective_until": date(self.BASE_YEAR, 12, 31),
                "publication_date": None,
                "source_reference": (
                    "VALOR BASE DE CONFIGURACIÓN; VALIDAR CONTRA "
                    "PUBLICACIÓN OFICIAL ANTES DE PRODUCCIÓN"
                ),
                "source_url": "",
            },
        )

    def _seed_manufacturers_and_models(self):
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "\n5. Fabricantes y modelos"
            )
        )

        rows = {
            "DELL": ["OPTIPLEX", "LATITUDE", "POWEREDGE"],
            "HP": ["PRODESK", "ELITEBOOK", "PROLIANT"],
            "LENOVO": ["THINKCENTRE", "THINKPAD"],
        }

        for manufacturer_name, model_names in rows.items():
            manufacturer = self._upsert(
                Manufacturer,
                {"name": manufacturer_name},
                {},
            )

            for model_name in model_names:
                self._upsert(
                    AssetModel,
                    {
                        "manufacturer": manufacturer,
                        "name": model_name,
                    },
                    {"description": "CATÁLOGO BASE DE DESARROLLO"},
                )

    def _seed_folio_policy(self):
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "\n6. Política institucional de folios"
            )
        )

        self._upsert(
            InventoryFolioPolicy,
            {
                "municipality_code": self.MUNICIPALITY_CODE,
                "effective_from": date(self.BASE_YEAR, 1, 1),
            },
            {
                "name": "FOLIO PATRIMONIAL COATZACOALCOS",
                "municipality_name": self.MUNICIPALITY_NAME,
                "format_template": (
                    "{municipality}-{year_short}-{conac}-"
                    "{dependency}-{asset_type}-{progressive}"
                ),
                "progressive_length": 4,
                "effective_until": None,
            },
        )

    def _seed_depreciation_policies(self, categories, accounts):
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "\n7. Políticas de depreciación"
            )
        )

        rows = [
            {
                "policy_code": "DEP-COMPUTO",
                "version_number": 1,
                "name": "DEPRECIACIÓN DE EQUIPO DE CÓMPUTO",
                "accounting_account": accounts["1.2.4.1.3"],
                "category": categories["COMPUTO_TI"],
                "method": DepreciationMethod.STRAIGHT_LINE,
                "frequency": DepreciationFrequency.MONTHLY,
                "useful_life_months": 36,
                "residual_percentage": Decimal("0.000"),
                "effective_from": date(self.BASE_YEAR, 1, 1),
                "effective_until": None,
                "source_reference": (
                    "POLÍTICA BASE; VALIDAR NORMATIVIDAD APLICABLE"
                ),
                "calculation_settings": {},
            },
            {
                "policy_code": "DEP-MOBILIARIO",
                "version_number": 1,
                "name": "DEPRECIACIÓN DE MOBILIARIO",
                "accounting_account": accounts["1.2.4.1.1"],
                "category": categories["MOBILIARIO"],
                "method": DepreciationMethod.STRAIGHT_LINE,
                "frequency": DepreciationFrequency.MONTHLY,
                "useful_life_months": 120,
                "residual_percentage": Decimal("0.000"),
                "effective_from": date(self.BASE_YEAR, 1, 1),
                "effective_until": None,
                "source_reference": (
                    "POLÍTICA BASE; VALIDAR NORMATIVIDAD APLICABLE"
                ),
                "calculation_settings": {},
            },
        ]

        for row in rows:
            lookup = {
                "policy_code": row["policy_code"],
                "version_number": row["version_number"],
            }
            defaults = {
                key: value
                for key, value in row.items()
                if key not in lookup
            }
            self._upsert(
                DepreciationPolicy,
                lookup,
                defaults,
            )
            
