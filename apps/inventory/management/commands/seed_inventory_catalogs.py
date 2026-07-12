# apps/inventory/management/commands/seed_inventory_catalogs.py

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.inventory.models import (
    AccountingAccount,
    AcquisitionType,
    Asset,
    AssetCategory,
    AssetControlType,
    AssetLifecycleStatus,
    AssetModel,
    AssetNature,
    Contract,
    CustodyAssignment,
    CustodyStatus,
    DepreciationFrequency,
    DepreciationMethod,
    DepreciationPolicy,
    DepreciationRecord,
    DisposalReason,
    DisposalRequest,
    DisposalStatus,
    ImmovableAssetDetail,
    InventoryAuditLog,
    InventoryFolioSequence,
    InventoryMovement,
    Manufacturer,
    MovementType,
    PhysicalAuditItem,
    PhysicalAuditResult,
    PhysicalAuditSession,
    PhysicalAuditStatus,
    PhysicalCondition,
    Supplier,
)

from apps.security.models.organigrama import AreaOperativa, Dependencia, Sede


User = get_user_model()


class Command(BaseCommand):
    help = "Siembra catálogos y datos DEV para probar el módulo Inventory Patrimonial."

    PASSWORD_DEV = "1q2w3e4r5t%"
    MUNICIPALITY_CODE = "039"
    CAPITALIZATION_THRESHOLD_2026 = Decimal("8211.70")

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "\n🚀 === SEED INVENTORY: CATÁLOGOS Y DATOS PATRIMONIALES ==="
            )
        )

        operador = self._get_or_create_user()
        sede = self._get_or_create_sede()
        dependencia = self._get_or_create_dependencia()
        area = self._get_or_create_area(
            dependencia=dependencia,
            sede=sede,
        )

        dependency_code = self._get_dependency_code(dependencia)

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "\n🏷️ 1. Sembrando categorías patrimoniales..."
            )
        )
        categories = self._seed_categories()

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "\n📘 2. Sembrando cuentas contables CONAC..."
            )
        )
        accounts = self._seed_accounting_accounts(categories)

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "\n📉 3. Sembrando políticas de depreciación..."
            )
        )
        self._seed_depreciation_policies(accounts)

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "\n🏭 4. Sembrando fabricantes y modelos..."
            )
        )
        manufacturers, models = self._seed_manufacturers_and_models()

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "\n🤝 5. Sembrando proveedor y contrato..."
            )
        )
        supplier, contract = self._seed_supplier_and_contract()

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "\n🔢 6. Sembrando secuencias de folios patrimoniales..."
            )
        )
        self._seed_folio_sequences(dependency_code=dependency_code)

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "\n💻 7. Sembrando activos patrimoniales de prueba..."
            )
        )
        assets = self._seed_assets(
            operador=operador,
            sede=sede,
            dependencia=dependencia,
            area=area,
            dependency_code=dependency_code,
            categories=categories,
            accounts=accounts,
            models=models,
            supplier=supplier,
            contract=contract,
        )

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "\n📜 8. Sembrando resguardos y movimientos..."
            )
        )
        self._seed_custodies_and_movements(
            operador=operador,
            dependencia=dependencia,
            area=area,
            sede=sede,
            assets=assets,
        )

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "\n🧾 9. Sembrando depreciación de ejemplo..."
            )
        )
        self._seed_depreciation_records(
            operador=operador,
            assets=assets,
        )

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "\n🧯 10. Sembrando expediente de baja de ejemplo..."
            )
        )
        self._seed_disposal_request(
            operador=operador,
            assets=assets,
        )

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "\n🔍 11. Sembrando auditoría física de ejemplo..."
            )
        )
        self._seed_physical_audit(
            operador=operador,
            dependencia=dependencia,
            area=area,
            sede=sede,
            assets=assets,
        )

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "\n🕵️ 12. Sembrando logs internos de Inventory..."
            )
        )
        self._seed_audit_logs(
            operador=operador,
            assets=assets,
        )

        self.stdout.write(
            self.style.SUCCESS(
                "\n✅ === INVENTORY SEED COMPLETADO CORRECTAMENTE ===\n"
            )
        )

        self.stdout.write(
            self.style.WARNING(
                f"👤 Usuario DEV: {operador.email}\n"
                f"🔐 Password DEV si fue creado por seed: {self.PASSWORD_DEV}\n"
            )
        )

    def _modelo_tiene_campo(self, modelo, campo: str) -> bool:
        try:
            modelo._meta.get_field(campo)
            return True
        except Exception:
            return False

    def _get_dependency_code(self, dependencia) -> str:
        codigo = getattr(dependencia, "codigo_presupuestal", None)

        if codigo:
            return str(codigo).strip().zfill(3)

        return "012"

    def _get_or_create_user(self):
        user = User.objects.filter(is_active=True).order_by("date_joined").first()

        if user:
            self.stdout.write(f"   🛡️ Usuario operador: {user.email}")
            return user

        defaults = {
            "first_name": "INVENTORY",
            "last_name": "DEV USER",
            "is_staff": True,
            "is_superuser": True,
            "is_active": True,
        }

        if self._modelo_tiene_campo(User, "username"):
            defaults["username"] = "inventory.dev@axentra.local"

        if self._modelo_tiene_campo(User, "is_manager"):
            defaults["is_manager"] = True

        if self._modelo_tiene_campo(User, "is_email_verified"):
            defaults["is_email_verified"] = True

        user = User.objects.create(
            email="inventory.dev@axentra.local",
            **defaults,
        )
        user.set_password(self.PASSWORD_DEV)
        user.save()

        self.stdout.write(f"   🟢 Usuario DEV creado: {user.email}")
        return user

    def _get_or_create_sede(self):
        sede, created = Sede.objects.get_or_create(
            nombre="TESORERIA MUNICIPAL",
            defaults={
                "direccion": "Quevedo 200, Centro, Coatzacoalcos",
                "is_active": True,
                "is_deleted": False,
            },
        )

        if not created:
            sede.is_active = True
            sede.is_deleted = False
            sede.save()

        self.stdout.write(f"   🏢 Sede base: {sede.nombre}")
        return sede

    def _get_or_create_dependencia(self):
        dependencia, created = Dependencia.objects.get_or_create(
            nombre="INNOVACION GUBERNAMENTAL",
            defaults={
                "is_active": True,
                "is_deleted": False,
            },
        )

        if not created:
            dependencia.is_active = True
            dependencia.is_deleted = False
            dependencia.save()

        if hasattr(dependencia, "codigo_presupuestal"):
            if not dependencia.codigo_presupuestal:
                dependencia.codigo_presupuestal = "012"
                dependencia.save()

        self.stdout.write(f"   🏛️ Dependencia base: {dependencia.nombre}")
        return dependencia

    def _get_or_create_area(self, dependencia, sede):
        area, created = AreaOperativa.objects.get_or_create(
            dependencia=dependencia,
            sede_fisica=sede,
            nombre="SOPORTE TECNICO",
            defaults={
                "is_active": True,
                "is_deleted": False,
            },
        )

        if not created:
            area.is_active = True
            area.is_deleted = False
            area.save()

        self.stdout.write(f"   🧩 Área base: {area.nombre}")
        return area

    def _seed_categories(self):
        data = [
            {
                "code": "BM-MOB",
                "name": "Mobiliario y Equipo de Administración",
                "nature": AssetNature.MOVABLE,
                "description": "Escritorios, archiveros, sillas, mobiliario de oficina.",
            },
            {
                "code": "BM-COMP",
                "name": "Equipo de Cómputo y Tecnologías de Información",
                "nature": AssetNature.MOVABLE,
                "description": "Computadoras, laptops, servidores, monitores y periféricos capitalizables.",
            },
            {
                "code": "BM-AV",
                "name": "Equipos y Aparatos Audiovisuales",
                "nature": AssetNature.MOVABLE,
                "description": "Pantallas, proyectores, audio y video institucional.",
            },
            {
                "code": "BM-VEH",
                "name": "Vehículos y Equipo de Transporte",
                "nature": AssetNature.MOVABLE,
                "description": "Vehículos terrestres, patrullas, camionetas, motocicletas.",
            },
            {
                "code": "BM-MAQ",
                "name": "Maquinaria, Otros Equipos y Herramientas",
                "nature": AssetNature.MOVABLE,
                "description": "Maquinaria, herramientas, equipos especializados.",
            },
            {
                "code": "BI-EDIF",
                "name": "Edificios No Habitacionales",
                "nature": AssetNature.IMMOVABLE,
                "description": "Oficinas, bodegas, edificios públicos municipales.",
            },
            {
                "code": "BI-TER",
                "name": "Terrenos",
                "nature": AssetNature.IMMOVABLE,
                "description": "Terrenos propiedad del municipio.",
            },
            {
                "code": "INT-SOFT",
                "name": "Licencias de Software y Sistemas Informáticos",
                "nature": AssetNature.INTANGIBLE,
                "description": "Licencias, sistemas y derechos de uso de software.",
            },
        ]

        result = {}

        for item in data:
            obj, created = AssetCategory.objects.update_or_create(
                code=item["code"],
                defaults={
                    "name": item["name"],
                    "nature": item["nature"],
                    "description": item["description"],
                    "is_active": True,
                    "is_deleted": False,
                },
            )
            result[item["code"]] = obj

            status = "🟢 Creada" if created else "🛡️ Actualizada"
            self.stdout.write(f"   {status}: {obj.code} · {obj.name}")

        return result

    def _seed_accounting_accounts(self, categories):
        data = [
            {
                "code": "1.2.3.3",
                "conac_folio_code": "1233",
                "name": "Edificios No Habitacionales",
                "category": "BI-EDIF",
                "is_depreciable": True,
                "life_months": 360,
                "rate": Decimal("3.300"),
            },
            {
                "code": "1.2.4.1.1",
                "conac_folio_code": "5111",
                "name": "Muebles de Oficina y Estantería",
                "category": "BM-MOB",
                "is_depreciable": True,
                "life_months": 120,
                "rate": Decimal("10.000"),
            },
            {
                "code": "1.2.4.1.3",
                "conac_folio_code": "5151",
                "name": "Equipo de Cómputo y Tecnologías de Información",
                "category": "BM-COMP",
                "is_depreciable": True,
                "life_months": 36,
                "rate": Decimal("33.300"),
            },
            {
                "code": "1.2.4.2.1",
                "conac_folio_code": "5211",
                "name": "Equipos y Aparatos Audiovisuales",
                "category": "BM-AV",
                "is_depreciable": True,
                "life_months": 36,
                "rate": Decimal("33.300"),
            },
            {
                "code": "1.2.4.4.1",
                "conac_folio_code": "5411",
                "name": "Vehículos Terrestres y Equipo de Transporte",
                "category": "BM-VEH",
                "is_depreciable": True,
                "life_months": 60,
                "rate": Decimal("20.000"),
            },
            {
                "code": "1.2.4.6",
                "conac_folio_code": "5651",
                "name": "Maquinaria, Otros Equipos y Herramientas",
                "category": "BM-MAQ",
                "is_depreciable": True,
                "life_months": 120,
                "rate": Decimal("10.000"),
            },
            {
                "code": "1.2.5.4",
                "conac_folio_code": "5911",
                "name": "Licencias de Software y Sistemas Informáticos",
                "category": "INT-SOFT",
                "is_depreciable": True,
                "life_months": 40,
                "rate": Decimal("30.000"),
            },
            {
                "code": "1.2.6.3",
                "conac_folio_code": "1263",
                "name": "Depreciación Acumulada de Bienes Muebles",
                "category": "BM-COMP",
                "is_depreciable": False,
                "life_months": None,
                "rate": None,
            },
            {
                "code": "5.5.1.1",
                "conac_folio_code": "5511",
                "name": "Depreciación de Bienes Muebles",
                "category": "BM-COMP",
                "is_depreciable": False,
                "life_months": None,
                "rate": None,
            },
        ]

        result = {}

        for item in data:
            obj, created = AccountingAccount.objects.update_or_create(
                code=item["code"],
                defaults={
                    "name": item["name"],
                    "category": categories[item["category"]],
                    "is_depreciable": item["is_depreciable"],
                    "default_useful_life_months": item["life_months"],
                    "default_annual_depreciation_rate": item["rate"],
                    "is_active": True,
                    "is_deleted": False,
                },
            )

            result[item["code"]] = obj
            result[item["conac_folio_code"]] = obj

            status = "🟢 Creada" if created else "🛡️ Actualizada"
            self.stdout.write(f"   {status}: {obj.code} · {obj.name}")

        return result

    def _seed_depreciation_policies(self, accounts):
        data = [
            {
                "name": "CONAC · Equipo de Cómputo · Línea Recta 36 meses",
                "account": "1.2.4.1.3",
                "life": 36,
                "residual": Decimal("0.000"),
            },
            {
                "name": "CONAC · Mobiliario · Línea Recta 120 meses",
                "account": "1.2.4.1.1",
                "life": 120,
                "residual": Decimal("0.000"),
            },
            {
                "name": "CONAC · Vehículos · Línea Recta 60 meses",
                "account": "1.2.4.4.1",
                "life": 60,
                "residual": Decimal("0.000"),
            },
            {
                "name": "CONAC · Software · Línea Recta 40 meses",
                "account": "1.2.5.4",
                "life": 40,
                "residual": Decimal("0.000"),
            },
        ]

        for item in data:
            obj, created = DepreciationPolicy.objects.update_or_create(
                name=item["name"],
                defaults={
                    "accounting_account": accounts[item["account"]],
                    "method": DepreciationMethod.STRAIGHT_LINE,
                    "frequency": DepreciationFrequency.MONTHLY,
                    "useful_life_months": item["life"],
                    "residual_percentage": item["residual"],
                    "is_active": True,
                    "is_deleted": False,
                },
            )

            status = "🟢 Creada" if created else "🛡️ Actualizada"
            self.stdout.write(f"   {status}: {obj.name}")

    def _seed_manufacturers_and_models(self):
        data = {
            "DELL": ["OPTIPLEX 7010", "LATITUDE 5440", "POWEREDGE R450"],
            "HP": ["ELITEDESK 800 G6", "LASERJET PRO M404DN", "PROBOOK 440 G9"],
            "LENOVO": ["THINKCENTRE M720Q", "THINKPAD E14"],
            "SAMSUNG": ["MONITOR 24 FHD"],
            "BROTHER": ["DCP-L2540DW"],
            "CISCO": ["CATALYST 2960X"],
            "UBIQUITI": ["U6 PRO", "UCG ULTRA"],
            "GRANDSTREAM": ["GXP1625", "UCM6302"],
        }

        manufacturers = {}
        models = {}

        for manufacturer_name, model_names in data.items():
            manufacturer, created = Manufacturer.objects.update_or_create(
                name=manufacturer_name,
                defaults={
                    "is_active": True,
                    "is_deleted": False,
                },
            )
            manufacturers[manufacturer_name] = manufacturer

            status = "🟢 Fabricante creado" if created else "🛡️ Fabricante actualizado"
            self.stdout.write(f"   {status}: {manufacturer.name}")

            for model_name in model_names:
                model, model_created = AssetModel.objects.update_or_create(
                    manufacturer=manufacturer,
                    name=model_name,
                    defaults={
                        "description": "",
                        "is_active": True,
                        "is_deleted": False,
                    },
                )
                models[f"{manufacturer_name}:{model_name}"] = model

                status_model = "🟢 Modelo creado" if model_created else "🛡️ Modelo actualizado"
                self.stdout.write(f"      ↳ {status_model}: {model}")

        return manufacturers, models

    def _seed_supplier_and_contract(self):
        supplier, supplier_created = Supplier.objects.update_or_create(
            razon_social="AXENTRA TECNOLOGIAS MUNICIPALES SA DE CV",
            defaults={
                "rfc": "ATM240101XX1",
                "contacto_nombre": "MESA DE SERVICIO AXENTRA",
                "telefono": "9210000000",
                "email": "soporte@axentra.local",
                "is_active": True,
                "is_deleted": False,
            },
        )

        contract, contract_created = Contract.objects.update_or_create(
            numero_contrato="COATZA-INV-DEV-2026-001",
            defaults={
                "nombre": "Suministro de equipo tecnológico para pruebas de inventario",
                "supplier": supplier,
                "fecha_inicio": timezone.localdate().replace(month=1, day=1),
                "fecha_fin": timezone.localdate().replace(month=12, day=31),
                "monto_total": Decimal("250000.00"),
                "is_active": True,
                "is_deleted": False,
            },
        )

        status_supplier = "🟢 Creado" if supplier_created else "🛡️ Actualizado"
        status_contract = "🟢 Creado" if contract_created else "🛡️ Actualizado"

        self.stdout.write(f"   {status_supplier}: {supplier.razon_social}")
        self.stdout.write(f"   {status_contract}: {contract.numero_contrato}")

        return supplier, contract

    def _seed_folio_sequences(self, *, dependency_code):
        data = [
            {
                "year": 26,
                "conac_code": "5151",
                "dependency_code": dependency_code,
                "asset_type_code": "BM",
                "current_number": 5,
            },
            {
                "year": 26,
                "conac_code": "1233",
                "dependency_code": dependency_code,
                "asset_type_code": "BI",
                "current_number": 1,
            },
            {
                "year": 26,
                "conac_code": "5911",
                "dependency_code": dependency_code,
                "asset_type_code": "BM",
                "current_number": 1,
            },
        ]

        for item in data:
            sequence, created = InventoryFolioSequence.objects.update_or_create(
                municipality_code=self.MUNICIPALITY_CODE,
                year=item["year"],
                conac_code=item["conac_code"],
                dependency_code=item["dependency_code"],
                asset_type_code=item["asset_type_code"],
                defaults={
                    "current_number": item["current_number"],
                    "is_active": True,
                    "is_deleted": False,
                },
            )

            status = "🟢 Creada" if created else "🛡️ Actualizada"
            self.stdout.write(f"   {status}: {sequence}")

    def _official_folio(self, *, year, conac_code, dependency_code, asset_type_code, number):
        return (
            f"{self.MUNICIPALITY_CODE}-"
            f"{year:02d}-"
            f"{conac_code}-"
            f"{dependency_code.zfill(3)}-"
            f"{asset_type_code}-"
            f"{number:04d}"
        )

    def _seed_assets(
        self,
        *,
        operador,
        sede,
        dependencia,
        area,
        dependency_code,
        categories,
        accounts,
        models,
        supplier,
        contract,
    ):
        today = timezone.localdate()

        data = [
            {
                "key": "desktop",
                "official": self._official_folio(
                    year=26,
                    conac_code="5151",
                    dependency_code=dependency_code,
                    asset_type_code="BM",
                    number=1,
                ),
                "internal": "AXN-INV-2026-000001",
                "legacy": "COATZA-TI-000001",
                "name": "Computadora de escritorio soporte técnico",
                "description": "Equipo de escritorio asignado al área de soporte técnico.",
                "category": categories["BM-COMP"],
                "account": accounts["1.2.4.1.3"],
                "control_type": AssetControlType.CAPITALIZED_ASSET,
                "status": AssetLifecycleStatus.ASSIGNED,
                "condition": PhysicalCondition.GOOD,
                "acquisition_type": AcquisitionType.PURCHASE,
                "cost": Decimal("18500.00"),
                "model": models["DELL:OPTIPLEX 7010"],
                "serial": "DLL-OPT-DEV-0001",
                "custodian": operador,
                "useful_life_months": 36,
                "extra": {
                    "origen_seed": True,
                    "perfil_operativo": "desktop",
                },
            },
            {
                "key": "monitor",
                "official": None,
                "internal": "AXN-INV-2026-000002",
                "legacy": "COATZA-TI-000002",
                "name": "Monitor soporte técnico",
                "description": "Monitor de control interno asignado al área de soporte técnico.",
                "category": categories["BM-COMP"],
                "account": accounts["1.2.4.1.3"],
                "control_type": AssetControlType.INTERNAL_CONTROL,
                "status": AssetLifecycleStatus.ASSIGNED,
                "condition": PhysicalCondition.GOOD,
                "acquisition_type": AcquisitionType.PURCHASE,
                "cost": Decimal("4200.00"),
                "model": models["SAMSUNG:MONITOR 24 FHD"],
                "serial": "SAM-MON-DEV-0001",
                "custodian": operador,
                "useful_life_months": 36,
                "extra": {
                    "origen_seed": True,
                    "perfil_operativo": "monitor",
                    "nota": "Bien menor a 70 UMA. Control interno.",
                },
            },
            {
                "key": "printer",
                "official": self._official_folio(
                    year=26,
                    conac_code="5151",
                    dependency_code=dependency_code,
                    asset_type_code="BM",
                    number=2,
                ),
                "internal": "AXN-INV-2026-000003",
                "legacy": "COATZA-TI-000003",
                "name": "Impresora láser mesa de ayuda",
                "description": "Impresora asignada para pruebas patrimoniales.",
                "category": categories["BM-COMP"],
                "account": accounts["1.2.4.1.3"],
                "control_type": AssetControlType.CAPITALIZED_ASSET,
                "status": AssetLifecycleStatus.IN_USE,
                "condition": PhysicalCondition.REGULAR,
                "acquisition_type": AcquisitionType.PURCHASE,
                "cost": Decimal("9200.00"),
                "model": models["HP:LASERJET PRO M404DN"],
                "serial": "HP-LJ-DEV-0001",
                "custodian": operador,
                "useful_life_months": 36,
                "extra": {
                    "origen_seed": True,
                    "perfil_operativo": "printer",
                },
            },
            {
                "key": "switch",
                "official": self._official_folio(
                    year=26,
                    conac_code="5151",
                    dependency_code=dependency_code,
                    asset_type_code="BM",
                    number=3,
                ),
                "internal": "AXN-INV-2026-000004",
                "legacy": "COATZA-NET-000001",
                "name": "Switch principal laboratorio TI",
                "description": "Switch de pruebas patrimoniales.",
                "category": categories["BM-COMP"],
                "account": accounts["1.2.4.1.3"],
                "control_type": AssetControlType.CAPITALIZED_ASSET,
                "status": AssetLifecycleStatus.IN_USE,
                "condition": PhysicalCondition.GOOD,
                "acquisition_type": AcquisitionType.PURCHASE,
                "cost": Decimal("13500.00"),
                "model": models["CISCO:CATALYST 2960X"],
                "serial": "CSC-SW-DEV-0001",
                "custodian": operador,
                "useful_life_months": 36,
                "extra": {
                    "origen_seed": True,
                    "perfil_operativo": "network",
                },
            },
            {
                "key": "ap",
                "official": self._official_folio(
                    year=26,
                    conac_code="5151",
                    dependency_code=dependency_code,
                    asset_type_code="BM",
                    number=4,
                ),
                "internal": "AXN-INV-2026-000005",
                "legacy": "COATZA-WIFI-000001",
                "name": "Access Point Palacio Municipal",
                "description": "Access point de ejemplo para pruebas patrimoniales.",
                "category": categories["BM-COMP"],
                "account": accounts["1.2.4.1.3"],
                "control_type": AssetControlType.CAPITALIZED_ASSET,
                "status": AssetLifecycleStatus.IN_USE,
                "condition": PhysicalCondition.GOOD,
                "acquisition_type": AcquisitionType.PURCHASE,
                "cost": Decimal("8900.00"),
                "model": models["UBIQUITI:U6 PRO"],
                "serial": "UBQ-AP-DEV-0001",
                "custodian": operador,
                "useful_life_months": 36,
                "extra": {
                    "origen_seed": True,
                    "ssid": "COATZA-GOB",
                    "vlan": "10",
                },
            },
            {
                "key": "building",
                "official": self._official_folio(
                    year=26,
                    conac_code="1233",
                    dependency_code=dependency_code,
                    asset_type_code="BI",
                    number=1,
                ),
                "internal": "AXN-INV-2026-000006",
                "legacy": "COATZA-INM-000001",
                "name": "Bodega operativa de innovación",
                "description": "Inmueble de ejemplo para pruebas de bienes inmuebles.",
                "category": categories["BI-EDIF"],
                "account": accounts["1.2.3.3"],
                "control_type": AssetControlType.CAPITALIZED_ASSET,
                "status": AssetLifecycleStatus.REGISTERED,
                "condition": PhysicalCondition.GOOD,
                "acquisition_type": AcquisitionType.REGULARIZATION,
                "cost": Decimal("2500000.00"),
                "model": None,
                "serial": "",
                "custodian": None,
                "useful_life_months": 360,
                "extra": {
                    "origen_seed": True,
                    "tipo_inmueble": "bodega",
                },
            },
            {
                "key": "software",
                "official": self._official_folio(
                    year=26,
                    conac_code="5911",
                    dependency_code=dependency_code,
                    asset_type_code="BM",
                    number=1,
                ),
                "internal": "AXN-INV-2026-000007",
                "legacy": "COATZA-SW-000001",
                "name": "Licencia sistema antivirus institucional",
                "description": "Licencia de software de ejemplo para intangible.",
                "category": categories["INT-SOFT"],
                "account": accounts["1.2.5.4"],
                "control_type": AssetControlType.CAPITALIZED_ASSET,
                "status": AssetLifecycleStatus.IN_USE,
                "condition": PhysicalCondition.GOOD,
                "acquisition_type": AcquisitionType.PURCHASE,
                "cost": Decimal("45000.00"),
                "model": None,
                "serial": "LIC-AV-DEV-2026",
                "custodian": operador,
                "useful_life_months": 40,
                "extra": {
                    "origen_seed": True,
                    "licencias": 100,
                },
            },
        ]

        result = {}

        for item in data:
            is_capitalizable = item["cost"] >= self.CAPITALIZATION_THRESHOLD_2026

            asset, created = Asset.objects.update_or_create(
                internal_inventory_number=item["internal"],
                defaults={
                    "official_inventory_number": item["official"],
                    "legacy_inventory_number": item["legacy"],
                    "name": item["name"],
                    "description": item["description"],
                    "category": item["category"],
                    "accounting_account": item["account"],
                    "control_type": item["control_type"],
                    "lifecycle_status": item["status"],
                    "physical_condition": item["condition"],
                    "acquisition_type": item["acquisition_type"],
                    "acquisition_date": today,
                    "registration_date": today,
                    "acquisition_cost": item["cost"],
                    "residual_value": Decimal("0.00"),
                    "useful_life_months": item["useful_life_months"],
                    "is_capitalizable": is_capitalizable,
                    "capitalization_threshold_amount": self.CAPITALIZATION_THRESHOLD_2026,
                    "manufacturer": item["model"].manufacturer if item["model"] else None,
                    "model": item["model"],
                    "serial_number": item["serial"] or None,
                    "supplier": supplier,
                    "contract": contract,
                    "sede": sede,
                    "dependencia": dependencia,
                    "area": area,
                    "current_custodian": item["custodian"],
                    "latitude": Decimal("18.1500000"),
                    "longitude": Decimal("-94.4330000"),
                    "notes": "ACTIVO DE PRUEBA CREADO POR SEED INVENTORY.",
                    "extra_attributes": item["extra"],
                    "is_active": True,
                    "is_deleted": False,
                },
            )

            result[item["key"]] = asset

            status = "🟢 Creado" if created else "🛡️ Actualizado"
            self.stdout.write(
                f"   {status}: {asset.display_inventory_number} · {asset.name}"
            )

        ImmovableAssetDetail.objects.update_or_create(
            asset=result["building"],
            defaults={
                "cadastral_key": "COATZA-DEV-CATASTRAL-0001",
                "public_registry_record": "RPP-COATZA-DEV-0001",
                "deed_number": "ESCRITURA-DEV-0001",
                "surface_m2": Decimal("350.00"),
                "legal_status": "REGULARIZADO PARA PRUEBAS",
                "is_active": True,
                "is_deleted": False,
            },
        )
        self.stdout.write("   🏢 Detalle de inmueble sembrado.")

        return result

    def _seed_custodies_and_movements(
        self,
        *,
        operador,
        dependencia,
        area,
        sede,
        assets,
    ):
        for key in ["desktop", "monitor", "printer"]:
            asset = assets[key]
            asset_folio = asset.display_inventory_number

            custody, created = CustodyAssignment.objects.update_or_create(
                folio=f"RESG-DEV-{asset.internal_inventory_number}",
                defaults={
                    "asset": asset,
                    "assigned_to": operador,
                    "assigned_by": operador,
                    "dependencia": dependencia,
                    "area": area,
                    "sede": sede,
                    "status": CustodyStatus.ACTIVE,
                    "assigned_at": timezone.now(),
                    "signed_at": timezone.now(),
                    "returned_at": None,
                    "digital_signature_hash": "",
                    "notes": "RESGUARDO ACTIVO DE PRUEBA GENERADO POR SEED.",
                    "is_active": True,
                    "is_deleted": False,
                },
            )

            status = "🟢 Resguardo creado" if created else "🛡️ Resguardo actualizado"
            self.stdout.write(f"   {status}: {custody.folio} · {asset_folio}")

            InventoryMovement.objects.update_or_create(
                asset=asset,
                movement_type=MovementType.ASSIGNMENT,
                reference_folio=custody.folio,
                defaults={
                    "from_dependencia": None,
                    "to_dependencia": dependencia,
                    "from_area": None,
                    "to_area": area,
                    "from_sede": None,
                    "to_sede": sede,
                    "from_user": None,
                    "to_user": operador,
                    "performed_by": operador,
                    "reason": "Asignación inicial de prueba desde seed inventory.",
                    "payload": {
                        "seed": True,
                        "custody_folio": custody.folio,
                        "asset_folio": asset_folio,
                    },
                    "is_active": True,
                    "is_deleted": False,
                },
            )

        self.stdout.write("   📜 Movimientos de asignación sembrados.")

    def _seed_depreciation_records(self, operador, assets):
        asset = assets["desktop"]

        policy = DepreciationPolicy.objects.filter(
            accounting_account=asset.accounting_account,
            is_active=True,
            is_deleted=False,
        ).first()

        if not policy:
            self.stdout.write(
                self.style.WARNING(
                    "   ⚠️ No existe política para el activo desktop. Se omite depreciación."
                )
            )
            return

        monthly_depreciation = (asset.acquisition_cost - asset.residual_value) / Decimal(
            policy.useful_life_months
        )
        accumulated = monthly_depreciation
        book_value = asset.acquisition_cost - accumulated

        record, created = DepreciationRecord.objects.update_or_create(
            asset=asset,
            period_year=timezone.localdate().year,
            period_month=timezone.localdate().month,
            defaults={
                "policy": policy,
                "original_value": asset.acquisition_cost,
                "residual_value": asset.residual_value,
                "depreciation_amount": monthly_depreciation.quantize(Decimal("0.01")),
                "accumulated_depreciation": accumulated.quantize(Decimal("0.01")),
                "book_value": book_value.quantize(Decimal("0.01")),
                "calculated_by": operador,
                "is_active": True,
                "is_deleted": False,
            },
        )

        status = "🟢 Creada" if created else "🛡️ Actualizada"
        self.stdout.write(f"   {status}: depreciación {record}")

    def _seed_disposal_request(self, operador, assets):
        asset = assets["monitor"]

        disposal, created = DisposalRequest.objects.update_or_create(
            folio="BAJA-DEV-000001",
            defaults={
                "asset": asset,
                "reason": DisposalReason.OBSOLESCENCE,
                "status": DisposalStatus.UNDER_REVIEW,
                "requested_by": operador,
                "reviewed_by": operador,
                "approved_by": None,
                "reviewed_at": timezone.now(),
                "approved_at": None,
                "executed_at": None,
                "description": "Expediente de baja de prueba por obsolescencia del monitor.",
                "legal_reference": "Expediente de prueba sin efectos legales.",
                "source_app": "",
                "source_model": "",
                "source_object_id": "",
                "is_active": True,
                "is_deleted": False,
            },
        )

        status = "🟢 Creada" if created else "🛡️ Actualizada"
        self.stdout.write(
            f"   {status}: {disposal.folio} · {asset.display_inventory_number}"
        )

    def _seed_physical_audit(
        self,
        *,
        operador,
        dependencia,
        area,
        sede,
        assets,
    ):
        session, created = PhysicalAuditSession.objects.update_or_create(
            folio="AUD-FIS-DEV-000001",
            defaults={
                "name": "Auditoría física DEV · Soporte Técnico",
                "status": PhysicalAuditStatus.IN_PROGRESS,
                "sede": sede,
                "dependencia": dependencia,
                "area": area,
                "started_by": operador,
                "closed_by": None,
                "started_at": timezone.now(),
                "closed_at": None,
                "notes": "Auditoría física de prueba para validar escaneo QR.",
                "is_active": True,
                "is_deleted": False,
            },
        )

        status = "🟢 Creada" if created else "🛡️ Actualizada"
        self.stdout.write(f"   {status}: {session.folio}")

        for key, result in [
            ("desktop", PhysicalAuditResult.FOUND),
            ("monitor", PhysicalAuditResult.FOUND_DIFFERENT_LOCATION),
            ("printer", PhysicalAuditResult.DAMAGED),
        ]:
            asset = assets[key]

            PhysicalAuditItem.objects.update_or_create(
                session=session,
                asset=asset,
                scanned_inventory_number=asset.display_inventory_number,
                defaults={
                    "result": result,
                    "scanned_by": operador,
                    "latitude": Decimal("18.1500000"),
                    "longitude": Decimal("-94.4330000"),
                    "notes": "Lectura de prueba generada por seed.",
                    "is_active": True,
                    "is_deleted": False,
                },
            )

        PhysicalAuditItem.objects.update_or_create(
            session=session,
            asset=None,
            scanned_inventory_number="COATZA-SOBRANTE-000001",
            defaults={
                "result": PhysicalAuditResult.UNREGISTERED,
                "scanned_by": operador,
                "latitude": Decimal("18.1500000"),
                "longitude": Decimal("-94.4330000"),
                "notes": "Sobrante no registrado de prueba.",
                "is_active": True,
                "is_deleted": False,
            },
        )

        self.stdout.write("   🔍 Items de auditoría física sembrados.")

    def _seed_audit_logs(self, operador, assets):
        logs = [
            {
                "action_type": "SEED_CREATED",
                "asset": assets["desktop"],
                "summary": "Activo de cómputo creado por seed inventory.",
            },
            {
                "action_type": "SEED_CUSTODY_CREATED",
                "asset": assets["printer"],
                "summary": "Resguardo de impresora creado por seed inventory.",
            },
            {
                "action_type": "SEED_PHYSICAL_AUDIT_CREATED",
                "asset": assets["desktop"],
                "summary": "Auditoría física de prueba creada por seed inventory.",
            },
        ]

        for item in logs:
            InventoryAuditLog.objects.update_or_create(
                action_type=item["action_type"],
                asset=item["asset"],
                target_model="inventory.Asset",
                target_id=str(item["asset"].id),
                defaults={
                    "actor": operador,
                    "summary": item["summary"],
                    "old_value": {},
                    "new_value": {
                        "official_inventory_number": item["asset"].official_inventory_number,
                        "internal_inventory_number": item["asset"].internal_inventory_number,
                        "legacy_inventory_number": item["asset"].legacy_inventory_number,
                        "display_inventory_number": item["asset"].display_inventory_number,
                        "seed": True,
                    },
                    "ip_address": None,
                    "user_agent": "seed_inventory_catalogs",
                    "is_active": True,
                    "is_deleted": False,
                },
            )

        self.stdout.write("   🕵️ Logs internos sembrados.")
        
