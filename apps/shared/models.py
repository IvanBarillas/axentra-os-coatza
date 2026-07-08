# apps/shared/models.py
import uuid
from django.db import models
from django.utils import timezone

class AxentraBaseModel(models.Model):
    """
    Modelo abstracto base para entidades operativas de Axentra OS.
    Incluye: UUID como pk, estado activo/inactivo, baja lógica y trazabilidad.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    is_active = models.BooleanField("¿Está Activo?", default=True)
    is_deleted = models.BooleanField("¿Está Eliminado?", default=False, db_index=True)
    created_at = models.DateTimeField("Fecha de Creación", auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField("Última Actualización", auto_now=True)
    deleted_at = models.DateTimeField("Fecha de Baja Lógica", null=True, blank=True)

    class Meta:
        abstract = True

    def soft_delete(self, save: bool = True):
        """Marca el registro como eliminado sin borrarlo físicamente."""
        self.is_active = False
        self.is_deleted = True
        self.deleted_at = timezone.now()
        if save:
            self.save(update_fields=["is_active", "is_deleted", "deleted_at", "updated_at"])

    def restore(self, save: bool = True):
        """Restaura un registro dado de baja lógica."""
        self.is_active = True
        self.is_deleted = False
        self.deleted_at = None
        if save:
            self.save(update_fields=["is_active", "is_deleted", "deleted_at", "updated_at"])
            
