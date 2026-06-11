# AXENTRA OS — Core Platform Manifesto

## Sistema Operativo Municipal Federado y Core de Ciberseguridad Aislada

Este repositorio concentra el Core de Infraestructura y Gobernanza Central de Axentra OS. Está diseñado bajo una arquitectura matricial de software federado, actuando como el motor maestro para despliegues en Ayuntamientos y Administraciones Públicas Municipales.

---

## 1. Manifiesto del Sistema de Permisos y Roles

Axentra OS no utiliza el sistema tradicional de permisos de Django (`auth.Permission`). El acceso perimetral opera mediante un catálogo atómico federado mantenido en memoria y persistido mediante un `JSONField` dentro de PostgreSQL (`UserAppRole`).

### Protocolo para crear y federar una nueva aplicación satélite

Cuando un desarrollador crea un nuevo módulo (por ejemplo: patrimonio o catastro), debe seguir estrictamente el siguiente flujo.

### Paso 1. Registrar el identificador Core

Agregar el slug e identificador de la aplicación en el catálogo unificado.

**Archivo:** `apps/shared/apps_config.py`

```python
class AppIdentifier:
    ORGANIGRAMA = "organigrama"
    ACCOUNTS = "accounts"
    SECURITY = "security"
    STAFF = "staff"
    DYNAMIC_FORMS = "dynamic_forms"
    HELPDESK = "helpdesk"
    NUEVA_APP = "nueva_app"

    @classmethod
    def get_choices(cls):
        return [
            (cls.ORGANIGRAMA, "ORGANIGRAMA Y MATRIZ"),
            (cls.ACCOUNTS, "CONTROL DE PERSONAL"),
            (cls.SECURITY, "CIBERSEGURIDAD CENTRAL"),
            (cls.STAFF, "INTELSTAFF AUSENCIAS"),
            (cls.DYNAMIC_FORMS, "FORMULARIOS DINÁMICOS"),
            (cls.HELPDESK, "MESA DE AYUDA"),
            (cls.NUEVA_APP, "NUEVA APP EJEMPLO"),
        ]
```

### Paso 2. Declarar el manifiesto de privilegios local

Dentro de la nueva aplicación debe existir obligatoriamente un archivo `permissions.py`. Este archivo define la metadata del lanzador, las llaves finas y el mapeo de perfiles.

**Archivo:** `apps/nueva_app/permissions.py`

### Desglose técnico de los componentes

El archivo `permissions.py` concentra la definición declarativa del comportamiento del módulo dentro del ecosistema de Axentra OS. Cada bloque cumple una responsabilidad específica y debe entenderse como parte del contrato de integración entre la aplicación satélite y el Core.

#### `LAUNCHER_CARD`

**Identidad en el Lanzador General**

Configura los metadatos necesarios para que el chasis de Axentra OS renderice la tarjeta de acceso rápido del módulo dentro del Home principal de la plataforma.

Responsabilidades:

- Definir el título visible del módulo.
- Proporcionar una descripción institucional.
- Configurar iconografía y estilos visuales.
- Especificar la ruta de aterrizaje (`url_name`).
- Determinar si el módulo pertenece al Core o corresponde a una aplicación satélite.

---

#### `PERMISSIONS`

**Catálogo Atómico de Llaves**

#### Anatomía del archivo `permissions.py`

El archivo `permissions.py` concentra la definición declarativa del comportamiento del módulo dentro del ecosistema de Axentra OS. Cada bloque cumple una responsabilidad específica y constituye parte del contrato de integración entre una aplicación satélite y el Core de la plataforma.

Su propósito es centralizar la identidad del módulo, los privilegios atómicos, los perfiles predeterminados, la navegación protegida y las capacidades organizacionales que modifican el comportamiento del sistema.

---

#### `LAUNCHER_CARD`

**Identidad en el Lanzador General**

Configura los metadatos necesarios para que el chasis de Axentra OS renderice la tarjeta de acceso rápido del módulo dentro del Home principal de la plataforma.

Responsabilidades:

- Definir el título visible del módulo.
- Proporcionar una descripción institucional.
- Configurar iconografía y estilos visuales.
- Especificar la ruta de aterrizaje (`url_name`).
- Determinar si el módulo pertenece al Core o corresponde a una aplicación satélite.

