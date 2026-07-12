# apps/inventory/urls/inventory_urls.py
from django.urls import path

from apps.inventory.views.inventory_views import inventory_dashboard_view


app_name = "inventory"


urlpatterns = [
    path("", inventory_dashboard_view, name="dashboard"),
]