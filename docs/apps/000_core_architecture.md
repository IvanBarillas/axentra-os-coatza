# AXENTRA OS — Arquitectura del Core

## Sistema Operativo Municipal Modular

Este documento describe la arquitectura vigente de Axentra OS y establece las reglas que deben respetar el Core y las aplicaciones que se incorporen posteriormente.

Axentra OS está construido actualmente como un monolito modular en Django. El sistema comparte autenticación, identidad institucional, estructura organizacional, permisos, auditoría y el chasis visual, pero mantiene separados sus dominios funcionales.

---

# 1. Arquitectura general

La plataforma se divide en tres capas conceptuales:

1. **Core de plataforma**
2. **Módulos funcionales**
3. **Aplicaciones satélite futuras**

El Core proporciona:

- Autenticación.
- Identidad institucional.
- Funcionarios.
- Sedes, dependencias y áreas.
- Gobierno de accesos.
- Permisos finos.
- Auditoría forense.
- Registro de aplicaciones.
- Shell visual.
- Navegación dinámica.
- Integración HTMX.

Los módulos actuales son:

| Identificador | Responsabilidad                                                   |
| ------------- | ----------------------------------------------------------------- |
| `security`    | Ciberseguridad, permisos, auditoría y configuración institucional |
| `accounts`    | Funcionarios y expedientes laborales                              |
| `organigrama` | Sedes, dependencias y áreas operativas                            |

Actualmente estos dominios se encuentran dentro de la aplicación física `apps.security`, pero se exponen como módulos lógicos independientes mediante namespaces, manifiestos y permisos.

---

# 2. Estructura principal del proyecto

```text
axentra-os/
├── apps/
│   ├── shared/
│   │   ├── apps_config.py
│   │   ├── context_processors.py
│   │   ├── manifest_registry.py
│   │   ├── models.py
│   │   ├── templates/
│   │   └── utils/
│   │
│   └── security/
│       ├── dtos/
│       ├── forms/
│       ├── models/
│       ├── selectors/
│       ├── services/
│       ├── templates/
│       ├── urls/
│       ├── utils/
│       ├── views/
│       ├── decorators.py
│       └── permissions.py
│
├── core/
│   ├── settings/
│   ├── urls.py
│   ├── views.py
│   ├── asgi.py
│   └── wsgi.py
│
├── templates/
│   ├── navigation/
│   ├── partials/
│   ├── public/
│   └── shell/
│
├── static/
├── media/
├── docs/
├── manage.py
└── pyproject.toml
```

---

# 3. Principios arquitectónicos

## 3.1 Monolito modular

Axentra OS no utiliza microservicios para sus funciones internas actuales.

Los módulos comparten:

- Proceso Django.
- Base de datos.
- Modelo de usuario.
- Sesión.
- Shell visual.
- Sistema de permisos.
- Auditoría.

La separación se realiza mediante:

- Namespaces de URL.
- Manifiestos.
- Servicios.
- Selectores.
- Formularios.
- DTO.
- Directorios de plantillas.
- Permisos por módulo.

Esta organización permite desarrollar inicialmente con sencillez y extraer aplicaciones satélite solamente cuando exista una necesidad real.

## 3.2 Fuente única de verdad

Cada concepto debe tener un responsable claro:

| Concepto                 | Fuente de verdad                   |
| ------------------------ | ---------------------------------- |
| Módulos reconocidos      | `apps/shared/apps_config.py`       |
| Manifiestos              | `permissions.py` de cada módulo    |
| Descubrimiento           | `apps/shared/manifest_registry.py` |
| Membresías               | `UserAppRole`                      |
| Permisos del usuario     | `permissions_list`                 |
| Estructura institucional | Sede, Dependencia y AreaOperativa  |
| Identidad del municipio  | `TenantConfig`                     |
| Navegación               | Manifiesto y context processors    |
| Auditoría                | `SecurityAuditLog`                 |

## 3.3 Baja lógica

Las entidades operativas heredan de `AxentraBaseModel`.

