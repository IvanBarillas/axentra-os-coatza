# apps/shared/utils/telemetry.py
import logging
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger('axentra.telemetry')

class AxentraRadar:
    @staticmethod
    def imprimir_auditoria(componente: str, request, titulo: str, extra_data: dict = None, es_error: bool = False, icono: str = "🛰️"):
        """
        Impresor Universal de Telemetría Perimetral.
        Si settings.AXENTRA_CORE_VERBOSE_RADAR es False, no consume recursos.
        """
        # 🛑 Compuerta de escape si el interruptor está apagado
        if not getattr(settings, 'AXENTRA_CORE_VERBOSE_RADAR', False):
            return

        ahora = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        email_usuario = request.user.email if request and request.user.is_authenticated else "ANONYMOUS_USER"
        url_impactada = request.path if request else "N/A"
        
        # Elegir el separador visual
        char_separador = "═" if not es_error else "🎚"
        borde = f"{char_separador}" * 76
        
        print(f"\n{icono}  {borde}")
        print(f"📡  [{componente.upper()}] -> {titulo.upper()}")
        print(f"⏰ Telemetría:      {ahora}")
        print(f"👤 Operador Activo:  {email_usuario}")
        print(f"📍 URL Impactada:    {url_impactada}")
        
        if extra_data:
            print("-" * 80)
            for llave, valor in extra_data.items():
                print(f"   🔹 {llave}: {valor}")
                
        print(f"{borde}\n")