# apps/shared/apps_config.py

class AppIdentifier:
    """Catálogo maestro unificado de Slugs de aplicaciones activas en Axentra OS."""
    SECURITY = "security"


    @classmethod
    def get_choices(cls):
        """Retorna el catálogo real de los módulos instalados en producción."""
        return [
            (cls.SECURITY, "CIBERSEGURIDAD CENTRAL"),
        ]