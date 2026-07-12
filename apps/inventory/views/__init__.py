# apps/inventory/views/__init__.py

# 👤 PILAR 1: GESTIÓN DE EXPEDIENTES Y PERSONAL (ACCOUNTS)
from .inventory_views import (
    inventory_dashboard_view,
    asset_list_view,
    asset_create_view,
    asset_detail_view,     

)

# Exposición oficial para los enrutadores de URLs de Axentra OS
__all__ = [
    # Accounts
    'inventory_dashboard_view',
    'asset_list_view',
    'asset_create_view',
    'asset_detail_view',    
]