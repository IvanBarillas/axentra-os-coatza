from core.settings.production import *  # noqa: F403

from .composition import compose_installed_apps

INSTALLED_APPS = compose_installed_apps(INSTALLED_APPS)  # noqa: F405
ROOT_URLCONF = "coatza.urls"