Este modelo proporciona:

- UUID como llave primaria.
- `is_active`.
- `is_deleted`.
- `created_at`.
- `updated_at`.
- `deleted_at`.
- `soft_delete()`.
- `restore()`.

Las consultas funcionales deben excluir registros con:

```python
is_deleted=True
```

Una baja lógica no equivale únicamente a desactivar el registro. Siempre deben evaluarse ambos campos cuando corresponda:

```python
is_active=True,
is_deleted=False,
```

---

# 4. Flujo de navegación

El flujo principal es:

```nginx
Portal público
    ↓
Autenticación
    ↓
Launcher de aplicaciones
    ↓
Módulo autorizado
    ↓
Workbench
    ↓
Contenido o expediente contextual
```

## 4.1 Portal público

Ruta:

```nginx
/
```

Vista:

```nginx
intro_portal_view
```

Responsabilidades:

- Mostrar la página institucional.
- No utilizar el shell interno.
- Redirigir al launcher si ya existe una sesión.

## 4.2 Autenticación

Ruta base:

```nginx
/app/auth/
```

Responsabilidades:

- Inicio de sesión.
- Cierre de sesión.
- Recuperación o administración futura de credenciales.
- Protección mediante Django Axes.

El usuario de Axentra OS utiliza correo electrónico como identificador:

```python
USERNAME_FIELD = "email"
```

## 4.3 Launcher

Ruta:

```nginx
/index/
```

Vista:

```nginx
index_hub_view
```

El launcher consulta los módulos permitidos y presenta únicamente las aplicaciones autorizadas.

Los usuarios con bypass global pueden visualizar todos los módulos registrados.

---

# 5. Shell visual vigente

La composición visual oficial es:

```text
shell/base.html
└── shell/workbench.html
    ├── global-sidebar
    ├── module-sidebar opcional
    └── page-content
```

## 5.1 `shell/base.html`

Es el documento HTML principal.

Contiene:

- Sidebar global.
- Navbar.
- Contenedor `#workbench`.
- Raíces para modales, drawers, mensajes y overlays.
- Inicialización de HTMX.
- Inicialización de Alpine.js.
- Inicialización de Lucide.
- Inicialización de Chart.js.
- Modal global de confirmación.
- Eventos globales HTMX.

## 5.2 `shell/workbench.html`

Define la superficie operativa de cada módulo.

Su estructura es:

```html
<div id="workbench">
  <aside id="module-sidebar">
    <!-- Sidebar contextual opcional -->
  </aside>

  <section>
    <main id="page-content">
      <!-- Contenido funcional -->
    </main>
  </section>
</div>
```

## 5.3 Reglas del shell

Las nuevas pantallas deben extender:

```django
{% extends "shell/workbench.html" %}
```

No deben crear nuevamente:

- Sidebar global.
- Navbar global.
- Footer global.
- Contenedor `#workbench`.
- Raíces de modales.
- Scripts base.

Una pantalla decide si necesita sidebar secundario mediante:

```python
context = {
    "show_module_sidebar": True,
}
```

Las pantallas simples pueden usar:

```python
context = {
    "show_module_sidebar": False,
}
```

---

# 6. Contrato HTMX

Axentra OS utiliza dos destinos principales.

## 6.1 Cambio de módulo

Cuando el usuario selecciona una aplicación desde el sidebar global:

```html
hx-target="#workbench" hx-push-url="true"
```

La vista debe devolver una plantilla de tipo:

```text
<modulo>/workbench/
```

Esta respuesta puede incluir:

- Sidebar del módulo.
- Contenido inicial.
- Estado de navegación.

## 6.2 Navegación dentro de un módulo

Cuando el usuario navega dentro de una aplicación:

```html
hx-target="#page-content" hx-push-url="true"
```

La vista debe devolver una plantilla de tipo:

```text
<modulo>/content/
```

El shell y el sidebar permanecen estables.

## 6.3 Fragmentos transaccionales