En términos prácticos, `LAUNCHER_CARD` representa la capa de descubrimiento y navegación inicial del módulo.

---

#### `PERMISSIONS`

**Catálogo Atómico de Llaves**

Define las acciones granulares que el sistema puede controlar dentro del dominio funcional del módulo.

Estas llaves no se almacenan como registros tradicionales de `auth.Permission`. Se persisten directamente dentro del `JSONField` asociado al funcionario mediante la entidad `UserAppRole`.

Responsabilidades:

- Declarar privilegios elementales.
- Servir como fuente única de verdad para la autorización.
- Permitir validaciones tanto en backend como en frontend.
- Facilitar la construcción de perfiles reutilizables.

Ejemplos:

- `has_access_module`
- `can_write_records`
- `can_delete_records`

Este bloque constituye la base del modelo de autorización federada de Axentra OS.

---

#### `ROLE_MAPPING`

**Plantillas de Roles Predeterminadas**

Agrupa las llaves definidas en `PERMISSIONS` para construir los perfiles funcionales estándar del Core.

Cuando un administrador asigna un rol desde la Matriz de Permisos, el sistema consulta este diccionario para determinar qué privilegios deben concederse automáticamente.

Responsabilidades:

- Definir perfiles reutilizables.
- Estandarizar criterios de acceso.
- Reducir configuraciones manuales repetitivas.
- Garantizar consistencia entre despliegues.

Perfiles soportados:

- `owner`
- `admin`
- `editor`
- `reviewer`
- `viewer`

Por ejemplo, al asignar el rol `admin`, el sistema concede automáticamente:

- `has_access_module`
- `can_write_records`

sin habilitar privilegios destructivos como `can_delete_records`.

Este bloque representa la capa de abstracción entre permisos atómicos y funciones organizacionales.

---

#### `SIDEBAR_MENU`

**Navegación Dinámica Protegida**

Define la estructura del menú lateral disponible dentro del módulo.

Cada entrada representa una opción navegable compuesta por:

```python
[
    "icono_lucide",
    "Texto",
    "Ruta",
    orden,
    "permiso_requerido",
]
```

Antes de renderizar cada elemento, el motor de navegación valida si el usuario posee la llave indicada.

Si el permiso requerido no existe, el elemento simplemente no será expuesto en la interfaz.

Responsabilidades:

- Construir menús de manera declarativa.
- Ocultar automáticamente opciones no autorizadas.
- Mantener sincronizada la experiencia visual con la política de seguridad.
- Evitar discrepancias entre autorización y navegación.

Este bloque constituye la capa de presentación segura del módulo.

---

#### `CAPABILITIES`

**Semántica de Comportamiento del Organigrama**

Define características operativas que modifican el comportamiento funcional del sistema sin representar permisos de acceso para usuarios específicos.

A diferencia de `PERMISSIONS`, las capacidades describen atributos institucionales asociados a dependencias, direcciones o áreas del organigrama municipal.

Su propósito es alterar reglas de negocio mediante configuraciones declarativas activadas desde la consola administrativa.

Responsabilidades:

- Modelar comportamientos organizacionales.
- Habilitar o restringir flujos especializados.
- Adaptar la lógica del sistema mediante configuración.
- Asociar características funcionales a estructuras administrativas.

Ejemplos de uso:

- Determinar si una dirección puede proveer personal técnico especializado.
- Restringir catálogos visibles durante la generación de reportes.
- Limitar ámbitos operativos de determinadas dependencias.
- Activar comportamientos específicos para procesos institucionales.

Este bloque representa la capa semántica de comportamiento institucional dentro de Axentra OS.

---

> **Nota conceptual**
>
> En Axentra OS, los permisos y las capacidades representan conceptos distintos:
>
> - Los **permisos** responden a la pregunta: **¿Qué puede hacer este usuario?**
> - Las **capacidades** responden a la pregunta: **¿Cómo debe comportarse el sistema respecto a esta unidad organizacional?**
>
> Esta separación permite desacoplar la autorización de usuarios de las reglas operativas del Ayuntamiento.

---

### Ejemplo completo

