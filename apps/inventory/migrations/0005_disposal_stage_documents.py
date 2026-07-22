import uuid

from django.db import migrations, models
from apps.inventory.models.catalog_models import DocumentType


def seed_requirements(apps, schema_editor):
    Requirement = apps.get_model("inventory", "DisposalStageDocumentRequirement")
    rows = [
        ("DEPARTMENT", "", "DISPOSAL_REQUEST", "REQUIRED", "Oficio firmado por la dependencia responsable."),
        ("TECHNICAL", "OBSOLESCENCE", "TECHNICAL_REPORT", "REQUIRED", "Dictamen técnico que sustente la obsolescencia."),
        ("TECHNICAL", "IRREPARABLE_DAMAGE", "TECHNICAL_REPORT", "REQUIRED", "Dictamen técnico de daño irreparable."),
        ("TECHNICAL", "DISASTER", "TECHNICAL_REPORT", "REQUIRED", "Dictamen técnico posterior al siniestro."),
        ("TECHNICAL", "SCRAP", "TECHNICAL_REPORT", "REQUIRED", "Dictamen técnico del estado del bien."),
        ("LEGAL", "THEFT", "POLICE_REPORT", "REQUIRED", "Denuncia presentada ante el Ministerio Público."),
        ("LEGAL", "LOSS", "POLICE_REPORT", "REQUIRED", "Constancia o denuncia que sustente el extravío."),
        ("COUNCIL", "SCRAP", "COUNCIL_MINUTES", "REQUIRED", "Acta de Cabildo que autorice la desincorporación."),
        ("COUNCIL", "DONATION", "COUNCIL_MINUTES", "REQUIRED", "Acta de Cabildo que autorice la donación."),
        ("COUNCIL", "SALE", "COUNCIL_MINUTES", "REQUIRED", "Acta de Cabildo que autorice la enajenación."),
        ("COUNCIL", "DESTRUCTION", "COUNCIL_MINUTES", "REQUIRED", "Acta de Cabildo que autorice la destrucción."),
        ("COUNCIL", "LEGAL_DISINCORPORATION", "COUNCIL_MINUTES", "REQUIRED", "Acta de Cabildo correspondiente."),
        ("PATRIMONY", "", "DISPOSAL_MINUTES", "OPTIONAL", "Acta circunstanciada integrada por Control Patrimonial."),
        ("FINAL_AUTHORIZATION", "", "DISINCORPORATION_AUTHORIZATION", "OPTIONAL", "Autorización final firmada."),
    ]
    for stage, reason, document_type, level, instructions in rows:
        Requirement.objects.get_or_create(
            stage=stage,
            disposal_reason=reason,
            document_type=document_type,
            defaults={"requirement_level": level, "instructions": instructions},
        )