Para tablas, formularios, filas, filtros o mensajes se utilizan plantillas dentro de:

```text
<modulo>/htmx/
```

Estas respuestas deben reemplazar únicamente el componente afectado.

## 6.4 Detección en las vistas

Las vistas deben distinguir entre:

- Navegación directa.
- Sustitución de `#workbench`.
- Sustitución de `#page-content`.
- Fragmentos pequeños.

Ejemplo:

```python
is_htmx = (
    str(request.headers.get("HX-Request", ""))
    .strip()
    .lower()
    == "true"
)

target_htmx = request.headers.get("HX-Target", "")

if is_htmx and target_htmx == "workbench":
    return render(
        request,
        "nueva_app/workbench/dashboard_workbench.html",
        context,
    )

if is_htmx and target_htmx == "page-content":
    return render(
        request,
        "nueva_app/content/dashboard_content.html",
        context,
    )

return render(
    request,
    "nueva_app/pages/dashboard.html",
    context,
)
```

## 6.5 Organización oficial de plantillas

Cada módulo debe utilizar, cuando corresponda:

```nginx
templates/nueva_app/
├── pages/
├── workbench/
├── content/
├── htmx/
└── contextual/
```

### `pages`

Documento para navegación directa o recarga completa.

### `workbench`

Respuesta destinada a reemplazar `#workbench`.

### `content`

Respuesta destinada a reemplazar `#page-content`.

### `htmx`

Fragmentos transaccionales pequeños.

### `contextual`

Sidebar o navegación específica de un expediente.

---

# 7. Sistema de aplicaciones y manifiestos

## 7.1 Registro de identificadores

Los módulos reconocidos se declaran en:

```nginx
apps/shared/apps_config.py
```

Ejemplo:

```python
class AppIdentifier:
    SECURITY = "security"
    ACCOUNTS = "accounts"
    ORGANIGRAMA = "organigrama"
    NUEVA_APP = "nueva_app"

    @classmethod
    def get_choices(cls):
        return [
            (cls.SECURITY, "Ciberseguridad Central"),
            (cls.ACCOUNTS, "Plantilla de Personal"),
            (cls.ORGANIGRAMA, "Estructura Orgánica"),
            (cls.NUEVA_APP, "Nueva Aplicación"),
        ]
```

El identificador debe:

- Estar en minúsculas.
- Ser estable.
- No depender del nombre visible.
- Coincidir con el slug persistido en `AppModule`.
- Coincidir con el namespace del módulo.

## 7.2 Descubrimiento de manifiestos

El registro se encuentra en:

```nginx
apps/shared/manifest_registry.py
```

`AxentraOSRegistry` intenta localizar el manifiesto en:

```nginx
apps.<app_code>.permissions
```

Mientras los dominios Core permanezcan centralizados, puede utilizar como compatibilidad:

```nginx
apps.security.permissions
```

Las nuevas aplicaciones satélite deben incluir su propio archivo:

```nginx
apps/nueva_app/permissions.py
```

## 7.3 Contenido del manifiesto

Cada manifiesto puede declarar:

- `APP_CODE`
- `PERMISSIONS`
- `ROLE_MAPPING`
- `ROLE_WEIGHTS`
- `SIDEBAR_MENU`
- `CAPABILITIES`
- Menús contextuales adicionales

Ejemplo:

