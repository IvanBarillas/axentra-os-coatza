# apps/inventory/permissions.py

"""
Manifiesto soberano de permisos de Inventory.

Es consumido por AxentraOSRegistry, get_app_permissions,
get_user_permissions_for_app y axentra_module_gate.

IMPORTANTE:
    Las llaves existentes no deben renombrarse ni eliminarse porque se guardan
    como snapshot en UserAppRole.permissions_list. Las nuevas responsabilidades
    se agregan mediante permisos adicionales.
"""

from apps.shared.apps_config import AppIdentifier


def _unique_permissions(*groups):
    """Combina grupos conservando el orden y eliminando duplicados."""

    return list(dict.fromkeys(permission for group in groups for permission in group))


class InventoryPermissions:
    APP_CODE = AppIdentifier.INVENTORY

    PERMISSIONS = {
        # ------------------------------------------------------------------
        # Acceso y consulta
        # ------------------------------------------------------------------
        "has_access_module": (
            "Permite ingresar al módulo de Inventario."
        ),
        "can_view_dashboard": (
            "Permite consultar el panel general de inventario."
        ),
        "can_view_assets": (
            "Permite consultar bienes patrimoniales dentro de su alcance."
        ),

        # ------------------------------------------------------------------
        # Solicitudes de alta
        # ------------------------------------------------------------------
        # Se conserva por compatibilidad. En el flujo actual significa crear
        # una solicitud, no insertar directamente un Asset.
        "can_create_asset": (
            "Permite capturar una solicitud de alta patrimonial."
        ),
        "can_create_intake_for_any_department": (
            "Permite capturar solicitudes destinadas a cualquier dependencia."
        ),
        "can_submit_asset_intake": (
            "Permite enviar solicitudes de alta a aceptación departamental."
        ),
        "can_approve_department_intake": (
            "Permite aceptar o rechazar altas destinadas a la dependencia "
            "sobre la que el usuario tiene autoridad."
        ),
        "can_validate_patrimony_intake": (
            "Permite revisar, observar o aprobar solicitudes desde Control "
            "Patrimonial."
        ),
        "can_register_asset": (
            "Permite convertir una solicitud aprobada en un activo oficial y "
            "generar sus folios patrimoniales."
        ),

        # ------------------------------------------------------------------
        # Expediente patrimonial
        # ------------------------------------------------------------------
        "can_edit_asset": (
            "Permite modificar datos administrativos autorizados del activo."
        ),
        "can_correct_asset": (
            "Permite ejecutar correcciones patrimoniales auditadas."
        ),

        # ------------------------------------------------------------------
        # Resguardos
        # ------------------------------------------------------------------
        "can_manage_custody": (
            "Permite generar y administrar resguardos."
        ),
        "can_accept_custody": (
            "Permite aceptar, firmar o rechazar un resguardo propio."
        ),

        # ------------------------------------------------------------------
        # Movimientos
        # ------------------------------------------------------------------
        "can_manage_movements": (
            "Permite registrar movimientos patrimoniales."
        ),
        "can_authorize_movements": (
            "Permite autorizar movimientos patrimoniales críticos."
        ),

        # ------------------------------------------------------------------
        # Préstamos
        # ------------------------------------------------------------------
        "can_request_loans": (
            "Permite solicitar préstamos temporales de activos."
        ),
        "can_manage_loans": (
            "Permite gestionar entrega, seguimiento y devolución de préstamos."
        ),
        "can_authorize_loans": (
            "Permite autorizar o rechazar préstamos de activos."
        ),

        # ------------------------------------------------------------------
        # Bajas patrimoniales
        # ------------------------------------------------------------------
        "can_request_disposals": (
            "Permite solicitar la baja de un activo."
        ),
        "can_manage_disposals": (
            "Permite integrar y revisar expedientes de baja patrimonial."
        ),
        "can_authorize_disposals": (
            "Permite autorizar o rechazar bajas patrimoniales."
        ),
        "can_execute_disposals": (
            "Permite ejecutar una baja previamente autorizada."
        ),

        # ------------------------------------------------------------------
        # Documentos y fotografías
        # ------------------------------------------------------------------
        "can_manage_documents": (
            "Permite cargar y administrar documentos patrimoniales."
        ),
        "can_validate_documents": (
            "Permite validar, observar o rechazar documentos."
        ),
        "can_view_restricted_documents": (
            "Permite consultar documentos confidenciales o restringidos."
        ),
        "can_manage_photos": (
            "Permite cargar y administrar evidencia fotográfica."
        ),

        # ------------------------------------------------------------------
        # Auditoría física y trazabilidad
        # ------------------------------------------------------------------
        "can_manage_physical_audits": (
            "Permite abrir, administrar y cerrar auditorías físicas."
        ),
        "can_scan_physical_audits": (
            "Permite registrar lecturas durante una auditoría física."
        ),
        "can_view_audit": (
            "Permite consultar trazabilidad y bitácora del módulo."
        ),

        # ------------------------------------------------------------------
        # Finanzas y contabilidad
        # ------------------------------------------------------------------
        "can_view_financials": (
            "Permite consultar depreciación, valor en libros e información "
            "contable."
        ),
        "can_run_depreciation": (
            "Permite calcular lotes de depreciación."
        ),
        "can_post_depreciation": (
            "Permite contabilizar o cerrar lotes de depreciación."
        ),
        "can_manage_reconciliation": (
            "Permite importar y conciliar información contable."
        ),
        "can_export_reports": (
            "Permite exportar reportes patrimoniales y contables."
        ),
    }

    # ----------------------------------------------------------------------
    # Agrupaciones reutilizables
    # ----------------------------------------------------------------------
    _VIEW_PERMISSIONS = [
        "has_access_module",
        "can_view_dashboard",
        "can_view_assets",
    ]

    _INTAKE_OPERATOR_PERMISSIONS = [
        "can_create_asset",
        "can_submit_asset_intake",
        "can_manage_documents",
        "can_manage_photos",
    ]

    _CROSS_DEPARTMENT_INTAKE_PERMISSIONS = [
        "can_create_intake_for_any_department",
    ]

    _PATRIMONY_VALIDATION_PERMISSIONS = [
        "can_validate_patrimony_intake",
        "can_register_asset",
        "can_validate_documents",
        "can_view_restricted_documents",
    ]

    _PATRIMONY_OPERATOR_PERMISSIONS = [
        "can_edit_asset",
        "can_correct_asset",
        "can_manage_custody",
        "can_manage_movements",
        "can_manage_loans",
        "can_manage_disposals",
        "can_manage_documents",
        "can_manage_photos",
    ]

    _FINANCIAL_VIEW_PERMISSIONS = [
        "can_view_financials",
        "can_export_reports",
    ]

    # ----------------------------------------------------------------------
    # Roles funcionales
    # ----------------------------------------------------------------------
    ROLE_MAPPING = {
        "owner": list(PERMISSIONS.keys()),
        "admin": list(PERMISSIONS.keys()),
        "admin_patrimonio": list(PERMISSIONS.keys()),

        # Adquisiciones captura para cualquier dependencia, pero no valida ni
        # genera el activo oficial.
        "adquisiciones": _unique_permissions(
            _VIEW_PERMISSIONS,
            _INTAKE_OPERATOR_PERMISSIONS,
            _CROSS_DEPARTMENT_INTAKE_PERMISSIONS,
        ),

        # Operación ordinaria de almacén/patrimonio. Puede capturar para su
        # propio alcance, resguardar y mover, pero no aprobar el alta oficial.
        "almacenista": _unique_permissions(
            _VIEW_PERMISSIONS,
            _INTAKE_OPERATOR_PERMISSIONS,
            _PATRIMONY_OPERATOR_PERMISSIONS,
            [
                "can_accept_custody",
                "can_request_loans",
                "can_request_disposals",
                "can_scan_physical_audits",
            ],
        ),

        "auditor": _unique_permissions(
            _VIEW_PERMISSIONS,
            _FINANCIAL_VIEW_PERMISSIONS,
            [
                "can_validate_documents",
                "can_view_restricted_documents",
                "can_manage_physical_audits",
                "can_scan_physical_audits",
                "can_view_audit",
                "can_manage_reconciliation",
            ],
        ),

        # El servicio todavía comprobará que sólo decida sobre solicitudes
        # destinadas a una dependencia bajo su autoridad.
        "director": _unique_permissions(
            _VIEW_PERMISSIONS,
            _FINANCIAL_VIEW_PERMISSIONS,
            [
                "can_approve_department_intake",
                "can_authorize_movements",
                "can_request_loans",
                "can_authorize_loans",
                "can_request_disposals",
                "can_accept_custody",
            ],
        ),

        "resguardatario": [
            "has_access_module",
            "can_view_assets",
            "can_accept_custody",
            "can_request_loans",
            "can_request_disposals",
            "can_manage_documents",
            "can_manage_photos",
        ],

        "viewer": list(_VIEW_PERMISSIONS),

        # Compatibilidad con roles reservados del Core.
        "editor": _unique_permissions(
            _VIEW_PERMISSIONS,
            _INTAKE_OPERATOR_PERMISSIONS,
            ["can_request_loans", "can_request_disposals"],
        ),
        "reviewer": _unique_permissions(
            _VIEW_PERMISSIONS,
            _FINANCIAL_VIEW_PERMISSIONS,
            [
                "can_validate_documents",
                "can_scan_physical_audits",
                "can_view_audit",
            ],
        ),
    }

    ROLE_WEIGHTS = {
        "owner": 100,
        "admin": 95,
        "admin_patrimonio": 90,
        "adquisiciones": 75,
        "almacenista": 70,
        "auditor": 60,
        "editor": 55,
        "reviewer": 50,
        "director": 45,
        "resguardatario": 25,
        "viewer": 20,
    }

    # Todas estas rutas existen en el inventory_urls.py actual.
    SIDEBAR_MENU = [
        [
            "layout-dashboard",
            "Panel de Inventario",
            "inventory:dashboard",
            1,
            "can_view_dashboard",
        ],
        [
            "clipboard-list",
            "Solicitudes de Alta",
            "inventory:intake_list",
            2,
            "can_view_assets",
        ],
        [
            "circle-plus",
            "Nueva Solicitud",
            "inventory:intake_create",
            3,
            "can_create_asset",
        ],
        [
            "package-search",
            "Bienes Patrimoniales",
            "inventory:asset_list",
            4,
            "can_view_assets",
        ],
        [
            "file-signature",
            "Resguardos",
            "inventory:custody_list",
            5,
            "can_manage_custody",
        ],
        [
            "arrow-left-right",
            "Movimientos",
            "inventory:movement_list",
            6,
            "can_manage_movements",
        ],
        [
            "handshake",
            "Préstamos",
            "inventory:loan_list",
            7,
            "can_manage_loans",
        ],
        [
            "archive-x",
            "Bajas Patrimoniales",
            "inventory:disposal_list",
            8,
            "can_manage_disposals",
        ],
        [
            "folder-check",
            "Expediente Digital",
            "inventory:document_list",
            9,
            "can_manage_documents",
        ],
        [
            "scan-line",
            "Auditoría Física",
            "inventory:physical_audit_list",
            10,
            "can_manage_physical_audits",
        ],
        [
            "landmark",
            "Finanzas y SIGMAVER",
            "inventory:financial_dashboard",
            11,
            "can_view_financials",
        ],
    ]

    CAPABILITIES = {
        "can_operate": {
            "label": "Puede Operar Inventario",
            "help_text": (
                "Permite que la dependencia capture solicitudes, resguardos "
                "y operaciones ordinarias de Inventory."
            ),
        },
        "can_supervise": {
            "label": "Puede Supervisar Inventario",
            "help_text": (
                "Permite que la dependencia revise movimientos, "
                "conciliaciones, auditorías e indicadores patrimoniales."
            ),
        },
        "can_authorize": {
            "label": "Puede Autorizar Inventario",
            "help_text": (
                "Habilita a la dependencia para participar en decisiones que "
                "también exigen un permiso individual de autorización."
            ),
        },
    }


__all__ = ["InventoryPermissions"]
