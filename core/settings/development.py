# core/settings/development.py
from .base import *
import dj_database_url

# 🛡️ SEGURIDAD EXCLUSIVA DE DESARROLLO
DEBUG = True
SECRET_KEY = config('SECRET_KEY', default='django-insecure-local-wsl-key')
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1,*').split(',')

# 🛡️ BASE DE DATOS LOCAL O EN DOCKER DEV (Postgres)
DATABASE_URL_STR = config('DATABASE_URL', default='')
if not DATABASE_URL_STR:
    DATABASE_URL_STR = f"sqlite:////{BASE_DIR / 'db.sqlite3'}"

DATABASES = {
    'default': dj_database_url.parse(DATABASE_URL_STR)
}
DATABASES['default']['ATOMIC_REQUESTS'] = True

# 🛡️ CORREO LOCAL (Archivos)
EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
EMAIL_FILE_PATH = BASE_DIR / 'sent_emails'

#CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='http://localhost:8000').split(',')

# 🛡️ LOGS DE DESARROLLO (Salida directa y rápida a consola)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG', # Nivel detallado para encontrar bugs rápido en WSL
    },
}

# =========================================================================
# INTERRUPTOR LOCAL: Siempre encendido para inspección visual en WSL/Consola
# =========================================================================
AXENTRA_CORE_VERBOSE_RADAR = config(
    "AXENTRA_CORE_VERBOSE_RADAR",
    default=True,
    cast=bool,
)
