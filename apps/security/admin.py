# apps/security/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
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
    # 🟢 OPTIMIZADO: Se añade el funcionario destino en el listado para análisis rápido
    list_display = ('created_at', 'get_level_badge', 'operator_email', 'target_email', 'action_name', 'target_scope')
    list_filter = ('level_status', 'created_at')
    # 🟢 FORENSIC SEARCH: Buscador extendido hacia el correo del afectado para rastreos quirúrgicos
    search_fields = ('operator_user__email', 'target_user__email', 'action_name', 'target_scope')
    ordering = ('-created_at',)
    
    # Declaramos los campos que se verán al dar clic en el detalle del Log
    fields = ('id', 'created_at', 'level_status', 'operator_user', 'target_user', 'action_name', 'target_scope', 'telemetria_json_pretty')
    # Forzamos que los metadatos e ID sean de solo lectura para evitar alteraciones accidentales en el detalle
    readonly_fields = ('id', 'created_at', 'telemetria_json_pretty')

    # 🟢 ACCESO TOTAL: Eliminados los métodos 'has_add_permission/has_delete_permission' por tu decreto.
    # Como administrador único, posees el control físico para purgar registros o inyectar eventos de testing.

    def operator_email(self, obj):
        return obj.operator_user.email
    operator_email.short_description = "Operador"
    operator_email.admin_order_field = 'operator_user__email'

    def target_email(self, obj):
        return obj.target_user.email if obj.target_user else "GLOBAL / SISTEMA"
    target_email.short_description = "Funcionario Destino"
    target_email.admin_order_field = 'target_user__email'

    # 🎨 COMPONENTE VISUAL: Badge a color para identificar la criticidad al vuelo en la grilla
    def get_level_badge(self, obj):
        if obj.level_status == SecurityAuditLog.Levels.CRITICAL:
            return mark_safe('<span style="background: #fee2e2; color: #991b1b; padding: 3px 8px; rounded: 6px; font-weight: bold; border-radius: 6px;">🚨 CRITICAL</span>')
        elif obj.level_status == SecurityAuditLog.Levels.SUCCESS:
            return mark_safe('<span style="background: #dcfce7; color: #166534; padding: 3px 8px; rounded: 6px; font-weight: bold; border-radius: 6px;">🟢 SUCCESS</span>')
        return mark_safe('<span style="background: #e0f2fe; color: #075985; padding: 3px 8px; rounded: 6px; font-weight: bold; border-radius: 6px;">🔵 INFO</span>')
    get_level_badge.short_description = "Nivel del Evento"
    get_level_badge.admin_order_field = 'level_status'

    # 🖥️ INTROSPECCIÓN GRANULAR: Formatea el JSONField de Postgres con estilo tipo consola oscura
    def telemetria_json_pretty(self, obj):
        if not obj.payload_json:
            return "No se capturó telemetría adicional."
        # Formateamos el diccionario a un string JSON con sangría limpia de 4 espacios
        json_bonito = json.dumps(obj.payload_json, indent=4, ensure_ascii=False)
        return mark_safe(
            f'<pre style="background: #0f172a; color: #38bdf8; padding: 16px; border-radius: 12px; font-family: monospace; font-size: 11px; max-height: 500px; overflow-y: auto;">{json_bonito}</pre>'
        )
    telemetria_json_pretty.short_description = "Detalle del Delta Criptográfico (Antes vs Después)"