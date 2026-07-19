from django.apps import AppConfig


class InventoryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.inventory"
    label = "inventory"
    verbose_name = "Inventario Patrimonial"

    def ready(self):
        from apps.inventory.workflows import register_inventory_workflows

        register_inventory_workflows()
