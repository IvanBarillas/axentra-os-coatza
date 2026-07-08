# apps/security/models/infrastructure.py
from django.db import models
from django.conf import settings
from apps.shared.models import AxentraBaseModel

class AppModule(AxentraBaseModel):
    """Inventario de módulos federados en el Core OS."""
    name = models.CharField("Nombre del Módulo", max_length=100)
    slug = models.SlugField("Identificador Técnico", unique=True)
    description = models.TextField("Descripción Operativa", blank=True)

    class Meta:
        db_table = "axentra_sec_modules"
        verbose_name = "Módulo Instalado"
        verbose_name_plural = "Módulos Instalados"
        ordering = ["name"]

    def __str__(self): return self.name

class UserAppRole(AxentraBaseModel):
    """Matriz dinámica de membresías por app con roles declarados por manifiesto."""

    class ReservedRoles(models.TextChoices):
        OWNER = "owner", "👑 Dueño / Director General"
        ADMIN = "admin", "🔒 Administrador"
        EDITOR = "editor", "📝 Editor / Operador"
        REVIEWER = "reviewer", "👁️ Revisor / Auditor"
        VIEWER = "viewer", "👤 Solo Lectura"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="roles", verbose_name="Funcionario Público")
    app = models.ForeignKey(AppModule, on_delete=models.CASCADE, related_name="roles", verbose_name="Módulo Autorizado")
    
    role = models.CharField(
        "Rol Funcional en el Módulo", max_length=50, default=ReservedRoles.VIEWER, db_index=True,
        help_text="Rol declarado en el permissions.py del módulo. Ej: owner, admin, director_rh, sma_manager."
    )
    
    permissions_list = models.JSONField(
        "Lista de Permisos Finos", default=list, blank=True,
        help_text="Snapshot de permisos finos derivados del rol funcional."
    )

    class Meta:
        db_table = "axentra_sec_user_roles"
        verbose_name = "Permiso de Aplicación"
        verbose_name_plural = "Permisos de Aplicaciones"
        constraints = [models.UniqueConstraint(fields=["user", "app"], name="uq_user_app_role")]

    def __str__(self):
        return f"{self.user.email} ➡️ {self.app.name} ({self.role})"

    def has_fine_permission(self, permission_string: str) -> bool:
        if not self.is_active or self.is_deleted:
            return False
        if self.role == self.ReservedRoles.OWNER:
            return True
        return permission_string in (self.permissions_list or [])

class TenantConfig(AxentraBaseModel):
    """Configuración de Marca e Identidad Legal del Ayuntamiento."""
    app_name = models.CharField("Nombre del Sistema", max_length=50, default="GovStack")
    entidad_nombre = models.CharField("Nombre del Ayuntamiento / Institución", max_length=150, default="H. Ayuntamiento Constitucional")
    siglas = models.CharField("Siglas de la Entidad", max_length=15, default="GOV")
    direccion_oficial = models.TextField("Dirección Institucional Sede", blank=True)
    rfc = models.CharField("RFC de la Institución", max_length=13, blank=True)
    logo_light = models.ImageField("Escudo Oficial (Fondo Claro)", upload_to="institucion/logos/", blank=True, null=True)
    logo_dark = models.ImageField("Escudo Oficial (Fondo Oscuro)", upload_to="institucion/logos/", blank=True, null=True)
    primary_color_class = models.CharField("Color de Acento (Tailwind Class)", max_length=30, default="slate-950", help_text="Clase nativa de Tailwind para branding.")

    class Meta:
        db_table = "axentra_core_tenant_config"
        verbose_name = "Configuración Institucional"
        verbose_name_plural = "Configuraciones Institucionales"

    def __str__(self): return f"Configuración Activa: {self.entidad_nombre}"

    def save(self, *args, **kwargs):
        if not self.pk and TenantConfig.objects.exists(): return TenantConfig.objects.first()
        return super().save(*args, **kwargs)