# AXENTRA OS — CORE PLATFORM MANIFESTO

## Sistema Operativo Municipal Federado y Core de Ciberseguridad Aislada

Este repositorio concentra el Core de Infraestructura y Gobernanza Central de Axentra OS. Está diseñado bajo una arquitectura matricial de software federado, actuando como el motor maestro para despliegues en Ayuntamientos y Administraciones Públicas Municipales.

---

# 1. Manifiesto del Sistema de Permisos y Roles

Axentra OS no utiliza el sistema tradicional de permisos de Django (`auth.Permission`). El acceso perimetral opera mediante un catálogo atómico federado mantenido en memoria y persistido mediante un `JSONField` dentro de PostgreSQL (`UserAppRole`).

## Protocolo para crear y federar una nueva aplicación satélite

Cuando un desarrollador crea un nuevo módulo (por ejemplo, patrimonio o catastro), debe seguir estrictamente el siguiente flujo de tres pasos.

---

## Paso 1. Registrar el identificador Core

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

---

## Paso 2. Declarar el manifiesto de privilegios local

Dentro de la nueva aplicación debe existir obligatoriamente un archivo `permissions.py`.

Su propósito es centralizar de manera declarativa la identidad del módulo, los privilegios atómicos, los perfiles predeterminados, la navegación protegida y las capacidades organizacionales.

**Archivo:** `apps/nueva_app/permissions.py`

---

## Desglose técnico de los componentes

### `LAUNCHER_CARD`

#### Identidad en el Lanzador General

Configura los metadatos necesarios para que el chasis de Axentra OS renderice la tarjeta de acceso rápido dentro del Home principal.

Representa la capa de descubrimiento inicial.

**Responsabilidades:**

- Definir título.
- Definir descripción.
- Configurar iconografía.
- Definir estilos visuales.
- Especificar la ruta de aterrizaje (`url_name`).
- Determinar si corresponde a un módulo Core o Satélite.

---

### `PERMISSIONS`

#### Catálogo Atómico de Llaves

Define las acciones granulares que el sistema puede controlar dentro del dominio funcional del módulo.

Se persisten directamente dentro de la matriz `JSONField` asociada al funcionario.

**Responsabilidades:**

- Declarar privilegios elementales.
- Servir como fuente única de verdad para la autorización.
- Permitir validaciones eficientes en backend y frontend.

**Ejemplos:**

- `has_access_module`
- `can_write_records`
- `can_delete_records`

---

### `ROLE_MAPPING`

#### Plantillas de Roles Predeterminadas

Agrupa las llaves de `PERMISSIONS` para construir los perfiles funcionales estándar del Core.

Perfiles soportados:

- `owner`
- `admin`
- `editor`
- `reviewer`
- `viewer`

Reduce configuraciones manuales repetitivas y garantiza consistencia entre despliegues.

---

## Directiva Inmutable Zero-Zero Trust SOBERANA

En Axentra OS, el rol `owner` es el único perfil que clona e inyecta automáticamente la piscina completa de permisos desde el primer segundo.

Al cambiar el rol a `admin` o cualquier escala jerárquica inferior:

- El sistema vacía todas las llaves por diseño defensivo.
- Preserva únicamente el token mínimo vitalicio obligatorio:

```text
has_access_module
```

- El operador del sistema deberá habilitar manualmente cada casilla desde la grilla visual.

---

### `SIDEBAR_MENU`

#### Navegación Dinámica Protegida

Define la estructura del menú lateral disponible dentro del módulo.

Cada entrada representa una opción navegable compuesta por un arreglo plano con la siguiente estructura:

```python
["icono_lucide", "Texto", "Ruta", orden, "permiso_requerido"]
```

Antes de renderizar cada elemento, el motor de navegación valida si el usuario posee la llave indicada.

Si el permiso no existe, la opción es omitida del DOM de forma segura.

---

### `CAPABILITIES`

#### Semántica de Comportamiento del Organigrama

Describe atributos institucionales asociados a dependencias, direcciones o áreas del organigrama municipal para alterar reglas de negocio mediante configuraciones declarativas avanzadas.

### Diferencia conceptual clave

**Permisos:**

Responden a la pregunta:

> ¿Qué puede hacer este usuario?

**Capacidades:**

Responden a la pregunta:

> ¿Cómo debe comportarse el sistema respecto a esta unidad organizacional?

---

## Ejemplo completo de manifiesto local (`permissions.py`)

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
                "[Security] Dependencia de TI / Innovación "
                "proveedora de soporte especializado"
            ),
            "help_text": (
                "Habilita al personal adscrito para "
                "asignación de comisiones técnicas."
            ),
        },
        "flag_beta": {
            "label": (
                "[Security] Dependencia consumidora "
                "estricta (Solo reportes)"
            ),
            "help_text": (
                "Limita los catálogos para que el área "
                "solo consulte sus propios folios."
            ),
        },
    }
