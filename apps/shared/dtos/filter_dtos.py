# apps/shared/dtos/filter_dtos.py
import uuid
from pydantic import BaseModel, Field, model_validator
from typing import Optional, Union, Any

class OrganizationalFilterDTO(BaseModel):
    """
    🎛️ GLOBAL VALUE OBJECT (AXENTRA OS STANDARD):
    Aduana perimetral que normaliza, limpia y sanea los parámetros estructurales 
    comunes de cualquier HTTP GET (Buscadores, Combos, Rejillas de Filtros HTMX).
    Garantiza que el motor del QueryEngine reciba únicamente UUIDs limpios o None.
    """
    q: Optional[str] = Field(default="", description="Búsqueda libre por texto plano")
    sede_id: Optional[uuid.UUID] = Field(default=None)
    dependencia_id: Optional[uuid.UUID] = Field(default=None)
    area_id: Optional[uuid.UUID] = Field(default=None)
    
    @model_validator(mode='before')
    @classmethod
    def limpiar_valores_vacios_o_comodines(cls, data: Any) -> Any:
        """
        🛡️ LIMPIADOR ATÓMICO INTERCEPTOR:
        Intercepta los inputs crudos del HTTP Request (incluyendo QueryDicts inmutables de Django)
        y purga cadenas vacías, nulos en string o comodines del frontend como 'all' o 'undefined'.
        """
        # 🪐 CAPA DE CONVERSIÓN: Si es un QueryDict de Django o un objeto inmutable, lo clonamos a dict puro
        if hasattr(data, 'dict') and callable(getattr(data, 'dict')):
            # Si el QueryDict tiene múltiples valores, .dict() de Django extrae el último elemento de forma limpia
            data = data.dict()
        elif hasattr(data, 'copy') and callable(getattr(data, 'copy')):
            data = data.copy()
        elif not isinstance(data, dict):
            data = getattr(data, '__dict__', data) if hasattr(data, '__dict__') else {}

        # Mapeo de campos relacionales que PostgreSQL espera recibir estrictamente como UUIDs
        campos_relacionales = ['sede_id', 'dependencia_id', 'area_id']
        
        for campo in campos_relacionales:
            val = data.get(campo)
            
            # Captura comodines de frameworks de JS, strings vacíos de HTMX o flags de resets globales
            if val in [None, "", "all", "None", "undefined", "null", "ALL", "all_sedes", "all_deps"]:
                data[campo] = None
            elif isinstance(val, uuid.UUID):
                # Si ya es un objeto UUID (por instanciación directa en el backend), se respeta
                continue
            elif isinstance(val, str) and val.strip() != "":
                try:
                    # Coerción explícita a tipo UUID de Python de 128 bits
                    data[campo] = uuid.UUID(val.strip())
                except ValueError:
                    # Si envían texto basura o malicioso, lo mitigamos forzándolo a None
                    data[campo] = None
            else:
                data[campo] = None
                
        # Saneamiento del buscador de texto libre
        if data.get('q'):
            data['q'] = str(data['q']).strip()
        else:
            data['q'] = ""
            
        return data