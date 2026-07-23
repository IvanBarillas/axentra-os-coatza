from django.urls import include, path

from .registry import module_registry


def satellite_urlpatterns():
    """Monta sólo los urlconf publicados por módulos realmente instalados."""
    patterns = []
    for manifest in module_registry.discover():
        if not manifest.urlconf or not manifest.url_prefix:
            continue
        patterns.append(path(manifest.url_prefix, include(manifest.urlconf)))
    return patterns


__all__ = ["satellite_urlpatterns"]
