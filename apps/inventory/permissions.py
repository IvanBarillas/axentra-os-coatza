from apps.shared.apps_config import AppIdentifier


class InventoryPermissions:
    APP_CODE = AppIdentifier.INVENTORY

    PERMISSIONS = {
        "has_access_module": "Permite ingresar al módulo de Inventario.",
        "can_view_dashboard": "Permite consultar el panel general de inventario.",
        "can_view_assets": "Permite consultar bienes patrimoniales.",
        "can_create_asset": "Permite registrar bienes patrimoniales.",
        "can_edit_asset": "Permite modificar bienes patrimoniales.",
        "can_view_technical_profile": "Permite consultar fichas técnicas tipo GLPI.",
        "can_manage_technical_profile": "Permite administrar fichas técnicas tipo GLPI.",
        "can_manage_custody": "Permite generar y administrar resguardos.",
        "can_manage_movements": "Permite registrar movimientos de inventario.",
        "can_manage_disposals": "Permite iniciar y gestionar bajas patrimoniales.",
        "can_view_financials": "Permite consultar depreciación y valor en libros.",
        "can_export_reports": "Permite exportar reportes patrimoniales.",
        "can_view_audit": "Permite consultar trazabilidad y auditoría del módulo.",
    }

    ROLE_MAPPING = {
        "owner": list(PERMISSIONS.keys()),
        "admin_patrimonio": [
            "has_access_module",
            "can_view_dashboard",
            "can_view_assets",
            "can_create_asset",
            "can_edit_asset",
            "can_view_technical_profile",
            "can_manage_technical_profile",
            "can_manage_custody",
            "can_manage_movements",
            "can_manage_disposals",
            "can_view_financials",
            "can_export_reports",
            "can_view_audit",
        ],
        "almacenista": [
            "has_access_module",
            "can_view_dashboard",
            "can_view_assets",
            "can_create_asset",
            "can_edit_asset",
            "can_manage_movements",
            "can_manage_custody",
        ],
        "soporte_tecnico": [
            "has_access_module",
            "can_view_dashboard",
            "can_view_assets",
            "can_view_technical_profile",
            "can_manage_technical_profile",
            "can_manage_movements",
        ],
        "director": [
            "has_access_module",
            "can_view_dashboard",
            "can_view_assets",
            "can_view_technical_profile",
        ],
        "resguardatario": [
            "has_access_module",
            "can_view_assets",
            "can_view_technical_profile",
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
        "soporte_tecnico": 60,
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
            "help_text": "Permite revisar resguardos, movimientos, conciliaciones e indicadores patrimoniales.",
        },
        "can_authorize": {
            "label": "Puede Autorizar Inventario",
            "help_text": "Permite autorizar bajas, reasignaciones críticas y cierres patrimoniales.",
        },
    }