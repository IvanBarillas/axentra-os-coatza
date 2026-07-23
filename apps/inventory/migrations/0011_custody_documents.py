from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0010_custody_assignee_mode"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CustodyDocument",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("is_active", models.BooleanField(db_index=True, default=True, verbose_name="Activo")),
                ("is_deleted", models.BooleanField(db_index=True, default=False, verbose_name="Eliminado")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Creado")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Actualizado")),
                ("deleted_at", models.DateTimeField(blank=True, null=True, verbose_name="Fecha de baja lógica")),
                ("folio", models.CharField(max_length=80, unique=True, verbose_name="Folio del documento")),
                ("status", models.CharField(choices=[("DRAFT", "Borrador"), ("IN_PROCESS", "En proceso"), ("CLOSED", "Finalizado"), ("REPLACED", "Sustituido por cambio de titular"), ("CANCELLED", "Cancelado")], db_index=True, default="DRAFT", max_length=20, verbose_name="Estado")),
                ("department_id", models.UUIDField(db_index=True, verbose_name="UUID de la dependencia")),
                ("department_name_snapshot", models.CharField(max_length=220, verbose_name="Dependencia")),
                ("department_code_snapshot", models.CharField(blank=True, max_length=40, verbose_name="Código de dependencia")),
                ("assignee_mode", models.CharField(max_length=30, verbose_name="Tipo de responsable")),
                ("assigned_to_id_snapshot", models.UUIDField(verbose_name="UUID del responsable")),
                ("assigned_to_name_snapshot", models.CharField(max_length=300, verbose_name="Responsable")),
                ("assigned_to_email_snapshot", models.EmailField(blank=True, max_length=254, verbose_name="Correo del responsable")),
                ("prepared_at", models.DateTimeField(default=django.utils.timezone.now, verbose_name="Fecha de elaboración")),
                ("closed_at", models.DateTimeField(blank=True, null=True, verbose_name="Fecha de finalización")),
                ("closure_reason", models.TextField(blank=True, verbose_name="Motivo de finalización")),
                ("notes", models.TextField(blank=True, verbose_name="Notas")),
                ("closed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="inventory_custody_documents_closed", to=settings.AUTH_USER_MODEL, verbose_name="Finalizado por")),
                ("prepared_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="inventory_custody_documents_prepared", to=settings.AUTH_USER_MODEL, verbose_name="Elaborado por")),
                ("replacement_of", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="replacement_document", to="inventory.custodydocument", verbose_name="Documento sustituido")),
            ],
            options={
                "verbose_name": "Documento de resguardo",
                "verbose_name_plural": "Documentos de resguardo",
                "db_table": "inventory_custody_documents",
                "ordering": ["-prepared_at"],
                "indexes": [
                    models.Index(fields=["department_id", "status"], name="inv_cust_doc_dept_status"),
                    models.Index(fields=["assigned_to_id_snapshot", "status"], name="inv_cust_doc_assignee"),
                    models.Index(fields=["prepared_at"], name="inv_cust_doc_prepared"),
                ],
            },
        ),
        migrations.CreateModel(
            name="CustodyDocumentItem",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("is_active", models.BooleanField(db_index=True, default=True, verbose_name="Activo")),
                ("is_deleted", models.BooleanField(db_index=True, default=False, verbose_name="Eliminado")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Creado")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Actualizado")),
                ("deleted_at", models.DateTimeField(blank=True, null=True, verbose_name="Fecha de baja lógica")),
                ("asset_id_snapshot", models.UUIDField(verbose_name="UUID histórico del bien")),
                ("inventory_number_snapshot", models.CharField(max_length=120, verbose_name="Folio patrimonial histórico")),
                ("asset_name_snapshot", models.CharField(max_length=220, verbose_name="Nombre histórico del bien")),
                ("serial_number_snapshot", models.CharField(blank=True, max_length=160, verbose_name="Número de serie histórico")),
                ("custody_assignment", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="document_item", to="inventory.custodyassignment", verbose_name="Resguardo individual")),
                ("document", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="items", to="inventory.custodydocument", verbose_name="Documento")),
            ],
            options={
                "verbose_name": "Bien en documento de resguardo",
                "verbose_name_plural": "Bienes en documentos de resguardo",
                "db_table": "inventory_custody_document_items",
                "ordering": ["inventory_number_snapshot"],
                "constraints": [
                    models.UniqueConstraint(fields=("document", "asset_id_snapshot"), name="uq_inv_custody_document_asset"),
                ],
            },
        ),
    ]
