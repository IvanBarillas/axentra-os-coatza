# apps/inventory/urls/inventory_urls.py
from django.urls import path

from apps.inventory.views.inventory_views import inventory_dashboard_view, asset_list_view, asset_create_view, asset_detail_view


app_name = "inventory"


urlpatterns = [
    path("", inventory_dashboard_view, name="dashboard"),
    
    path("assets/", asset_list_view, name="asset_list"),
    path("assets/new/", asset_create_view, name="asset_create"),
    path("assets/<uuid:asset_id>/", asset_detail_view, name="asset_detail"),
]