class Migration(migrations.Migration):
    dependencies = [("inventory", "0004_assetintake_traceability")]

    operations = [
        migrations.AlterField(
            model_name="assetdocument",
            name="owner_type",
            field=models.CharField(
                choices=[
                    ("INTAKE_REQUEST", "Solicitud de alta"),
                    ("ASSET", "Activo patrimonial"),
                    ("CUSTODY_ASSIGNMENT", "Resguardo"),
                    ("MOVEMENT", "Movimiento patrimonial"),
                    ("LOAN", "Préstamo"),
                    ("DISPOSAL_REQUEST", "Expediente de baja"),
                    ("DISPOSAL_APPROVAL", "Etapa de aprobación de baja"),
                    ("PHYSICAL_AUDIT_SESSION", "Auditoría física"),
                    ("PHYSICAL_AUDIT_ITEM", "Partida de auditoría física"),
                    ("SERVICE_ORDER", "Orden de servicio"),
                    ("TECHNICAL_DIAGNOSIS", "Diagnóstico técnico"),
                    ("TECHNICAL_REPORT", "Dictamen técnico"),
                    ("COMPONENT", "Componente o refacción"),
                    ("OTHER", "Otro expediente"),
                ],
                db_index=True,
                max_length=40,
                verbose_name="Tipo de expediente propietario",
            ),
        ),
        migrations.AlterField(
            model_name="assetphoto",
            name="owner_type",
            field=models.CharField(
                choices=[
                    ("INTAKE_REQUEST", "Solicitud de alta"),
                    ("ASSET", "Activo patrimonial"),
                    ("CUSTODY_ASSIGNMENT", "Resguardo"),
                    ("MOVEMENT", "Movimiento patrimonial"),
                    ("LOAN", "Préstamo"),
                    ("DISPOSAL_REQUEST", "Expediente de baja"),
                    ("DISPOSAL_APPROVAL", "Etapa de aprobación de baja"),
                    ("PHYSICAL_AUDIT_SESSION", "Auditoría física"),
                    ("PHYSICAL_AUDIT_ITEM", "Partida de auditoría física"),
                    ("SERVICE_ORDER", "Orden de servicio"),
                    ("TECHNICAL_DIAGNOSIS", "Diagnóstico técnico"),
                    ("TECHNICAL_REPORT", "Dictamen técnico"),
                    ("COMPONENT", "Componente o refacción"),
                    ("OTHER", "Otro expediente"),
                ],
                db_index=True,
                max_length=40,
                verbose_name="Tipo de expediente propietario",
            ),
        ),
        migrations.CreateModel(
            name="DisposalStageDocumentRequirement",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("is_active", models.BooleanField(db_index=True, default=True, verbose_name="Activo")),
                ("is_deleted", models.BooleanField(db_index=True, default=False, verbose_name="Eliminado")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Creado")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Actualizado")),
                ("deleted_at", models.DateTimeField(blank=True, null=True, verbose_name="Fecha de baja lógica")),
                ("stage", models.CharField(choices=[("DEPARTMENT", "Dependencia responsable"), ("TECHNICAL", "Dictamen técnico"), ("PATRIMONY", "Control Patrimonial"), ("LEGAL", "Área Jurídica"), ("INTERNAL_CONTROL", "Órgano Interno de Control"), ("COUNCIL", "Cabildo"), ("FINAL_AUTHORIZATION", "Autorización final")], max_length=40, verbose_name="Etapa de baja")),
                ("disposal_reason", models.CharField(blank=True, choices=[("OBSOLESCENCE", "Obsolescencia"), ("IRREPARABLE_DAMAGE", "Daño irreparable"), ("THEFT", "Robo"), ("LOSS", "Extravío"), ("DISASTER", "Siniestro"), ("SCRAP", "Desecho / chatarra"), ("DONATION", "Donación"), ("TRANSFER", "Transferencia"), ("SALE", "Enajenación / venta"), ("DESTRUCTION", "Destrucción autorizada"), ("LEGAL_DISINCORPORATION", "Desincorporación legal"), ("OTHER", "Otro motivo autorizado")], help_text="Vacío significa que aplica a todos los motivos.", max_length=50, verbose_name="Motivo específico")),
                ("document_type", models.CharField(choices=DocumentType.choices, max_length=60, verbose_name="Tipo de documento")),
                ("requirement_level", models.CharField(choices=[("REQUIRED", "Obligatorio"), ("OPTIONAL", "Opcional")], default="REQUIRED", max_length=20, verbose_name="Nivel de requisito")),
                ("instructions", models.TextField(blank=True, verbose_name="Indicaciones")),
            ],
            options={
                "verbose_name": "Requisito documental de baja",
                "verbose_name_plural": "Requisitos documentales de bajas",
                "db_table": "inventory_disposal_stage_document_requirements",
                "ordering": ["stage", "disposal_reason", "document_type"],
            },
        ),
        migrations.AddConstraint(
            model_name="disposalstagedocumentrequirement",
            constraint=models.UniqueConstraint(fields=("stage", "disposal_reason", "document_type"), name="uq_inv_disp_doc_requirement"),
        ),
        migrations.RunPython(seed_requirements, migrations.RunPython.noop),
    ]
