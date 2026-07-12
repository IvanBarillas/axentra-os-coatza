# apps/inventory/permissions.py

from apps.shared.apps_config import AppIdentifier


class InventoryPermissions:
    APP_CODE = AppIdentifier.INVENTORY

    PERMISSIONS = {
        "has_access_module": "Permite ingresar al módulo de Inventario.",
        "can_view_dashboard": "Permite consultar el panel general de inventario.",
        "can_view_assets": "Permite consultar bienes patrimoniales.",
        "can_create_asset": "Permite registrar bienes patrimoniales.",
        "can_edit_asset": "Permite modificar bienes patrimoniales.",
        "can_manage_custody": "Permite generar y administrar resguardos.",
        "can_manage_movements": "Permite registrar movimientos patrimoniales.",
        "can_manage_disposals": "Permite iniciar y gestionar bajas patrimoniales.",
        "can_view_financials": "Permite consultar depreciación, valor en libros e información contable.",
        "can_export_reports": "Permite exportar reportes patrimoniales y contables.",
        "can_manage_documents": "Permite cargar y administrar documentos del expediente patrimonial.",
        "can_manage_photos": "Permite cargar y administrar evidencia fotográfica del activo.",
        "can_manage_physical_audits": "Permite ejecutar auditorías físicas de inventario.",
        "can_view_audit": "Permite consultar trazabilidad y bitácora del módulo.",
    }

    ROLE_MAPPING = {
        "owner": list(PERMISSIONS.keys()),

        "admin_patrimonio": [
            "has_access_module",
            "can_view_dashboard",
            "can_view_assets",
            "can_create_asset",
            "can_edit_asset",
            "can_manage_custody",
            "can_manage_movements",
            "can_manage_disposals",
            "can_view_financials",
            "can_export_reports",
            "can_manage_documents",
            "can_manage_photos",
            "can_manage_physical_audits",
            "can_view_audit",
        ],

        "almacenista": [
            "has_access_module",
            "can_view_dashboard",
            "can_view_assets",
            "can_create_asset",
            "can_edit_asset",
            "can_manage_custody",
            "can_manage_movements",
            "can_manage_documents",
            "can_manage_photos",
        ],

        "auditor": [
            "has_access_module",
            "can_view_dashboard",
            "can_view_assets",
            "can_view_financials",
            "can_export_reports",
            "can_manage_physical_audits",
            "can_view_audit",
        ],

        "director": [
            "has_access_module",
            "can_view_dashboard",
            "can_view_assets",
            "can_view_financials",
            "can_export_reports",
        ],

        "resguardatario": [
            "has_access_module",
            "can_view_assets",
        ],

        "viewer": [
            "has_access_module",
            "can_view_dashboard",
            "can_view_assets",
        ],
    }

    ROLE_WEIGHTS = {
        "owner": 100,
        "admin_patrimonio": 90,
        "almacenista": 70,
        "auditor": 60,
        "director": 45,
        "resguardatario": 25,
        "viewer": 20,
    }

    CAPABILITIES = {
        "can_operate": {
            "label": "Puede Operar Inventario",
            "help_text": "Permite registrar, actualizar y mover bienes dentro del módulo de Inventario.",
        },
        "can_supervise": {
            "label": "Puede Supervisar Inventario",
            "help_text": "Permite revisar resguardos, movimientos, conciliaciones, auditorías físicas e indicadores patrimoniales.",
        },
        "can_authorize": {
            "label": "Puede Autorizar Inventario",
            "help_text": "Permite autorizar bajas, reasignaciones críticas y cierres patrimoniales.",
        },
    }
    
