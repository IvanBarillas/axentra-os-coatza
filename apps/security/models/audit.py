# apps/security/models/audit.py
import uuid
from django.db import models
from django.conf import settings

class SecurityAuditLog(models.Model):
    """Caja Negra Forense Global de Axentra OS con Indexación Quirúrgica."""
    class Levels(models.TextChoices):
        CRITICAL = "CRITICAL", "🚨 Operación Crítica / Traslape / Bloqueo"
        SUCCESS = "SUCCESS", "🟢 Operación Exitosa / Acceso Concedido"
        INFO = "INFO", "🔵 Modificación Informativa / Rutina"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # 🔍 COLUMNAS FILTRABLES INDEXADAS (CAMPOS INDEPENDIENTES)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True) # ◄── Indexado para búsquedas por fechas veloces
    
    app_namespace = models.CharField(
        "Módulo / App de Origen", 
        max_length=50,
        default="core", 
        db_index=True # ◄── Indexado para filtrar de golpe por: 'security', 'inventario', 'catastro'
    )
    
    operator_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='logs',
        verbose_name="Operador del Sistema",
        db_index=True
    )
    
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='auditorias_recibidas',
        verbose_name="Funcionario Afectado",
        db_index=True
    )
    
    level_status = models.CharField(
        "Nivel del Evento",
        max_length=15,
        choices=Levels.choices,
        default=Levels.INFO,
        db_index=True
    )
    
    action_name = models.CharField("Acción Ejecutada", max_length=150, db_index=True)
    
    # 🟢 TU PROPUESTA CRITERIO DINÁMICO: Guarda aquí el Num_Serie, la Clave_Catastral, el Folio_Ticket, etc.
    search_target = models.CharField(
        "Criterio / Llave de Búsqueda Dinámica", 
        max_length=255, 
        null=True, 
        blank=True, 
        db_index=True # ◄── Indexado: Buscará claves catastrales o series a velocidad luz
    )

    target_scope = models.CharField("Ámbito / Descripción del Destino", max_length=255)
    
    # 🌐 TELEMETRÍA DE RED EN COLUMNAS INDEPENDIENTES
    ip_address = models.GenericIPAddressField("Dirección IP", default="127.0.0.1", null=True, blank=True, db_index=True)
    user_agent = models.TextField("Navegador / Dispositivo", null=True, blank=True)
    
    # 📥 TELEMETRÍA SECUNDARIA VARIABLE (NO FILTRABLE DE GOLPE)
    payload_json = models.JSONField("Telemetría Estructurada JSON", default=dict, blank=True)
    
    class Meta:
        db_table = 'axentra_sec_audit_logs'
        verbose_name = "Log de Auditoría"
        verbose_name_plural = "Logs de Auditoría"
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.app_namespace.upper()}] - [{self.level_status}] {self.operator_user.email} - {self.action_name}"