```

---

## Paso 3. Proteger las vistas mediante los mixins Core

Para blindar las URLs contra accesos ilegítimos o intentos de manipulación perimetral, las vistas basadas en clases (CBV) deben heredar los mixins de control respetando el orden estricto de resolución de herencia de Python (MRO).

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

# 2. Motor de UI: Home Matrix

Para renderizar la interfaz Home Matrix, el backend consume el contexto `user_module_permissions`, validando qué aplicaciones puede utilizar el usuario a partir de la persistencia de `UserAppRole`.

El despliegue de componentes en plantillas se realiza exclusivamente mediante los inclusion tags autorizados.

**Archivo:** `apps/shared/templatetags/axentra_ui.py`

```django
{% load axentra_ui %}

{% dashboard_header
    badge_text="MÓDULO"
    title="Catastro Municipal"
    description="Gestión territorial"
    modulo_actual="security"
%}

<div class="grid grid-cols-1 md:grid-cols-3 gap-6">
    {% action_card
        title="Configurar Parámetros"
        description="Modificación global"
        url_destination="security:tenant_config"
        icon="settings"
        button_text="Abrir Configuración"
    %}
</div>
```

---

# 3. Engine de Filtrado Organizacional

Para garantizar el cumplimiento de las restricciones perimetrales, Axentra OS implementa el `OrganizationalQueryEngine`.

Este mecanismo evita que un funcionario consulte información fuera de su adscripción autorizada, aplicando automáticamente restricciones relacionales en cascada sobre entidades archivadas o inactivas.

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

---

# 4. Pasarela de Validación Pydantic v2

Axentra OS delega las reglas complejas de integridad y contratos de datos a esquemas estrictos de Pydantic v2.

Las excepciones brutas nunca deben exponerse directamente al cliente.

Los errores de validación se interceptan y se acoplan de forma transparente al ciclo de renderizado de formularios tradicionales.

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
            datos_validados = MI_ESQUEMA_PYDANTIC(
                **form.cleaned_data
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

# 5. Servicio de Auditoría Forense

Toda mutación de datos, conmutación de estados o alteración estructural en Axentra OS es capturada por el motor transaccional `ForensicAuditor`.

Opera de forma asíncrona y desacoplada de la capa visual, implementando un diseño de catálogo normalizado bajo PostgreSQL.

## Columnas indexadas clave

### `action_type` (El Verbo Global)

- `CREATE`
- `UPDATE`
- `DELETE`
- `ASSIGN`
- `ACCESS`
- `RESET`
- `QUERY`

### `module_component` (El Sujeto)

Ejemplos:

- `MATRIZ_PERMISOS`
- `FICHA_PERSONAL`
- `SEDES_INFRAESTRUCTURA`

Los desarrolladores deben invocar el auditor desde la capa de servicios transaccionales.

---

```python
from apps.security.models.audit import SecurityAuditLog
from apps.security.utils.forensic_auditor import ForensicAuditor


ForensicAuditor.registrar_evento(
    request=request,
    action_type=SecurityAuditLog.ActionTypes.UPDATE,
    module_component="FICHA_PERSONAL",
    action_name="EDICION_FICHA_IDENTIDAD",
    target_scope=(
        f"Actualización del expediente "
        f"de {usuario.email}"
    ),
    level=SecurityAuditLog.Levels.INFO,
    target_user=usuario,
    search_target=usuario.id,
    payload=payload_delta,
)
```

---

## Cabina de Mando Analítica y Reportes de Evidencia

La plataforma provee una consola analítica avanzada con filtros en caliente y un motor de cumplimiento de Compliance Forense capaz de exportar conjuntos de datos hacia hojas de cálculo inmutables (`.xlsx`), incrustando el JSON crudo de auditoría para revisiones de los órganos internos de control.

---

# 6. Pipeline de Context Processors

El archivo `apps/shared/context_processors.py` proporciona variables globales residentes en memoria optimizadas para consumo directo desde el motor de plantillas.

| Variable                | Descripción                                                    |
| ----------------------- | -------------------------------------------------------------- |
| `tenant.app_name`       | Nombre del aplicativo central.                                 |
| `tenant.entidad_nombre` | Nombre de la entidad o administración activa.                  |
| `tenant.siglas`         | Siglas oficiales de la administración vigente.                 |
| `allowed_modules`       | Lista de módulos autorizados para el usuario autenticado.      |
| `menu_actual`           | Menú dinámico generado a partir de la memoria RAM del request. |

---

# Principios de Arquitectura

- Gobernanza centralizada con despliegues federados.
- Control de acceso basado en privilegios atómicos sin redundancia de roles relacionales.
- Separación estricta entre autorización, visualización y persistencia transaccional.
- Auditoría forense resiliente basada en firmas e índices.
- Restricciones organizacionales aplicadas transversalmente en la capa de base de datos.
- Validación estricta mediante esquemas inmutables de Pydantic v2.

---

# Licencia

**AXENTRA MÉXICO © 2026**

Infraestructura soberana y tecnologías de ciberseguridad centralizada.
