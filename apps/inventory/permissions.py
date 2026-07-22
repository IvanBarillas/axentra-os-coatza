# apps/inventory/permissions.py

"""
Manifiesto soberano de permisos de Inventory consumido por AxentraOSRegistry,
get_app_permissions, get_user_permissions_for_app y axentra_module_gate.
Las llaves deben permanecer estables (se guardan como snapshot en UserAppRole.permissions_list).
"""

from apps.shared.apps_config import AppIdentifier

class InventoryPermissions:
    APP_CODE = AppIdentifier.INVENTORY

    PERMISSIONS = {
        # Acceso y consulta general
        "has_access_module": "Permite ingresar al módulo de Inventario.",
        "can_view_dashboard": "Permite consultar el panel general de inventario.",
        "can_view_assets": "Permite consultar bienes patrimoniales.",

        # Solicitudes de alta
        "can_create_asset": "Permite capturar una solicitud de alta patrimonial.",
        "can_create_intake_for_any_department": "Permite capturar solicitudes de alta para una dependencia destino distinta a la adscripción del usuario.",
        "can_submit_asset_intake": "Permite enviar solicitudes de alta a revisión.",
        "can_approve_department_intake": "Permite aceptar o rechazar altas por la dependencia.",
        "can_validate_patrimony_intake": "Permite validar altas y crear el activo patrimonial oficial.",
        "can_register_asset": "Permite generar el folio oficial y registrar un activo previamente aprobado.",

        # Expediente patrimonial
        "can_edit_asset": "Permite corregir datos administrativos autorizados del activo.",
        "can_correct_asset": "Permite ejecutar correcciones patrimoniales auditadas.",
        "can_manage_catalogs": "Permite administrar catálogos maestros de Inventario.",

        # Resguardos
        "can_manage_custody": "Permite generar y administrar resguardos.",
        "can_accept_custody": "Permite aceptar, firmar o rechazar un resguardo propio.",

        # Movimientos
        "can_manage_movements": "Permite registrar movimientos patrimoniales.",
        "can_authorize_movements": "Permite autorizar movimientos patrimoniales críticos.",

        # Préstamos
        "can_request_loans": "Permite solicitar préstamos temporales de activos.",
        "can_manage_loans": "Permite gestionar entrega, seguimiento y devolución de préstamos.",
        "can_authorize_loans": "Permite autorizar o rechazar préstamos de activos.",

        # Bajas
        "can_request_disposals": "Permite solicitar la baja de un activo.",
        "can_manage_disposals": "Permite integrar y revisar expedientes de baja patrimonial.",
        "can_authorize_disposals": "Permite autorizar o rechazar bajas patrimoniales.",
        "can_execute_disposals": "Permite ejecutar una baja previamente autorizada.",
        "can_view_department_intake_inbox": "Permite consultar la bandeja de altas pendientes y el historial de la propia dependencia.",
        "can_view_own_custody_tasks": "Permite consultar exclusivamente tareas personales de resguardo.",

        # Documentos y fotografías
        "can_manage_documents": "Permite cargar y administrar documentos patrimoniales.",
        "can_validate_documents": "Permite validar, observar o rechazar documentos.",
        "can_view_restricted_documents": "Permite consultar documentos confidenciales o restringidos.",
        "can_manage_photos": "Permite cargar y administrar evidencia fotográfica.",

        # Auditoría física y trazabilidad
        "can_manage_physical_audits": "Permite abrir, administrar y cerrar auditorías físicas.",
        "can_scan_physical_audits": "Permite registrar lecturas durante una auditoría física.",
        "can_view_audit": "Permite consultar trazabilidad y bitácora del módulo.",

        # Finanzas y contabilidad
        "can_view_financials": "Permite consultar depreciación, valor en libros e información contable.",
        "can_run_depreciation": "Permite calcular lotes de depreciación.",
        "can_post_depreciation": "Permite contabilizar o cerrar lotes de depreciación.",
        "can_manage_reconciliation": "Permite importar y conciliar información contable.",
        "can_export_reports": "Permite exportar reportes patrimoniales y contables.",
    }

    # Agrupaciones reutilizables
    _VIEW_PERMISSIONS = ["has_access_module", "can_view_dashboard", "can_view_assets"]
    _INTAKE_OPERATOR_PERMISSIONS = ["can_create_asset", "can_submit_asset_intake", "can_manage_documents", "can_manage_photos"]
    _FINANCIAL_VIEW_PERMISSIONS = ["can_view_financials", "can_export_reports"]
    _PATRIMONY_OPERATOR_PERMISSIONS = [
        "can_edit_asset", "can_manage_custody", "can_manage_movements", "can_manage_loans",
        "can_manage_disposals", "can_manage_documents", "can_manage_photos"
    ]

    # Roles funcionales
    ROLE_MAPPING = {
        "owner": list(PERMISSIONS.keys()),
        "admin": list(PERMISSIONS.keys()),
        "admin_patrimonio": list(PERMISSIONS.keys()),
        "adquisiciones": _VIEW_PERMISSIONS + _INTAKE_OPERATOR_PERMISSIONS + [
            "can_create_intake_for_any_department",
        ],
        "almacenista": _VIEW_PERMISSIONS + _INTAKE_OPERATOR_PERMISSIONS + _PATRIMONY_OPERATOR_PERMISSIONS + [
            "can_request_loans", "can_request_disposals", "can_accept_custody", "can_scan_physical_audits"
        ],
        "auditor": _VIEW_PERMISSIONS + _FINANCIAL_VIEW_PERMISSIONS + [
            "can_validate_documents", "can_view_restricted_documents", "can_manage_physical_audits",
            "can_scan_physical_audits", "can_view_audit", "can_manage_reconciliation"
        ],
        "director": _VIEW_PERMISSIONS + [
            "can_approve_department_intake",
            "can_view_department_intake_inbox",
            "can_accept_custody",
            "can_view_own_custody_tasks",
            "can_request_loans",
            "can_authorize_loans",
        ],
        "resguardatario": [
            "has_access_module", "can_view_assets", "can_accept_custody", "can_view_own_custody_tasks", "can_request_loans",
            "can_request_disposals", "can_manage_documents", "can_manage_photos"
        ],
        "viewer": _VIEW_PERMISSIONS,
        # Compatibilidad con roles reservados del Core
        "editor": _VIEW_PERMISSIONS + _INTAKE_OPERATOR_PERMISSIONS + ["can_request_loans", "can_request_disposals"],
        "reviewer": _VIEW_PERMISSIONS + _FINANCIAL_VIEW_PERMISSIONS + ["can_validate_documents", "can_scan_physical_audits", "can_view_audit"],
    }

    ROLE_WEIGHTS = {
        "owner": 100, "admin": 95, "admin_patrimonio": 90, "adquisiciones": 75, "almacenista": 70, "auditor": 60,
        "editor": 55, "reviewer": 50, "director": 45, "resguardatario": 25, "viewer": 20
    }

    # Rutas existentes del Sidebar (evita NoReverseMatch en templates)
    SIDEBAR_MENU = [
        ["layout-dashboard", "Panel de Inventario", "inventory:dashboard", 1, "can_view_dashboard"],
        ["package", "Bienes Patrimoniales", "inventory:asset_list", 2, "can_view_assets"],
        ["circle-plus", "Solicitud de Alta", "inventory:intake_create", 3, "can_create_asset"],
        ["library-big", "Catálogos", "inventory:catalog_home", 4, "can_manage_catalogs"],
    ]

    CAPABILITIES = {
        "can_operate": {
            "label": "Puede Operar Inventario",
            "help_text": "Permite que la dependencia capture solicitudes, resguardos y operaciones ordinarias de Inventory."
        },
        "can_supervise": {
            "label": "Puede Supervisar Inventario",
            "help_text": "Permite que la dependencia revise movimientos, conciliaciones, auditorías e indicadores patrimoniales."
        },
        "can_authorize": {
            "label": "Puede Autorizar Inventario",
            "help_text": "Habilita a la dependencia para participar en decisiones que además exigen un permiso individual de autorización."
        },
    }

__all__ = ["InventoryPermissions"]
