# apps/security/models/organigrama.py
import uuid
from django.db import models
from django.utils.text import slugify
from django.conf import settings

class Sede(models.Model):
    """Inmuebles físicos del Ayuntamiento (Ej: Palacio Municipal, Anexo, Obras Públicas)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField("Nombre del Edificio", max_length=150, unique=True)
    direccion = models.CharField("Dirección Física", max_length=255, blank=True)

    encargado_sede = models.ForeignKey(
        settings.AUTH_USER_MODEL,  
        on_delete=models.SET_NULL,
        related_name="sedes_tecnicas_a_cargo",
        verbose_name="Encargado Técnico de Sede (TI)",
        null=True,
        blank=True,
        help_text="Líder técnico responsable del soporte en este edificio."
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'axentra_org_sedes'
        verbose_name = "Sede / Edificio"
        verbose_name_plural = "Sedes / Edificios"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Dependencia(models.Model):
    """Direcciones o Secretarías institucionales de la estructura del Ayuntamiento."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField("Nombre de la Dependencia", max_length=150, unique=True)
    slug = models.SlugField(max_length=150, unique=True, editable=False)

    sedes_ocupadas = models.ManyToManyField(
        Sede,
        through='security.AreaOperativa',
        related_name='dependencias_alojadas',
        verbose_name="Sedes Físicas Operativas"
    )

    encargado_departamento = models.ForeignKey(
        settings.AUTH_USER_MODEL,  
        on_delete=models.SET_NULL,
        related_name="dependencias_administrativas_a_cargo",
        verbose_name="Titular / Encargado de la Dependencia",
        null=True,
        blank=True,
        help_text="Director o Jefe de Área con facultades para gestionar su personal."
    )

    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField("¿Está Eliminado?", default=False)

    class Meta:
        db_table = 'axentra_org_dependencias'
        verbose_name = "Dependencia / Dirección"
        verbose_name_plural = "Dependencias / Direcciones"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nombre)
        super().save(*args, **kwargs)


class AreaOperativa(models.Model):
    """Matriz de asignación multidimensional Muchos a Muchos con candado de unicidad."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    dependencia = models.ForeignKey(
        Dependencia, 
        on_delete=models.CASCADE, 
        related_name="areas_operativas_instaladas",
        verbose_name="Dependencia Superior"
    )
    sede_fisica = models.ForeignKey(
        Sede, 
        on_delete=models.PROTECT, 
        related_name="oficinas_maestras_instaladas",
        verbose_name="Sede Física de Operación"
    )
    
    nombre = models.CharField("Nombre de la Oficina / Área", max_length=150)
    slug = models.SlugField(max_length=150, editable=False)
    is_active = models.BooleanField("¿Está Activo?", default=True)
    is_deleted = models.BooleanField("¿Está Eliminado?", default=False)

    class Meta:
        db_table = 'axentra_org_areas_operativas'
        verbose_name = "Área Operativa / Oficina"
        verbose_name_plural = "Áreas Operativas / Oficinas"
        ordering = ['nombre']
        unique_together = ('dependencia', 'sede_fisica', 'slug')

    def __str__(self):
        return f"{self.nombre} ➡️ {self.dependencia.nombre} ({self.sede_fisica.nombre})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nombre)
        super().save(*args, **kwargs)


class AppDependencyCapability(models.Model):
    """Federación de capacidades abstractas por dependencia vinculadas a un módulo."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    app = models.ForeignKey(
        'security.AppModule', 
        on_delete=models.CASCADE, 
        related_name="dependencias_vinculadas"
    )
    dependencia = models.ForeignKey(
        Dependencia, 
        on_delete=models.CASCADE, 
        related_name="capacidades_apps"
    )
    
    flag_alfa = models.BooleanField("Capacidad Primaria (Alfa)", default=False)
    flag_beta = models.BooleanField("Capacidad Secundaria (Beta)", default=False)
    
    custom_settings = models.JSONField("Configuraciones Avanzadas JSON", default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'axentra_org_app_capabilities'
        unique_together = ('app', 'dependencia')
        verbose_name = "Capacidad de Dependencia"
        verbose_name_plural = "Capacidades de Dependencias"

    def __str__(self):
        return f"{self.dependencia.nombre} ➡️ {self.app.name}"