```python
from apps.shared.apps_config import AppIdentifier


class NuevaAppPermissions:
    APP_CODE = AppIdentifier.NUEVA_APP

    PERMISSIONS = {
        "has_access_module": (
            "Permite ingresar al módulo."
        ),
        "can_view_records": (
            "Permite consultar registros."
        ),
        "can_create_records": (
            "Permite crear registros."
        ),
        "can_edit_records": (
            "Permite modificar registros."
        ),
        "can_delete_records": (
            "Permite aplicar bajas lógicas."
        ),
    }

    ROLE_MAPPING = {
        "owner": [
            "has_access_module",
            "can_view_records",
            "can_create_records",
            "can_edit_records",
            "can_delete_records",
        ],
        "admin": [
            "has_access_module",
            "can_view_records",
            "can_create_records",
            "can_edit_records",
        ],
        "editor": [
            "has_access_module",
            "can_view_records",
            "can_create_records",
            "can_edit_records",
        ],
        "reviewer": [
            "has_access_module",
            "can_view_records",
        ],
        "viewer": [
            "has_access_module",
            "can_view_records",
        ],
    }

    ROLE_WEIGHTS = {
        "owner": 100,
        "admin": 80,
        "editor": 60,
        "reviewer": 40,
        "viewer": 20,
    }

    SIDEBAR_MENU = [
        {
            "icon": "layout-dashboard",
            "name": "Panel principal",
            "url": "nueva_app:dashboard",
            "order": 10,
            "permission": "has_access_module",
        },
        {
            "icon": "database",
            "name": "Registros",
            "url": "nueva_app:record_list",
            "order": 20,
            "permission": "can_view_records",
        },
    ]

    CAPABILITIES = {
        "can_operate": {
            "label": "Puede operar",
            "help_text": (
                "Permite a la dependencia ejecutar "
                "procesos de esta aplicación."
            ),
        },
        "can_supervise": {
            "label": "Puede supervisar",
            "help_text": (
                "Permite a la dependencia supervisar "
                "procesos de esta aplicación."
            ),
        },
        "can_authorize": {
            "label": "Puede autorizar",
            "help_text": (
                "Permite a la dependencia autorizar "
                "operaciones críticas."
            ),
        },
    }
```

---

# 8. Gobierno de accesos

Axentra OS utiliza un modelo de autorización por aplicación.

## 8.1 `AppModule`

Representa una aplicación registrada:

```python
class AppModule(AxentraBaseModel):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
```

## 8.2 `UserAppRole`

Relaciona un funcionario con una aplicación:

```python
class UserAppRole(AxentraBaseModel):
    user = models.ForeignKey(User, ...)
    app = models.ForeignKey(AppModule, ...)
    role = models.CharField(max_length=50)
    permissions_list = models.JSONField(default=list)
```

La combinación usuario–aplicación es única.

## 8.3 Permisos finos

`permissions_list` contiene un snapshot de las llaves autorizadas:

```json
["has_access_module", "can_view_records", "can_create_records"]
```

La base de datos determina las llaves concedidas al usuario. El manifiesto determina cuáles llaves son válidas para la aplicación.

Nunca debe confiarse solamente en que una opción no aparezca en el HTML. Toda operación sensible debe protegerse también en backend.

## 8.4 Roles

Los roles agrupan permisos predeterminados, pero no sustituyen a los permisos finos.

El rol responde:

> ¿Qué perfil funcional tiene el usuario dentro del módulo?

Los permisos responden:

> ¿Qué acciones concretas puede ejecutar?

## 8.5 Regla de owner

El rol `owner` puede recibir todas las llaves declaradas por el manifiesto.

Los roles inferiores deben conservar como mínimo:

```text
has_access_module
```

si se desea que el usuario pueda ingresar al módulo.

Los permisos adicionales deben validarse contra `PERMISSIONS` antes de persistirse.

## 8.6 Bypass global

Puede existir bypass para:

- `is_superuser`.
- `is_manager`.
- Perfil con condición root administrativa.

El bypass debe utilizarse solamente para gobierno global del Core.

No debe confundirse:

- Administrador global del sistema.
- Owner de una aplicación.
- Administrador funcional de una aplicación.

---

# 9. Guardián de rutas

Las vistas funcionales deben protegerse con:

```python
axentra_module_gate
```

El alias `axentra_gate_enforcer` puede mantenerse temporalmente por compatibilidad, pero el nombre arquitectónico oficial es:

```python
axentra_module_gate
```

Ejemplo:

```python
from django.contrib.auth.decorators import login_required

from apps.security.decorators import axentra_module_gate
from apps.shared.apps_config import AppIdentifier


@login_required
@axentra_module_gate(
    AppIdentifier.NUEVA_APP,
    required_fine_permission="can_view_records",
)
def record_list_view(request):
    ...
```

