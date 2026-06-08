# apps/security/dtos/security_dtos.py
import uuid
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Optional

class RoleReadOnlyDTO(BaseModel):
    """
    CONTRATO INMUTABLE DE LECTURA (GET):
    Mapea de forma segura los permisos activos por usuario para consumo del decorador y la UX.
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    user_email: str
    app_id: int
    app_name: str
    app_slug: str
    role: str
    role_display: str
    is_active: bool
    permissions_list: Optional[List[str]] = Field(default_factory=list)

    @field_validator('permissions_list', mode='before')
    @classmethod
    def asegurar_lista_valida(cls, value):
        return value if value is not None else []


class RoleInputDTO(BaseModel):
    """CONTRATO DE VALIDACIÓN (POST - MUTACIÓN): Altas y Overrides de privilegios."""
    user_id: uuid.UUID
    app_id: int
    role: str = Field(..., max_length=20)
    permissions_list: List[str] = Field(default_factory=list)


class TenantConfigReadOnlyDTO(BaseModel):
    """CONTRATO GLOBAL INYECTABLE: Mapea los activos de marca del Ayuntamiento."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    app_name: str
    entidad_nombre: str
    siglas: str
    direccion_oficial: Optional[str] = ""
    rfc: Optional[str] = ""
    primary_color_class: str
    logo_light: Optional[str] = None
    logo_dark: Optional[str] = None

    @field_validator('logo_light', 'logo_dark', mode='before')
    @classmethod
    def extraer_url_de_imagen_django(cls, value):
        if value and hasattr(value, 'url'):
            try:
                return value.url
            except ValueError:
                return None
        return None