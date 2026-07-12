# apps/shared/apps_config.py

class AppIdentifier:
    """
    🛰️ CORE OS APPS REGISTRY - AXENTRA OS
    Catálogo maestro unificado de Slugs e identificadores de aplicaciones del ecosistema.
    Gobierna de forma centralizada la siembra en BD, el filtrado perimetral del decorador,
    el descubrimiento de manifiestos y el dibujado de tarjetas en el Launcher.
    """
    SECURITY = "security"
    ACCOUNTS = "accounts"
    ORGANIGRAMA = "organigrama"
    INVENTORY = "inventory"

    @classmethod
    def get_choices(cls) -> list:
        """
        📋 CATÁLOGO MAESTRO DE PRODUCCIÓN:
        Retorna el inventario legal de los módulos lógicos activos y autorizados
        para operar dentro del chasis del sistema operativo corporativo.
        """
        return [
            (cls.SECURITY, "Ciberseguridad Central"),
            (cls.ACCOUNTS, "Plantilla de Personal"),
            (cls.ORGANIGRAMA, "Estructura Orgánica"),
            (cls.INVENTORY, "Inventario Patrimonial"),
        ]