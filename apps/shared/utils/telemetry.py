import logging

from django.conf import settings
from django.utils import timezone


logger = logging.getLogger("axentra.telemetry")


class AxentraRadar:
    """Telemetría diagnóstica condicionada y centralizada de Axentra OS."""

    SENSITIVE_MARKERS = (
        "password",
        "contraseña",
        "secret",
        "token",
        "cookie",
        "authorization",
        "credential",
        "api_key",
    )

    @staticmethod
    def enabled() -> bool:
        return bool(
            getattr(settings, "AXENTRA_CORE_VERBOSE_RADAR", False)
        )

    @classmethod
    def _safe_value(cls, key, value):
        normalized = str(key).strip().lower()
        if any(marker in normalized for marker in cls.SENSITIVE_MARKERS):
            return "[REDACTED]"
        return value

    @classmethod
    def emitir_evento(
        cls,
        *,
        componente: str,
        titulo: str,
        extra_data: dict | None = None,
        request=None,
        actor_email: str = "",
        es_error: bool = False,
        icono: str = "🛰️",
    ):
        """
        Emite un único registro mediante logging cuando el radar está activo.

        No usa salida directa, no persiste secretos y no evalúa información costosa
        cuando AXENTRA_CORE_VERBOSE_RADAR está apagado.
        """
        if not cls.enabled():
            return

        user = getattr(request, "user", None) if request else None
        authenticated = bool(
            user and getattr(user, "is_authenticated", False)
        )
        email = (
            getattr(user, "email", "")
            if authenticated
            else actor_email or "ANONYMOUS_USER"
        )
        path = getattr(request, "path", "N/A") if request else "N/A"
        timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        border = ("🎚" if es_error else "═") * 76
        lines = [
            f"{icono}  {border}",
            f"📡  [{componente.upper()}] -> {titulo.upper()}",
            f"⏰ Telemetría:      {timestamp}",
            f"👤 Operador Activo: {email}",
            f"📍 URL Impactada:   {path}",
        ]
        if extra_data:
            lines.append("-" * 80)
            lines.extend(
                f"   🔹 {key}: {cls._safe_value(key, value)}"
                for key, value in extra_data.items()
            )
        lines.append(border)

        level = logging.ERROR if es_error else logging.INFO
        logger.log(level, "\n%s", "\n".join(lines))

    @classmethod
    def imprimir_auditoria(
        cls,
        componente: str,
        request,
        titulo: str,
        extra_data: dict | None = None,
        es_error: bool = False,
        icono: str = "🛰️",
    ):
        """Alias compatible para llamadas existentes."""
        cls.emitir_evento(
            componente=componente,
            titulo=titulo,
            extra_data=extra_data,
            request=request,
            es_error=es_error,
            icono=icono,
        )


__all__ = ["AxentraRadar"]
