SERVICIOS DISPONIBLES PARA LAS PRIMERAS VISTAS

audit_service.py
    Bitácora inmutable, snapshots y eventos de bypass.

folio_service.py
    Vista previa y generación concurrente del folio oficial.

intake_service.py
    Borrador, envío, aceptación departamental, revisión patrimonial,
    observación, aprobación, cancelación y registro del activo.

asset_service.py
    Correcciones auditadas y cambio de condición. Impide eliminar activos.

movement_service.py
    Registro append-only de movimientos patrimoniales.

REGLA DE USO EN VISTAS

    1. Form valida entrada.
    2. Form.to_dto() construye el DTO.
    3. Service ejecuta la transacción.
    4. Selector vuelve a consultar la pantalla.

Los servicios de resguardos, préstamos, bajas, documentos, auditoría física y
finanzas deben conectarse cuando se implementen sus vistas. No deben simularse
antes de cerrar sus máquinas de estados y sus evidencias obligatorias.