```python
from apps.shared.apps_config import AppIdentifier


class NuevaAppPermissions:
    APP_CODE = AppIdentifier.NUEVA_APP

    LAUNCHER_CARD = {
        "title": "Gestión de Nueva App",
        "description": "Descripción operativa táctica del módulo municipal.",
        "icon": "package",
        "badge_text": "Operaciones",
        "hover_color": "hover:border-blue-600",
        "text_hover_color": "group-hover:text-blue-600",
        "url_name": "nueva_app:dashboard",
        "is_core": False,
    }

    PERMISSIONS = {
        "has_access_module": (
            "Token elemental requerido para que el módulo "
            "sea visible y accesible."
        ),
        "can_write_records": (
            "Permite la creación y modificación de registros."
        ),
        "can_delete_records": (
            "Permite la eliminación lógica de elementos."
        ),
    }

    ROLE_MAPPING = {
        "owner": [
            "has_access_module",
            "can_write_records",
            "can_delete_records",
        ],
        "admin": [
            "has_access_module",
            "can_write_records",
        ],
        "editor": [
            "has_access_module",
            "can_write_records",
        ],
        "reviewer": [
            "has_access_module",
        ],
        "viewer": [
            "has_access_module",
        ],
    }

    SIDEBAR_MENU = [
        [
            "layout-dashboard",
            "Tablero General",
            "nueva_app:dashboard",
            1,
            "has_access_module",
        ],
        [
            "database",
            "Registros",
            "nueva_app:records_list",
            2,
            "can_write_records",
        ],
    ]

    CAPABILITIES = {
        "flag_alfa": {
            "label": (
                "[Security] Dependencia proveedora de seguridad"
            ),
            "help_text": (
                "Efecto en el sistema: al activar esta capacidad, "
                "el personal adscrito a esta dependencia será "
                "elegible para aparecer en los procesos de "
                "asignación de perfiles técnicos y comisiones "
                "especializadas. Debe utilizarse únicamente en "
                "direcciones responsables de tecnologías, "
                "innovación o soporte de sistemas."
            ),
        },
        "flag_beta": {
            "label": (
                "[Security] Dependencia consumidora estricta "
                "(solo reportes)"
            ),
            "help_text": (
                "Efecto en el sistema: indica que esta área "
                "únicamente puede generar reportes y consultar "
                "sus propios folios. El sistema limitará los "
                "catálogos de selección para que únicamente "
                "puedan interactuar con las sedes y áreas "
                "formalmente asociadas a su dirección."
            ),
        },
    }
}
```

### Paso 3. Proteger las vistas mediante los mixins Core

Para blindar las URLs contra accesos ilegítimos o intentos de manipulación, las vistas deben heredar los mixins en el orden correcto.

**Archivo:** `apps/nueva_app/views.py`

```python
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

from apps.security.services.mixins import (
    ModuleAccessRequiredMixin,
    ModulePermissionsMixin,
)

from apps.shared.apps_config import AppIdentifier


class NuevaAppDashboardView(
    LoginRequiredMixin,
    ModulePermissionsMixin,
    ModuleAccessRequiredMixin,
    TemplateView,
):
    template_name = "nueva_app/dashboard.html"

    required_module = AppIdentifier.NUEVA_APP
    required_fine_permission = "can_write_records"
```

---

## 2. Motor de UI: Home Matrix

Para renderizar la interfaz Home Matrix, el backend consume el contexto `user_module_permissions`, validando qué aplicaciones puede utilizar el usuario a partir de la persistencia de `UserAppRole`.

### Renderizado mediante templatetags unificados

Los desarrolladores deben utilizar exclusivamente los inclusion tags definidos en:

**Archivo:** `apps/shared/templatetags/axentra_ui.py`

```html
{% load axentra_ui %} {% dashboard_header badge_text="MÓDULO" title="Catastro
Municipal" description="Gestión territorial" modulo_actual="security" %}

<div class="grid grid-cols-1 md:grid-cols-3 gap-6">
  {% action_card title="Configurar Parámetros" description="Modificación global"
  url_destination="security:tenant_config" icon="settings" button_text="Abrir
  Configuración" %}
</div>
```

---

## 3. Engine de Filtrado Organizacional

Para garantizar el cumplimiento de las restricciones organizacionales, Axentra OS implementa el `OrganizationalQueryEngine`.

