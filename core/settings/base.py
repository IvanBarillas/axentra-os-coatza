
# core/settings/base.py
from pathlib import Path
from decouple import Config, RepositoryEnv
import os  

# =========================================================
# CARGA DE ENTORNO EN RAÍZ
# =========================================================  
BASE_DIR = Path(__file__).resolve().parent.parent.parent  

ENV = os.getenv("DJANGO_ENV", "dev")
ENV_FILE = BASE_DIR / f".env.{ENV}"
config = Config(RepositoryEnv(ENV_FILE))

# =========================================================
# APPLICATIONS (Estructura fija)
# =========================================================
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'axes',

]

LOCAL_APPS = [
    'apps.shared.apps.SharedConfig',
    'apps.security.apps.SecurityConfig',
    'apps.inventory.apps.InventoryConfig',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# =========================================================
# MIDDLEWARE (Estructura fija)
# =========================================================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'axes.middleware.AxesMiddleware',
]

ROOT_URLCONF = 'core.urls'
WSGI_APPLICATION = 'core.wsgi.application'

# =========================================================
# TEMPLATES (Estructura fija)
# =========================================================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                
                # 🪐 LOS INYECTORES DE GOBERNANZA GLOBAL DE AXENTRA OS
                'apps.shared.context_processors.global_tenant_settings',    # Activos de marca e identidad ({{ tenant }})
                'apps.shared.context_processors.user_module_permissions',  # Lista de apps asignadas ({{ allowed_modules }})
                "apps.shared.context_processors.satellite_navigation",
                'apps.shared.context_processors.menu_dinamico_processor',
            ],
        },
    },
]

# =========================================================
# CONFIGURACIONES INTERNAS FIJAS
# =========================================================
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
]

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
]

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# =========================================================================
# 🛡️ CONFIGURACIÓN DE AUTENTICACIÓN Y REDIRECCIÓN CORE
# =========================================================================
# Destino definitivo tras un login exitoso (Apunta a tu path('launcher/', ...))
LOGIN_REDIRECT_URL = 'index_hub'

# Destino en caso de que un usuario intente entrar a una ruta protegida sin sesión
LOGIN_URL = 'login'

# Destino tras cerrar sesión en el sistema
LOGOUT_REDIRECT_URL = '/'

AUTH_USER_MODEL = 'security.User'

AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1
AXES_RESET_ON_SUCCESS = True
AXES_LOCK_OUT_BY_COMBINATION = True

LANGUAGE_CODE = 'es-mx'
TIME_ZONE = 'America/Mexico_City'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'same-origin'

# =========================================================================
# CONFIGURACIÓN SOBERANA DE TELEMETRÍA (AXENTRA RADAR INTERRUPTOR)
# =========================================================================
# Lee del archivo .env correspondiente; si no existe, por defecto se apaga.
AXENTRA_CORE_VERBOSE_RADAR = config('AXENTRA_CORE_VERBOSE_RADAR', default=False, cast=bool)

# =========================================================
# APROVISIONAMIENTO DEL OPERADOR INICIAL
# =========================================================

AXENTRA_OWNER_EMAIL = config(
    "AXENTRA_OWNER_EMAIL",
    default="owner@axentra.com.mx",
)

AXENTRA_OWNER_DEFAULT_PASSWORD = config(
    "AXENTRA_OWNER_DEFAULT_PASSWORD",
    default="",
)