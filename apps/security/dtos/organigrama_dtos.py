# apps/security/dtos/organigrama_dtos.py
import uuid
from pydantic import BaseModel, Field, ConfigDict
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
    nombre: str = Field(..., min_length=3, max_length=150)
    direccion: Optional[str] = Field("", max_length=255)
    encargado_sede_id: Optional[uuid.UUID] = Field(None)

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
    nombre: str = Field(..., min_length=3, max_length=150)
    encargado_departamento_id: Optional[uuid.UUID] = Field(None)

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
    dependencia_id: uuid.UUID
    sede_fisica_id: uuid.UUID
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
    app_id: int
    dependencia_id: uuid.UUID
    flag_alfa: bool = False
    flag_beta: bool = False
    custom_settings: Dict[str, Any] = Field(default_factory=dict)