Este mecanismo evita que un funcionario consulte información fuera de su perímetro autorizado.

### Aplicación de filtros organizacionales

Cada consulta relacionada con empleados, expedientes o trámites debe canalizarse mediante este motor.

**Archivo:** `apps/shared/services/query_filters.py`

```python
from apps.shared.services.query_filters import OrganizationalQueryEngine
from apps.shared.dtos.filter_dtos import OrganizationalFilterDTO


def get_records_view(request):
    filtros_dto = OrganizationalFilterDTO(
        sede_id=request.GET.get("sede"),
        dependencia_id=request.GET.get("dependencia"),
        area_id=request.GET.get("area"),
    )

    queryset_base = Expediente.objects.all()

    queryset_filtrado = (
        OrganizationalQueryEngine.filtrar_entidades(
            queryset=queryset_base,
            filtros=filtros_dto,
            profile_path="empleado__axentra_profile",
        )
    )

    return queryset_filtrado
```

### Regla de infraestructura

El motor aplica automáticamente restricciones relacionales en cascada, excluyendo registros asociados a sedes, dependencias o áreas inactivas o archivadas.

---

## 4. Pasarela de Validación Pydantic v2

Axentra OS delega las reglas complejas de integridad de datos a esquemas de Pydantic v2.

Las excepciones nunca deben exponerse directamente al usuario final.

### Integración de errores con Django Forms

**Archivo:** `apps/shared/services/pydantic_validators.py`

```python
from pydantic import ValidationError

from apps.shared.services.pydantic_validators import (
    PydanticErrorBridge,
)


def procesar_formulario_view(request):
    form = MiExpedienteForm(request.POST)

    if form.is_valid():
        try:
            datos_validados = (
                MI_ESQUEMA_PYDANTIC(**form.cleaned_data)
            )

        except ValidationError as ex:
            PydanticErrorBridge.acoplar_errores_a_formulario(
                ex,
                form,
            )

            return render(
                request,
                "template.html",
                {"form": form},
            )
```

---

## 5. Servicio de Auditoría Forense

Toda acción crítica relacionada con ciberseguridad o modificaciones estructurales debe registrarse mediante `SecurityAuditService`.

### Protocolo fail-safe

Si el registro en PostgreSQL falla, el evento es redirigido automáticamente al sistema de archivos local para evitar la interrupción del flujo transaccional.

**Archivo:** `apps/security/services/audit_service.py`

```python
from apps.security.services.audit_service import (
    SecurityAuditService,
)

from apps.security.models.security_models import (
    SecurityAuditLog,
)


SecurityAuditService.registrar_evento(
    usuario=request.user,
    nivel=SecurityAuditLog.Levels.SUCCESS,
    accion=(
        "Mutación de Identidad Global: "
        "Se modificaron las siglas legales "
        "del Ayuntamiento"
    ),
    destino=(
        f"App: Security | "
        f"TenantConfig ID: {config.id}"
    ),
)
```

---

## 6. Pipeline de Context Processors

El archivo `apps/shared/context_processors.py` proporciona variables globales disponibles durante toda la sesión del usuario.

### Variables disponibles

| Variable                | Descripción                                                                 |
| ----------------------- | --------------------------------------------------------------------------- |
| `tenant.app_name`       | Nombre del aplicativo central.                                              |
| `tenant.entidad_nombre` | Nombre de la entidad o Ayuntamiento activo.                                 |
| `tenant.siglas`         | Siglas oficiales de la administración vigente.                              |
| `allowed_modules`       | Lista de módulos permitidos para el usuario autenticado.                    |
| `menu_actual`           | Menú dinámico generado a partir del `SIDEBAR_MENU` y filtrado por permisos. |

---

## Principios de Arquitectura

- Gobernanza centralizada con despliegues federados.
- Control de acceso basado en privilegios atómicos.
- Separación entre autorización, visualización y persistencia.
- Auditoría forense resiliente.
- Restricciones organizacionales aplicadas transversalmente.
- Validación estricta mediante Pydantic v2.
- Componentes reutilizables y desacoplados.

---

## Licencia

AXENTRA MÉXICO © 2026

Infraestructura soberana y tecnologías de ciberseguridad centralizada.
