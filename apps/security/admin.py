# apps/security/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group

# Importamos todos nuestros modelos unificados de forma limpia
from apps.security.models import (
    User, UserProfile, Sede, Dependencia, 
    AreaOperativa, AppDependencyCapability, 
    AppModule, UserAppRole, TenantConfig, SecurityAuditLog
)

# =========================================================================
# 👤 BLOQUE 1: IDENTIDAD DIGITAL Y CUENTAS (EXTENSIÓN DE USER)
# =========================================================================
class UserProfileInline(admin.StackedInline):
    """Permite editar el expediente laboral del funcionario dentro de la misma vista del Usuario."""
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Expediente Laboral de Adscripción'
    fk_name = 'user'
    extra = 0


@admin.register(User)
class AxentraUserAdmin(BaseUserAdmin):
    """Rediseño estricto del administrador de usuarios adaptado a la autenticación por Email."""
    
    list_display = ('email', 'first_name', 'last_name', 'is_manager', 'is_staff', 'is_active', 'created_at')
    list_filter = ('is_manager', 'is_staff', 'is_active')
    ordering = ('-created_at',)
    inlines = (UserProfileInline,)
    
    # Redefinimos los buscadores y filtros del formulario para evitar que herede 'username'
    search_fields = ('email', 'first_name', 'last_name')
    filter_horizontal = ()
    list_filter = ('is_manager', 'is_staff', 'is_active')
    
    fieldsets = (
        ('Credenciales de Identidad', {'fields': ('email', 'password')}),
        ('Información Personal', {'fields': ('first_name', 'last_name', 'phone')}),
        ('Gobernanza y Privilegios Core', {'fields': ('is_manager', 'is_staff', 'is_active', 'must_change_password', 'is_email_verified')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password', 'first_name', 'last_name'),
        }),
    )


# =========================================================================
# 🏛️ BLOQUE 2: TOPOLOGÍA GUBERNAMENTAL (ORGANIGRAMA FISCO-JERÁRQUICO)
# =========================================================================
@admin.register(Sede)
class SedeAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'direccion', 'encargado_sede', 'is_active')
    search_fields = ('nombre', 'direccion')
    list_filter = ('is_active',)


class AreaOperativaInline(admin.TabularInline):
    """Permite ver y asignar Oficinas a una Dependencia directamente."""
    model = AreaOperativa
    extra = 1
    prepopulated_fields = {}


@admin.register(Dependencia)
class DependenciaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'slug', 'encargado_departamento', 'is_active', 'is_deleted')
    search_fields = ('nombre',)
    list_filter = ('is_active', 'is_deleted')
    inlines = [AreaOperativaInline]


@admin.register(AreaOperativa)
class AreaOperativaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'dependencia', 'sede_physic_link', 'is_active', 'is_deleted')
    search_fields = ('nombre', 'dependencia__nombre')
    list_filter = ('is_active', 'is_deleted')

    def sede_physic_link(self, obj):
        return obj.sede_fisica.nombre
    sede_physic_link.short_description = "Sede Física"


@admin.register(AppDependencyCapability)
class AppDependencyCapabilityAdmin(admin.ModelAdmin):
    list_display = ('dependencia', 'app', 'flag_alfa', 'flag_beta', 'created_at')
    list_filter = ('app', 'flag_alfa', 'flag_beta')
    search_fields = ('dependencia__nombre', 'app__name')


# =========================================================================
# 🛡️ BLOQUE 3: MATRICES, PERÍMETROS Y SINGLETON CONFIG
# =========================================================================
@admin.register(AppModule)
class AppModuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active')
    search_fields = ('name', 'slug')
    list_filter = ('is_active',)


@admin.register(UserAppRole)
class UserAppRoleAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'app_name', 'role', 'is_active', 'created_at')
    list_filter = ('role', 'is_active', 'app')
    search_fields = ('user__email', 'app__name')
    
    # Renderizado estético y limpio del campo JSON de privilegios overrides en el Admin
    fields = ('user', 'app', 'role', 'permissions_list', 'is_active')

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = "Funcionario"

    def app_name(self, obj):
        return obj.app.name
    app_name.short_description = "Módulo"


@admin.register(TenantConfig)
class TenantConfigAdmin(admin.ModelAdmin):
    """Administrador especial blindado para forzar visualmente el patrón Singleton."""
    list_display = ('entidad_nombre', 'siglas', 'app_name', 'rfc')
    
    def has_add_permission(self, request):
        """Bloquea el botón de 'Añadir' si ya existe un registro de marca en la BD."""
        if TenantConfig.objects.exists():
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        """Impide borrar la configuración institucional de marca para cuidar la consistencia."""
        return False


# =========================================================================
# 🛰️ BLOQUE 4: BITÁCORA FORENSE E HISTORIAL INMUTABLE (LOGS)
# =========================================================================
@admin.register(SecurityAuditLog)
class SecurityAuditLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'level_status', 'operator_email', 'action_name', 'target_scope')
    list_filter = ('level_status', 'created_at')
    search_fields = ('operator_user__email', 'action_name', 'target_scope')
    ordering = ('-created_at',)

    # Los logs son INMUTABLES: Se bloquea la edición o borrado desde el panel admin
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False

    def operator_email(self, obj):
        return obj.operator_user.email
    operator_email.short_description = "Operador"