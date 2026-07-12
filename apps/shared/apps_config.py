# apps/shared/apps_config.py

class AppIdentifier:
    """
    CORE OS APPS REGISTRY - AXENTRA OS

    Catálogo maestro unificado de slugs e identificadores de aplicaciones
    del ecosistema Axentra OS.
    """

    SECURITY = "security"
    CONFIGURATION = "configuration"
    ACCOUNTS = "accounts"
    ORGANIGRAMA = "organigrama"

    @classmethod
    def get_choices(cls) -> list:
        """
        Catálogo maestro de módulos lógicos activos y autorizados.
        """
        return [
            (cls.SECURITY, "Ciberseguridad Central"),
            (cls.CONFIGURATION, "Configuración Institucional"),
            (cls.ACCOUNTS, "Plantilla de Personal"),
            (cls.ORGANIGRAMA, "Estructura Orgánica"),
        ]