El guardián realiza:

1. Validación de autenticación.
2. Bloqueo de usuarios dados de baja.
3. Resolución de bypass global.
4. Lectura de `UserAppRole`.
5. Validación de acceso al módulo.
6. Validación del permiso fino.
7. Construcción del menú permitido.
8. Inyección de contexto en el request.
9. Telemetría de acceso.

El decorador deja disponibles:

```python
request.axentra_permissions
request.axentra_permissions_list
request.axentra_is_root
request.axentra_active_module
request.axentra_sidebar_menu
```

---

# 10. Navegación dinámica

Los menús se generan desde el manifiesto activo.

Cada elemento debe incluir:

```python
{
    "icon": "database",
    "name": "Registros",
    "url": "nueva_app:record_list",
    "order": 20,
    "permission": "can_view_records",
}
```

Antes de mostrarlo, el Core verifica:

- Módulo activo.
- Permisos del usuario.
- Permiso requerido.
- Estado del usuario.
- Estado de la membresía.
- Bypass global.

Ocultar un enlace no sustituye la protección de la vista.

---

# 11. Estructura organizacional

Axentra OS modela la institución mediante:

- `Sede`
- `Dependencia`
- `AreaOperativa`
- `UserProfile`

## 11.1 Sede

Representa un inmueble físico.

## 11.2 Dependencia

Representa una unidad administrativa:

- Secretaría.
- Dirección.
- Coordinación.
- Departamento.

Puede participar en una jerarquía mediante:

```python
parent = models.ForeignKey(
    "self",
    null=True,
    blank=True,
    related_name="children",
    on_delete=models.PROTECT,
)
```

## 11.3 Área operativa

Representa la intersección entre una dependencia y una sede:

```text
Dependencia + Sede = Área operativa
```

Esto permite que una dependencia opere en diferentes inmuebles sin duplicar su identidad administrativa.

## 11.4 Perfil del funcionario

`UserProfile` conecta al funcionario con su área.

A partir del área se obtiene:

- Dependencia.
- Sede.
- Adscripción institucional.

---

# 12. Capacidades organizacionales

Los permisos y las capacidades resuelven problemas diferentes.

## Permisos

Responden:

> ¿Qué puede hacer este usuario?

## Capacidades

Responden:

> ¿Cómo participa esta dependencia dentro de una aplicación?

Las capacidades se almacenan mediante:

```python
AppDependencyCapability
```

Ejemplos:

- Puede operar.
- Puede supervisar.
- Puede autorizar.
- Configuración particular mediante `custom_settings`.

Una capacidad no debe utilizarse como sustituto de un permiso de usuario.

---

# 13. Capas de cada módulo

## 13.1 Views

Responsabilidades:

- Recibir la petición.
- Leer parámetros.
- Detectar HTMX.
- Invocar selectores y servicios.
- Preparar contexto.
- Elegir la plantilla correspondiente.

Las vistas no deben concentrar consultas complejas ni reglas transaccionales extensas.

## 13.2 Selectors

Responsabilidades:

- Consultas de lectura.
- Filtros.
- Agregaciones.
- Optimización con `select_related`.
- Optimización con `prefetch_related`.
- Construcción de datos para dashboards.

Los selectores no deben ejecutar mutaciones.

## 13.3 Services

Responsabilidades:

- Altas.
- Modificaciones.
- Bajas lógicas.
- Restauraciones.
- Asignación de permisos.
- Validaciones de negocio.
- Transacciones.
- Auditoría de mutaciones.

Las operaciones relacionadas deben ejecutarse dentro de:

```python
transaction.atomic()
```

## 13.4 Forms

Responsabilidades:

- Validar datos de entrada.
- Normalizar valores.
- Aplicar validaciones de formulario.
- Proporcionar errores de usuario.

## 13.5 DTO

Responsabilidades:

