# apps/security/models/organigrama.py
from django.db import models
from django.utils.text import slugify
from django.conf import settings
from apps.shared.models import AxentraBaseModel

class Sede(AxentraBaseModel):
    """Inmuebles físicos del Ayuntamiento."""
    nombre = models.CharField("Nombre del Edificio", max_length=150, unique=True)
    direccion = models.CharField("Dirección Física", max_length=255, blank=True)
    encargado_sede = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name="sedes_tecnicas_a_cargo", verbose_name="Encargado Técnico de Sede (TI)", null=True, blank=True, help_text="Líder técnico responsable del soporte en este edificio.")

    class Meta:
        db_table = "axentra_org_sedes"
        verbose_name = "Sede / Edificio"
        verbose_name_plural = "Sedes / Edificios"
        ordering = ["nombre"]

    def __str__(self): return self.nombre

class Dependencia(AxentraBaseModel):
    """Direcciones o Secretarías institucionales de la estructura del Ayuntamiento."""
    nombre = models.CharField("Nombre de la Dependencia", max_length=150, unique=True)
    slug = models.SlugField(max_length=150, unique=True, editable=False)
    sedes_ocupadas = models.ManyToManyField(Sede, through="security.AreaOperativa", related_name="dependencias", verbose_name="Sedes Físicas Operativas")
    encargado_departamento = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name="dependencias_administrativas_a_cargo", verbose_name="Titular / Encargado de la Dependencia", null=True, blank=True, help_text="Director o Jefe de Área con facultades para gestionar su personal.")

    class Meta:
        db_table = "axentra_org_dependencias"
        verbose_name = "Dependencia / Dirección"
        verbose_name_plural = "Dependencias / Direcciones"
        ordering = ["nombre"]

    def __str__(self): return self.nombre

    def save(self, *args, **kwargs):
        if not self.slug: self.slug = slugify(self.nombre)
        super().save(*args, **kwargs)

class AreaOperativa(AxentraBaseModel):
    """Oficina o área de una dependencia dentro de una sede física."""
    dependencia = models.ForeignKey(Dependencia, on_delete=models.PROTECT, related_name="areas", verbose_name="Dependencia Superior")
    sede_fisica = models.ForeignKey(Sede, on_delete=models.PROTECT, related_name="areas", verbose_name="Sede Física de Operación")
    nombre = models.CharField("Nombre de la Oficina / Área", max_length=150)
    slug = models.SlugField(max_length=150, editable=False)

    class Meta:
        db_table = "axentra_org_areas_operativas"
        verbose_name = "Área Operativa / Oficina"
        verbose_name_plural = "Áreas Operativas / Oficinas"
        ordering = ["nombre"]
        constraints = [models.UniqueConstraint(fields=["dependencia", "sede_fisica", "slug"], name="uq_area_dependencia_sede_slug")]

    def __str__(self): return f"{self.nombre} ➡️ {self.dependencia.nombre} ({self.sede_fisica.nombre})"

    def save(self, *args, **kwargs):
        if not self.slug: self.slug = slugify(self.nombre)
        super().save(*args, **kwargs)

class AppDependencyCapability(AxentraBaseModel):
    """Federación de capacidades abstractas por dependencia vinculadas a un módulo."""
    app = models.ForeignKey("security.AppModule", on_delete=models.CASCADE, related_name="dependencias_vinculadas")
    dependencia = models.ForeignKey(Dependencia, on_delete=models.CASCADE, related_name="capacidades", verbose_name="Dependencia")
    can_operate = models.BooleanField("Puede Operar", default=False)
    can_supervise = models.BooleanField("Puede Supervisar", default=False)
    can_authorize = models.BooleanField("Puede Autorizar", default=False)
    custom_settings = models.JSONField("Configuraciones Avanzadas JSON", default=dict, blank=True)

    class Meta:
        db_table = "axentra_org_app_capabilities"
        verbose_name = "Capacidad de Dependencia"
        verbose_name_plural = "Capacidades de Dependencias"
        constraints = [models.UniqueConstraint(fields=["app", "dependencia"], name="uq_app_dependencia_capability")]

    def __str__(self): return f"{self.dependencia.nombre} ➡️ {self.app.name}"
    
