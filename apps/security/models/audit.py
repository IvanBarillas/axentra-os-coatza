# apps/security/models/audit.py
import uuid
from django.db import models
from django.conf import settings

class SecurityAuditLog(models.Model):
    """Buffer circular de auditoría forense (Heimdall Logs)."""
    class Levels(models.TextChoices):
        CRITICAL = "CRITICAL", "🚨 Operación Crítica / Traslape / Bloqueo"
        SUCCESS = "SUCCESS", "🟢 Operación Exitosa / Acceso Concedido"
        INFO = "INFO", "🔵 Modificación Informativa / Rutina"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    operator_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='security_logs',
        verbose_name="Operador del Sistema"
    )
    level_status = models.CharField(
        "Nivel del Evento",
        max_length=15,
        choices=Levels.choices,
        default=Levels.INFO
    )
    action_name = models.CharField("Acción Ejecutada", max_length=150)
    target_scope = models.CharField("Ámbito / Destino", max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'axentra_sec_audit_logs'
        verbose_name = "Log de Auditoría"
        verbose_name_plural = "Logs de Auditoría"
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.level_status}] {self.operator_user.email} - {self.action_name}"