- Transportar resultados estructurados.
- Evitar diccionarios ambiguos.
- Separar la representación del modelo persistente.

## 13.6 Templates

Responsabilidades:

- Presentación.
- Interacciones HTMX.
- Estados visuales.
- Mensajes.
- Componentes.

Las plantillas no deben implementar reglas críticas de autorización.

---

# 14. Auditoría forense

Las operaciones sensibles deben registrarse en:

```python
SecurityAuditLog
```

El registro puede contener:

- Aplicación.
- Tipo de acción.
- Componente.
- Nivel.
- Nombre de la acción.
- Operador.
- Usuario afectado.
- Dirección IP.
- User agent.
- Payload estructurado.
- Criterio de búsqueda.
- Alcance de la operación.

Las mutaciones relevantes deben utilizar el auditor central para mantener un formato consistente.

No deben registrarse:

- Contraseñas.
- Tokens.
- Secretos.
- Cookies.
- Llaves privadas.
- Datos innecesariamente sensibles.

---

# 15. Context processors

El Core utiliza context processors para exponer información transversal.

## `global_tenant_settings`

Entrega:

```django
{{ tenant }}
```

Incluye identidad institucional y activos visuales.

## `user_module_permissions`

Entrega:

```django
{{ allowed_modules }}
{{ is_global_admin }}
```

Controla las aplicaciones visibles en el launcher.

## `menu_dinamico_processor`

Entrega:

```django
{{ modulo_actual }}
{{ menu_actual }}
{{ sidebar_menu }}
```

El menú se obtiene del manifiesto y de los permisos efectivos.

Los context processors no deben sustituir la validación backend.

---

# 16. Incorporación de una aplicación nueva

## Paso 1. Crear la aplicación

```bash
python manage.py startapp nueva_app apps/nueva_app
```

Debe quedar registrada correctamente como paquete Django.

## Paso 2. Registrar su identificador

Editar:

```text
apps/shared/apps_config.py
```

Agregar:

```python
NUEVA_APP = "nueva_app"
```

y su elección correspondiente.

## Paso 3. Crear el manifiesto

Crear:

```text
apps/nueva_app/permissions.py
```

Debe contener como mínimo:

- `APP_CODE`.
- `PERMISSIONS`.
- `ROLE_MAPPING`.
- `ROLE_WEIGHTS`.
- `SIDEBAR_MENU`.

## Paso 4. Registrar la aplicación Django

Agregarla a `LOCAL_APPS`:

```python
LOCAL_APPS = [
    "apps.shared.apps.SharedConfig",
    "apps.security.apps.SecurityConfig",
    "apps.nueva_app.apps.NuevaAppConfig",
]
```

## Paso 5. Crear URLs con namespace

Ejemplo:

```python
# apps/nueva_app/urls.py

from django.urls import path

from .views import dashboard_view


app_name = "nueva_app"

urlpatterns = [
    path("", dashboard_view, name="dashboard"),
]
```

Incluirlas en el proyecto:

```python
path(
    "app/nueva-app/",
    include("apps.nueva_app.urls"),
)
```

## Paso 6. Proteger las vistas

```python
@login_required
@axentra_module_gate(
    AppIdentifier.NUEVA_APP,
    required_fine_permission="has_access_module",
)
def dashboard_view(request):
    ...
```

## Paso 7. Crear las plantillas

```text
apps/nueva_app/templates/nueva_app/
├── pages/
│   └── dashboard.html
├── workbench/
│   └── dashboard_workbench.html
├── content/
│   └── dashboard_content.html
├── htmx/
└── contextual/
```

## Paso 8. Aplicar migraciones

```bash
python manage.py makemigrations nueva_app
python manage.py migrate
```

El proceso de sincronización debe crear o verificar el registro correspondiente en `AppModule`.

## Paso 9. Verificar permisos

Comprobar:

- Usuario sin membresía: acceso denegado.
- Usuario con `has_access_module`: acceso general.
- Usuario sin permiso fino: operación denegada.
- Owner: permisos completos del módulo.
- Manager global: bypass esperado.
- Usuario dado de baja: acceso denegado.

