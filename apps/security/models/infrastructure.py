# apps/security/models/infrastructure.py
import uuid
from django.db import models
from django.conf import settings

class AppModule(models.Model):
    """Inventario de módulos federados en el Core OS."""
    name = models.CharField("Nombre del Módulo", max_length=100)
    slug = models.SlugField("Identificador Técnico", unique=True)
    description = models.TextField("Descripción Operativa", blank=True)
    is_active = models.BooleanField("Estatus Activo", default=True)

    class Meta:
        db_table = 'axentra_sec_modules'
        verbose_name = "Módulo Instalado"
        verbose_name_plural = "Módulos Instalados"
        ordering = ['name']

    def __str__(self):
        return self.name


class UserAppRole(models.Model):
    """Matriz corporativa dinámica con Overrides quirúrgicos vía JSONField."""
    class Roles(models.TextChoices):
        OWNER = "owner", "👑 Dueño / Director General (Acceso Total)"
        ADMIN = "admin", "🔒 Administrador de Módulo"
        EDITOR = "editor", "📝 Editor / Operador / Capturista"
        REVIEWER = "reviewer", "👁️ Revisor / Auditor"
        VIEWER = "viewer", "👤 Solo Lectura"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # 🟢 OPTIMIZADO: Accesor directo desde el objeto Usuario (ej: usuario.roles.all())
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='roles',
        verbose_name="Funcionario Público"
    )
    # 🟢 OPTIMIZADO: Accesor limpio desde el objeto Módulo (ej: modulo.roles.all())
    app = models.ForeignKey(
        AppModule, 
        on_delete=models.CASCADE, 
        related_name='roles',
        verbose_name="Módulo Autorizado"
    )
    role = models.CharField(
        "Rol Asignado en el Módulo", 
        max_length=20, 
        choices=Roles.choices, 
        default=Roles.VIEWER
    )
    
    permissions_list = models.JSONField(
        "Lista de Permisos Finos (JSON Overrides)", 
        default=list, 
        blank=True,
        help_text="Clonación atómica de privilegios para permitir Overrides individuales."
    )
    
    is_active = models.BooleanField("Membresía Activa", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'axentra_sec_user_roles'
        verbose_name = "Permiso de Aplicación"
        verbose_name_plural = "Permisos de Aplicaciones"
        unique_together = ('user', 'app')

    def __str__(self):
        return f'{self.user.email} ➡️ {self.app.name} ({self.get_role_display()})'

    def has_fine_permission(self, permission_string: str) -> bool:
        """Determina de forma síncrona si la credencial requerida está activa en el pool."""
        if not self.is_active:
            return False
        if self.role == self.Roles.OWNER:
            return True
        return permission_string in (self.permissions_list or [])


class TenantConfig(models.Model):
    """Configuración inmutable de Marca e Identidad Legal del Ayuntamiento (Singleton)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    app_name = models.CharField("Nombre del Sistema", max_length=50, default="GovStack")
    entidad_nombre = models.CharField("Nombre del Ayuntamiento / Institución", max_length=150, default="H. Ayuntamiento Constitucional")
    siglas = models.CharField("Siglas de la Entidad", max_length=15, default="GOV")
    direccion_oficial = models.TextField("Dirección Institucional Sede", blank=True)
    rfc = models.CharField("RFC de la Institución", max_length=13, blank=True)
    
    logo_light = models.ImageField("Escudo Oficial (Fondo Claro)", upload_to="institucion/logos/", blank=True, null=True)
    logo_dark = models.ImageField("Escudo Oficial (Fondo Oscuro)", upload_to="institucion/logos/", blank=True, null=True)
    
    primary_color_class = models.CharField(
        "Color de Acento (Tailwind Class)", 
        max_length=30, 
        default="slate-950", 
        help_text="Clase nativa de Tailwind para branding."
    )

    class Meta:
        db_table = 'axentra_core_tenant_config'
        verbose_name = "Configuración Institucional"
        verbose_name_plural = "Configuraciones Institucionales"

    def __str__(self):
        return f"Configuración Activa: {self.entidad_nombre}"

    def save(self, *args, **kwargs):
        if not self.pk and TenantConfig.objects.exists():
            return TenantConfig.objects.first()
        return super().save(*args, **kwargs)