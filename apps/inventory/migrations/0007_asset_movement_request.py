import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("inventory", "0006_remove_asset_authorized_asset_type_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="AssetMovementRequest",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("is_active", models.BooleanField(db_index=True, default=True, verbose_name="Activo")),
                ("is_deleted", models.BooleanField(db_index=True, default=False, verbose_name="Eliminado")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Creado")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Actualizado")),
                ("deleted_at", models.DateTimeField(blank=True, null=True, verbose_name="Fecha de baja lógica")),
                ("folio", models.CharField(max_length=80, unique=True, verbose_name="Folio de solicitud")),
                ("movement_type", models.CharField(choices=[("REGISTRATION","Alta patrimonial"),("ASSIGNMENT","Asignación"),("REASSIGNMENT","Reasignación"),("TRANSFER","Transferencia definitiva"),("LOAN","Préstamo temporal"),("RETURN","Devolución"),("LOCATION_CHANGE","Cambio de ubicación"),("CUSTODY_CHANGE","Cambio de resguardatario"),("MAINTENANCE_OUT","Salida a mantenimiento"),("MAINTENANCE_IN","Retorno de mantenimiento"),("DIAGNOSIS_OUT","Salida a diagnóstico"),("DIAGNOSIS_IN","Retorno de diagnóstico"),("DISPOSAL_REQUEST","Solicitud de baja"),("DISPOSAL_APPROVED","Baja aprobada"),("DISPOSAL_REJECTED","Baja rechazada"),("DISPOSAL_EXECUTED","Baja ejecutada"),("PHYSICAL_AUDIT","Auditoría física"),("FOUND","Activo localizado"),("NOT_FOUND","Activo no localizado"),("ADJUSTMENT","Ajuste administrativo"),("CORRECTION","Corrección de movimiento")], max_length=40, verbose_name="Tipo de movimiento")),
                ("status", models.CharField(choices=[("PENDING_ORIGIN_APPROVAL","Pendiente de autorización de origen"),("PENDING_DESTINATION_ACCEPTANCE","Pendiente de aceptación de destino"),("PENDING_PATRIMONY_EXECUTION","Pendiente de ejecución por Patrimonio"),("REJECTED","Rechazada"),("EXECUTED","Ejecutada"),("CANCELLED","Cancelada")], db_index=True, default="PENDING_ORIGIN_APPROVAL", max_length=40, verbose_name="Estado")),
                ("requested_at", models.DateTimeField(default=django.utils.timezone.now, verbose_name="Fecha de solicitud")),
                ("reason", models.TextField(verbose_name="Justificación")),
                ("occurred_at", models.DateTimeField(blank=True, null=True, verbose_name="Fecha efectiva propuesta")),
                ("origin_approved_at", models.DateTimeField(blank=True, null=True)),
                ("destination_accepted_at", models.DateTimeField(blank=True, null=True)),
                ("executed_at", models.DateTimeField(blank=True, null=True)),
                ("rejection_reason", models.TextField(blank=True, verbose_name="Motivo de rechazo")),
                ("bypass_used", models.BooleanField(default=False)),
                ("bypass_reason", models.TextField(blank=True)),
                ("asset", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="movement_requests", to="inventory.asset")),
                ("origin_dependencia", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="inventory_movement_requests_origin", to="security.dependencia")),
                ("origin_area", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="inventory_movement_requests_origin", to="security.areaoperativa")),
                ("origin_sede", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="inventory_movement_requests_origin", to="security.sede")),
                ("destination_dependencia", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="inventory_movement_requests_destination", to="security.dependencia")),
                ("destination_area", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="inventory_movement_requests_destination", to="security.areaoperativa")),
                ("destination_sede", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="inventory_movement_requests_destination", to="security.sede")),
                ("requested_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="inventory_movement_requests", to=settings.AUTH_USER_MODEL)),
                ("origin_custodian", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="inventory_movement_requests_origin", to=settings.AUTH_USER_MODEL)),
                ("destination_custodian", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="inventory_movement_requests_destination", to=settings.AUTH_USER_MODEL)),
                ("origin_approved_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="inventory_movement_origin_approvals", to=settings.AUTH_USER_MODEL)),
                ("destination_accepted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="inventory_movement_destination_acceptances", to=settings.AUTH_USER_MODEL)),
                ("executed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="inventory_movement_executions", to=settings.AUTH_USER_MODEL)),
                ("resulting_movement", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="source_request", to="inventory.inventorymovement")),
            ],
            options={"db_table":"inventory_asset_movement_requests", "ordering":["-requested_at"]},
        ),
        migrations.AddIndex(model_name="assetmovementrequest", index=models.Index(fields=["status","requested_at"], name="inv_mov_req_status_idx")),
        migrations.AddIndex(model_name="assetmovementrequest", index=models.Index(fields=["asset","requested_at"], name="inv_mov_req_asset_idx")),
    ]
