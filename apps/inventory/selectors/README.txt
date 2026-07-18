Destino:
    apps/inventory/selectors/

Instalación:
    1. Sustituye el contenido de esa carpeta por estos archivos.
    2. Conserva el nombre del paquete ``selectors``.
    3. Copia también el core_directory.py actualizado a:
       apps/inventory/integrations/core_directory.py

Verificación:
    python manage.py check

Regla arquitectónica:
    Estos archivos sólo consultan. No crean, actualizan, autorizan ni eliminan
    registros. Toda escritura o transición de estado debe ir en services/.
