# apps/inventory/admin/__init__.py

"""
Configuración administrativa de Inventory.

Importar este módulo ejecuta el registro automático de todos los modelos
definido en asset_admin.py.
"""

from apps.inventory.admin.asset_admin import InventoryDevelopmentAdmin


__all__ = ["InventoryDevelopmentAdmin"]

