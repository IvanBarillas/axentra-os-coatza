# apps/inventory/admin/asset_admin.py

"""
Administración completa de Inventory para desarrollo.

Características:
- Registra automáticamente todos los modelos de Inventory.
- Muestra todos los campos concretos en los listados.
- Muestra todos los campos en los formularios.
- Permite buscar en textos, correos, UUID y relaciones.
- Genera filtros para estados, opciones, booleanos y fechas.
- Usa raw_id_fields para evitar desplegables demasiado grandes.
- Mantiene visibles los campos técnicos y de auditoría.

Esta configuración está pensada para desarrollo y diagnóstico.
Antes de producción conviene crear administradores específicos y
restringir los campos sensibles o de sólo lectura.
"""

from django.apps import apps
from django.contrib import admin
from django.contrib.admin.sites import AlreadyRegistered
from django.db import models


# =============================================================================
# CONFIGURACIÓN GENERAL DEL SITIO
# =============================================================================

admin.site.site_header = "Axentra OS · Administración"
admin.site.site_title = "Axentra OS"
admin.site.index_title = "Administración del sistema"


# =============================================================================
# ADMINISTRADOR BASE DE DESARROLLO
# =============================================================================

class InventoryDevelopmentAdmin(admin.ModelAdmin):
    """
    Administrador genérico para visualizar completamente cualquier modelo
    perteneciente a Inventory.
    """

    list_per_page = 50
    list_max_show_all = 5000

    save_on_top = True
    save_as = True

    preserve_filters = True
    show_full_result_count = True

    actions_on_top = True
    actions_on_bottom = True

    empty_value_display = "—"

    # -------------------------------------------------------------------------
    # Campos mostrados en el listado
    # -------------------------------------------------------------------------

    def get_list_display(self, request):
        """
        Muestra todos los campos concretos del modelo.

        No incluye relaciones inversas ni ManyToMany porque no son columnas
        concretas de la tabla.
        """

        return tuple(
            field.name
            for field in self.model._meta.concrete_fields
        )

    # -------------------------------------------------------------------------
    # Campos de sólo lectura
    # -------------------------------------------------------------------------

    def get_readonly_fields(self, request, obj=None):
        """
        Los campos no editables definidos por Django se presentan como
        sólo lectura, pero continúan siendo visibles.
        """

        readonly = []

        for field in self.model._meta.concrete_fields:
            if not field.editable:
                readonly.append(field.name)

        return tuple(readonly)

    # -------------------------------------------------------------------------
    # Relaciones
    # -------------------------------------------------------------------------

    def get_raw_id_fields(self, request):
        """
        Usa selectores por ID para todas las relaciones.

        Esto evita cargar miles de usuarios, activos, dependencias o
        movimientos dentro de un <select>.
        """

        return tuple(
            field.name
            for field in self.model._meta.concrete_fields
            if isinstance(
                field,
                (models.ForeignKey, models.OneToOneField),
            )
        )

    def get_queryset(self, request):
        """
        Reduce consultas repetidas al mostrar relaciones ForeignKey.
        """

        queryset = super().get_queryset(request)

        relation_fields = [
            field.name
            for field in self.model._meta.concrete_fields
            if isinstance(
                field,
                (models.ForeignKey, models.OneToOneField),
            )
        ]

        if relation_fields:
            queryset = queryset.select_related(*relation_fields)

        return queryset

    # -------------------------------------------------------------------------
    # Búsqueda
    # -------------------------------------------------------------------------

    def get_search_fields(self, request):
        """
        Habilita búsqueda automática sobre:

        - CharField
        - TextField
        - EmailField
        - SlugField
        - UUIDField
        - Llaves foráneas por su identificador
        """

        search_fields = []

        text_field_types = (
            models.CharField,
            models.TextField,
            models.EmailField,
            models.SlugField,
        )

        for field in self.model._meta.concrete_fields:
            if isinstance(field, text_field_types):
                search_fields.append(field.name)

            elif isinstance(field, models.UUIDField):
                search_fields.append(f"={field.name}")

            elif isinstance(
                field,
                (models.ForeignKey, models.OneToOneField),
            ):
                search_fields.append(f"={field.name}__pk")

        return tuple(search_fields)

    # -------------------------------------------------------------------------
    # Filtros
    # -------------------------------------------------------------------------

    def get_list_filter(self, request):
        """
        Genera filtros para:

        - Campos con choices.
        - Booleanos.
        - Fechas.
        - Fechas y horas.
        - Relaciones ForeignKey.
        """

        list_filter = []

        for field in self.model._meta.concrete_fields:
            if field.primary_key:
                continue

            if field.choices:
                list_filter.append(field.name)
                continue

            if isinstance(field, models.BooleanField):
                list_filter.append(field.name)
                continue

            if isinstance(field, (models.DateField, models.DateTimeField)):
                list_filter.append(field.name)
                continue

            if isinstance(
                field,
                (models.ForeignKey, models.OneToOneField),
            ):
                list_filter.append(
                    (
                        field.name,
                        admin.RelatedOnlyFieldListFilter,
                    )
                )

        return tuple(list_filter)

    # -------------------------------------------------------------------------
    # Ordenamiento
    # -------------------------------------------------------------------------

    def get_ordering(self, request):
        """
        Respeta el ordering declarado en Meta.

        Si el modelo no declara uno, ordena por fecha de creación o por PK.
        """

        declared_ordering = self.model._meta.ordering

        if declared_ordering:
            return declared_ordering

        field_names = {
            field.name
            for field in self.model._meta.concrete_fields
        }

        if "created_at" in field_names:
            return ("-created_at",)

        return (self.model._meta.pk.name,)

    # -------------------------------------------------------------------------
    # Navegación por fecha
    # -------------------------------------------------------------------------

    def get_date_hierarchy(self, request):
        """
        Utiliza created_at como navegación cronológica cuando exista.
        """

        field_names = {
            field.name
            for field in self.model._meta.concrete_fields
        }

        if "created_at" in field_names:
            return "created_at"

        return None


# =============================================================================
# REGISTRO AUTOMÁTICO
# =============================================================================

inventory_app_config = apps.get_app_config("inventory")


for inventory_model in inventory_app_config.get_models():
    try:
        admin.site.register(
            inventory_model,
            InventoryDevelopmentAdmin,
        )
    except AlreadyRegistered:
        # Permite conservar un administrador específico si algún modelo
        # ya fue registrado antes.
        pass
    
