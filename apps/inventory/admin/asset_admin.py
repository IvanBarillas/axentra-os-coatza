"""
Administración completa de Inventory para desarrollo.

Características:
- Registra automáticamente todos los modelos de Inventory.
- Muestra todos los campos concretos en los listados.
- Conserva visibles todos los campos editables y técnicos en formularios.
- Permite buscar texto, UUID, PK y referencias directas.
- Genera filtros para choices, booleanos, fechas y relaciones.
- Usa raw_id_fields para relaciones potencialmente voluminosas.

Esta configuración está pensada para desarrollo y diagnóstico.
Antes de producción deben crearse administradores específicos y restringirse
las mutaciones sobre folios, estados, trazabilidad y datos financieros.
"""

from uuid import UUID

from django.apps import apps
from django.contrib import admin
from django.contrib.admin.sites import AlreadyRegistered
from django.core.exceptions import ValidationError
from django.db import DataError, models
from django.db.models import Q


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
    """Administrador genérico de máxima visibilidad para Inventory."""

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
    # Utilidades internas
    # -------------------------------------------------------------------------

    def _concrete_fields(self):
        return tuple(self.model._meta.concrete_fields)

    def _direct_relation_fields(self):
        return tuple(
            field
            for field in self._concrete_fields()
            if isinstance(field, (models.ForeignKey, models.OneToOneField))
        )

    def _field_names(self):
        return {field.name for field in self._concrete_fields()}

    # -------------------------------------------------------------------------
    # Listado
    # -------------------------------------------------------------------------

    def get_list_display(self, request):
        """
        Muestra todas las columnas concretas de la tabla.

        Las relaciones inversas y ManyToMany no aparecen en el listado porque
        no corresponden a una única columna concreta.
        """

        return tuple(field.name for field in self._concrete_fields())

    # -------------------------------------------------------------------------
    # Campos visibles y de sólo lectura
    # -------------------------------------------------------------------------

    def get_readonly_fields(self, request, obj=None):
        """
        Conserva visibles los campos no editables.

        La PK se vuelve de sólo lectura al editar para impedir que desde el
        administrador se cambie accidentalmente la identidad de un registro.
        """

        readonly = {
            field.name
            for field in self._concrete_fields()
            if not field.editable
        }

        if obj is not None:
            readonly.add(self.model._meta.pk.name)

        return tuple(
            field.name
            for field in self._concrete_fields()
            if field.name in readonly
        )

    # -------------------------------------------------------------------------
    # Relaciones
    # -------------------------------------------------------------------------

    def get_raw_id_fields(self, request):
        """
        Usa selectores por ID para ForeignKey, OneToOne y ManyToMany locales.

        Esto evita cargar miles de usuarios, activos, dependencias o
        movimientos dentro de un elemento ``select``.
        """

        direct_relations = [field.name for field in self._direct_relation_fields()]
        many_to_many = [
            field.name
            for field in self.model._meta.many_to_many
            if field.editable and not field.auto_created
        ]

        return tuple(direct_relations + many_to_many)

    def get_queryset(self, request):
        """Evita consultas repetidas al representar relaciones directas."""

        queryset = super().get_queryset(request)
        relation_names = [field.name for field in self._direct_relation_fields()]

        if relation_names:
            queryset = queryset.select_related(*relation_names)

        return queryset

    # -------------------------------------------------------------------------
    # Búsqueda
    # -------------------------------------------------------------------------

    def get_search_fields(self, request):
        """
        Habilita búsqueda parcial segura sobre campos textuales.

        Los UUID, PK y relaciones se procesan por separado en
        ``get_search_results`` para que una cadena ordinaria no provoque un
        error de conversión en la base de datos.
        """

        searchable_types = (
            models.CharField,
            models.TextField,
            models.EmailField,
            models.SlugField,
        )

        return tuple(
            field.name
            for field in self._concrete_fields()
            if isinstance(field, searchable_types)
        )

    def get_search_results(self, request, queryset, search_term):
        queryset, may_have_duplicates = super().get_search_results(
            request,
            queryset,
            search_term,
        )

        term = str(search_term or "").strip()
        if not term:
            return queryset, may_have_duplicates

        identifier_filter = Q()
        has_identifier_filter = False

        # UUID propios del modelo.
        try:
            uuid_value = UUID(term)
        except (TypeError, ValueError, AttributeError):
            uuid_value = None

        if uuid_value is not None:
            for field in self._concrete_fields():
                if isinstance(field, models.UUIDField):
                    identifier_filter |= Q(**{field.name: uuid_value})
                    has_identifier_filter = True

            # Relaciones cuyo modelo destino usa UUID como PK.
            for field in self._direct_relation_fields():
                if isinstance(field.target_field, models.UUIDField):
                    identifier_filter |= Q(**{f"{field.name}_id": uuid_value})
                    has_identifier_filter = True

        # PK y relaciones enteras.
        if term.isdigit():
            integer_value = int(term)
            integer_types = (
                models.AutoField,
                models.BigAutoField,
                models.SmallAutoField,
                models.IntegerField,
                models.BigIntegerField,
                models.SmallIntegerField,
                models.PositiveIntegerField,
                models.PositiveBigIntegerField,
                models.PositiveSmallIntegerField,
            )

            if isinstance(self.model._meta.pk, integer_types):
                identifier_filter |= Q(pk=integer_value)
                has_identifier_filter = True

            for field in self._direct_relation_fields():
                if isinstance(field.target_field, integer_types):
                    identifier_filter |= Q(**{f"{field.name}_id": integer_value})
                    has_identifier_filter = True

        if has_identifier_filter:
            try:
                identifier_queryset = self.get_queryset(request).filter(
                    identifier_filter
                )
                queryset = queryset | identifier_queryset
            except (ValidationError, ValueError, TypeError, DataError):
                # La búsqueda textual continúa funcionando aunque algún backend
                # no pueda convertir un identificador concreto.
                pass

        return queryset, may_have_duplicates

    # -------------------------------------------------------------------------
    # Filtros
    # -------------------------------------------------------------------------

    def get_list_filter(self, request):
        """Genera filtros útiles sin incluir la llave primaria."""

        list_filter = []

        for field in self._concrete_fields():
            if field.primary_key:
                continue

            if field.choices:
                list_filter.append(field.name)
            elif isinstance(field, models.BooleanField):
                list_filter.append(field.name)
            elif isinstance(field, (models.DateField, models.DateTimeField)):
                list_filter.append(field.name)
            elif isinstance(field, (models.ForeignKey, models.OneToOneField)):
                list_filter.append(
                    (field.name, admin.RelatedOnlyFieldListFilter)
                )

        return tuple(list_filter)

    # -------------------------------------------------------------------------
    # Ordenamiento y navegación temporal
    # -------------------------------------------------------------------------

    def get_ordering(self, request):
        declared_ordering = self.model._meta.ordering

        if declared_ordering:
            return tuple(declared_ordering)

        if "created_at" in self._field_names():
            return ("-created_at",)

        return (self.model._meta.pk.name,)

    def get_date_hierarchy(self, request):
        if "created_at" in self._field_names():
            return "created_at"

        return None


# =============================================================================
# REGISTRO AUTOMÁTICO DE TODOS LOS MODELOS DE INVENTORY
# =============================================================================

inventory_app_config = apps.get_app_config("inventory")

for inventory_model in inventory_app_config.get_models():
    try:
        admin.site.register(inventory_model, InventoryDevelopmentAdmin)
    except AlreadyRegistered:
        # Conserva un ModelAdmin específico registrado previamente.
        pass


__all__ = ["InventoryDevelopmentAdmin"]

