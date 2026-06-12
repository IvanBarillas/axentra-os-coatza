# apps/security/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from pydantic import json
from apps.security.forms import CustomUserCreationForm, CustomUserChangeForm
from django.utils.safestring import mark_safe

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
    # 🟢 CORRECCIÓN: Apunta al related_name 'axentra_profile' corregido en tus modelos
    model = UserProfile
    extra = 1
    can_delete = True  # Paso libre total para borrar perfiles desde la ficha del usuario

@admin.register(User)
class AxentraUserAdmin(BaseUserAdmin):
    """Administrador blindado adaptado al esquema funcional por Email."""
    
    # Inyección de formularios limpios (Anula los rígidos de Django con username)
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    
    list_display = ('email', 'first_name', 'last_name', 'is_manager', 'is_staff', 'is_active', 'created_at')
    list_filter = ('is_manager', 'is_staff', 'is_active')
    ordering = ('-created_at',)
    inlines = (UserProfileInline,)
    search_fields = ('email', 'first_name', 'last_name')
    filter_horizontal = ()
    
    fieldsets = (
        ('Credenciales de Identidad', {'fields': ('email', 'password')}),
        ('Información Personal', {'fields': ('first_name', 'last_name', 'phone')}),
        ('Gobernanza y Privilegios', {'fields': ('is_manager', 'is_staff', 'is_active', 'must_change_password', 'is_email_verified')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password', 'first_name', 'last_name'),
        }),
    )

    def get_form(self, request, obj=None, **kwargs):
        """Si es alta, usa el add_form limpio; si es edición, delega al padre sin verificar usernames."""
        if obj is None:
            return self.add_form
        return super(BaseUserAdmin, self).get_form(request, obj, **kwargs)


# =========================================================================
# 🏛️ BLOQUE 2: TOPOLOGÍA GUBERNAMENTAL (ORGANIGRAMA FISCO-JERÁRQUICO)
# =========================================================================
@admin.register(Sede)
class SedeAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'direccion', 'encargado_sede', 'is_active')
    search_fields = ('nombre', 'direccion')
    list_filter = ('is_active',)


class AreaOperativaInline(admin.TabularInline):
    """Permite ver, crear y remover Oficinas a una Dependencia directamente."""
    model = AreaOperativa
    extra = 1


@admin.register(Dependencia)
class DependenciaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'slug', 'encargado_departamento', 'is_active', 'is_deleted')
    search_fields = ('nombre',)
    list_filter = ('is_active', 'is_deleted')
    inlines = [AreaOperativaInline]


@admin.register(AreaOperativa)
class AreaOperativaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'dependencia', 'sede_link', 'is_active', 'is_deleted')
    search_fields = ('nombre', 'dependencia__nombre', 'sede_fisica__nombre')
    list_filter = ('is_active', 'is_deleted')

    # 🟢 SANEADO: Limpieza de nombres spanglish por variables nativas del ORM
    def sede_link(self, obj):
        return obj.sede_fisica.nombre
    sede_link.short_description = "Sede Física"


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
    fields = ('user', 'app', 'role', 'permissions_list', 'is_active')

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = "Funcionario"

    def app_name(self, obj):
        return obj.app.name
    app_name.short_description = "Módulo"


@admin.register(TenantConfig)
class TenantConfigAdmin(admin.ModelAdmin):
    """Administrador Singleton sin bloqueos para control total del dueño."""
    list_display = ('entidad_nombre', 'siglas', 'app_name', 'rfc')
    
    # 🟢 REMOVIDOS LOS BLOQUEOS: Ahora puedes agregar o borrar configuraciones a tu antojo
    pass


# =========================================================================
# 🛰️ BLOQUE 4: BITÁCORA FORENSE E HISTORIAL INMUTABLE (LOGS)
# =========================================================================
@admin.register(SecurityAuditLog)
class SecurityAuditLogAdmin(admin.ModelAdmin):
    # Grilla de listado general
    list_display = (
        'created_at', 
        'level_status', 
        'app_namespace', 
        'action_type',        
        'module_component',
        'operator_email', 
        'target_email', 
        'action_name', 
        'search_target', 
        'ip_address'
    )
    
    # Filtros laterales de búsqueda rápida
    list_filter = ('app_namespace', 'action_type', 'module_component', 'level_status', 'created_at')
    
    # Buscador superior en texto plano indexado
    search_fields = (
        'operator_user__email', 
        'target_user__email', 
        'action_type', 
        'module_component', 
        'search_target', 
        'ip_address'
    )
    
    ordering = ('-created_at',)
    
    # 🟢 SANEADO: Estructura limpia de la vista detallada usando las columnas nativas del modelo.
    # Cambiamos tu método 'telemetria_json_pretty' por 'payload_json' directo de la base de datos.
    fields = (
        'id', 
        'created_at', 
        'level_status', 
        'app_namespace', 
        'operator_user', 
        'target_user', 
        'action_name', 
        'search_target', 
        'target_scope', 
        'ip_address', 
        'user_agent', 
        'payload_json'  # ◄── El JSON directo de Postgres sin intermediarios
    )
    
    # Todos los campos en modo lectura para garantizar que no haya alteraciones accidentales
    readonly_fields = (
        'id', 
        'created_at', 
        'level_status',
        'app_namespace', 
        'operator_user', 
        'target_user', 
        'action_name', 
        'search_target', 
        'target_scope', 
        'ip_address', 
        'user_agent', 
        'payload_json'  # ◄── Visualización pura sin interferencia de HTML/CSS
    )

    # Métodos de resolución rápidos para las columnas del listado general
    def operator_email(self, obj):
        return obj.operator_user.email if obj.operator_user else "SISTEMA"
    operator_email.short_description = "Operador"

    def target_email(self, obj):
        return obj.target_user.email if obj.target_user else "GLOBAL / SISTEMA"
    target_email.short_description = "Funcionario Destino"