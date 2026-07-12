# apps/security/dtos/organigrama_dtos.py
import uuid
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, Dict, Any, List

# =========================================================================
# 🏢 DOMINIO: SEDES (INMUEBLES FÍSICOS)
# =========================================================================
class SedeReadOnlyDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    nombre: str
    direccion: Optional[str] = ""
    encargado_sede_id: Optional[uuid.UUID] = None
    encargado_sede_name: str = "Sin Líder Asignado"
    is_active: bool

class SedeInputDTO(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True) # 🟢 Permite objetos nativos de Django
    nombre: str = Field(..., min_length=3, max_length=150)
    direccion: Optional[str] = Field("", max_length=255)
    # 🟢 Polimorfismo de entrada para tolerar UUIDs o instancias de User de Django Forms
    encargado_sede_id: Optional[Any] = Field(None)
    is_active: Optional[bool] = Field(True)

# =========================================================================
# 🏛️ DOMINIO: DEPENDENCIAS (DIRECCIONES CORE)
# =========================================================================
class DependenciaReadOnlyDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    nombre: str
    slug: str
    encargado_departamento_id: Optional[uuid.UUID] = None
    encargado_departamento_name: str = "Titular No Asignado"
    is_active: bool
    is_deleted: bool
    sedes_asignadas_nombres: List[str] = Field(default_factory=list)

class DependenciaInputDTO(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    nombre: str = Field(
        ...,
        min_length=3,
        max_length=150,
    )

    codigo_presupuestal: Optional[str] = Field(
        default="",
        max_length=3,
        description="Código presupuestal de 3 dígitos usado para folios patrimoniales. Ejemplo: 012.",
    )

    parent_id: Optional[Any] = Field(
        None,
        description="Dependencia padre opcional para jerarquía administrativa.",
    )

    encargado_departamento_id: Optional[Any] = Field(
        None,
        description="Servidor público titular opcional.",
    )

    @field_validator("nombre")
    @classmethod
    def validar_nombre(cls, value: str) -> str:
        value = value.strip()

        if len(value) < 3:
            raise ValueError("El nombre de la dependencia debe tener al menos 3 caracteres.")

        return value

    @field_validator("codigo_presupuestal")
    @classmethod
    def validar_codigo_presupuestal(cls, value: Optional[str]) -> str:
        value = (value or "").strip()

        if not value:
            return ""

        if not value.isdigit():
            raise ValueError("El código presupuestal debe contener sólo números.")

        if len(value) > 3:
            raise ValueError("El código presupuestal no puede tener más de 3 dígitos.")

        return value.zfill(3)
    

# =========================================================================
# 🎛️ DOMINIO: AREAS OPERATIVAS (LA MATRIZ TRIPLE)
# =========================================================================
class AreaOperativaReadOnlyDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    nombre: str
    slug: str
    dependencia_id: uuid.UUID
    dependencia_nombre: str
    sede_fisica_id: uuid.UUID
    sede_fisica_nombre: str
    is_active: bool
    is_deleted: bool

class AreaOperativaInputDTO(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True) # 🟢 Permite objetos nativos de Django
    dependencia_id: Optional[Any] = Field(...) # 🟢 Polimorfismo de entrada para Formularios
    sede_fisica_id: Optional[Any] = Field(...)  # 🟢 Polimorfismo de entrada para Formularios
    nombre: str = Field(..., min_length=2, max_length=150)

# =========================================================================
# 🛰️ DOMINIO: FEDERACIÓN DE CAPACIDADES
# =========================================================================
class CapabilityReadOnlyDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    app_id: int
    app_name: str
    app_slug: str
    dependencia_id: uuid.UUID
    dependencia_nombre: str
    flag_alfa: bool
    flag_beta: bool
    custom_settings: Dict[str, Any] = Field(default_factory=dict)

class CapabilityInputDTO(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    app_id: int
    dependencia_id: Optional[Any] = Field(...)
    flag_alfa: bool = False
    flag_beta: bool = False
    custom_settings: Dict[str, Any] = Field(default_factory=dict)