# apps/security/apps.py
from django.apps import AppConfig

class SecurityConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.security'
    verbose_name = 'Ciberseguridad e Identidad Central'

    def ready(self):
        """
        Espacio reservado para inicializaciones en caliente al levantar el servidor.
        Aquí se conectarán señales (signals) si en el futuro necesitas gatillar acciones
        automáticas en la creación de usuarios o logs forenses.
        """
        pass