## Paso 10. Verificar HTMX

Comprobar:

- Acceso directo.
- Recarga de página.
- Cambio desde sidebar global.
- Navegación interna.
- Botón atrás.
- Historial del navegador.
- Mensajes.
- Formularios con errores.
- Confirmaciones.
- Restauración de iconos después de un swap.

---

# 17. Convenciones obligatorias

## Python

- Nombres descriptivos.
- Vistas pequeñas.
- Selectores para lectura.
- Servicios para escritura.
- Transacciones para mutaciones relacionadas.
- Tipado cuando mejore claridad.
- Sin credenciales dentro del código.

## URLs

- Namespace por aplicación.
- Nombres estables.
- Rutas agrupadas por dominio.
- UUID para entidades del Core.

## Templates

- `pages` para documento completo.
- `workbench` para `#workbench`.
- `content` para `#page-content`.
- `htmx` para fragmentos.
- `contextual` para navegación de expediente.

## Permisos

- Toda aplicación debe declarar `has_access_module`.
- Las llaves deben ser estables.
- Backend y frontend deben validar el mismo permiso.
- No deben persistirse llaves inexistentes en el manifiesto.

## Datos

- Utilizar baja lógica.
- Evitar eliminaciones físicas salvo necesidad justificada.
- Auditar operaciones críticas.
- Filtrar registros eliminados.
- Evitar consultas repetidas desde templates.

---

# 18. Seguridad operativa

Nunca deben almacenarse en el repositorio:

- Contraseñas.
- Secret keys.
- Tokens.
- Credenciales PostgreSQL.
- Credenciales SMTP.
- Llaves privadas.
- Contraseñas iniciales de administradores.

La configuración sensible debe recibirse mediante variables de entorno o secretos del entorno de despliegue.

Producción debe utilizar:

- `DEBUG=False`.
- Cookies seguras.
- Redirección HTTPS.
- `CSRF_TRUSTED_ORIGINS`.
- `ALLOWED_HOSTS` explícitos.
- Argon2 como hasher principal.
- PostgreSQL.
- Logs persistentes.
- Nginx o proxy inverso.
- Gunicorn.

---

# 19. Pruebas mínimas requeridas

Cada módulo debe cubrir como mínimo:

## Acceso

- Usuario anónimo.
- Usuario dado de baja.
- Usuario sin módulo.
- Usuario con módulo.
- Usuario sin permiso fino.
- Usuario con permiso fino.
- Owner.
- Manager global.

## Servicios

- Alta correcta.
- Edición correcta.
- Baja lógica.
- Restauración.
- Validaciones de jerarquía.
- Auditoría.
- Rollback transaccional.

## HTMX

- Respuesta de página.
- Respuesta de workbench.
- Respuesta de contenido.
- Fragmento con error.
- Fragmento con éxito.
- Mensajes fuera de banda cuando corresponda.

## Organigrama

- Dependencia jerárquica.
- Área por dependencia y sede.
- Restricción de duplicados.
- Adscripción de funcionarios.
- Protección de relaciones mediante `PROTECT`.

---

# 20. Regla final

Una nueva funcionalidad pertenece al Core solamente cuando es transversal a varias aplicaciones.

Ejemplos de responsabilidades Core:

- Identidad.
- Autenticación.
- Permisos.
- Organigrama.
- Auditoría.
- Documentos compartidos.
- Notificaciones compartidas.
- Configuración institucional.

Una funcionalidad de negocio debe pertenecer a su aplicación:

- Predial.
- Catastro.
- Comercio.
- Agua.
- Tesorería.
- Obras.
- Recursos Humanos.
- Cabildo.

El Core gobierna identidad, acceso, organización e integración. Las aplicaciones satélite implementan los procesos municipales especializados sin duplicar las capacidades de plataforma.

---

AXENTRA MÉXICO © 2026  
Arquitectura del Core de Axentra OS
