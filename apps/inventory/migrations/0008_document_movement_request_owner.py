from django.db import migrations, models


OWNER_CHOICES = [
    ("INTAKE_REQUEST", "Solicitud de alta"),
    ("ASSET", "Activo patrimonial"),
    ("CUSTODY_ASSIGNMENT", "Resguardo"),
    ("MOVEMENT", "Movimiento patrimonial"),
    ("MOVEMENT_REQUEST", "Solicitud de movimiento"),
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
]


class Migration(migrations.Migration):
    dependencies = [("inventory", "0007_asset_movement_request")]

    operations = [
        migrations.AlterField(
            model_name="assetdocument",
            name="owner_type",
            field=models.CharField(
                "Tipo de expediente propietario",
                max_length=40,
                choices=OWNER_CHOICES,
                db_index=True,
            ),
        ),
        migrations.AlterField(
            model_name="assetphoto",
            name="owner_type",
            field=models.CharField(
                "Tipo de expediente propietario",
                max_length=40,
                choices=OWNER_CHOICES,
                db_index=True,
            ),
        ),
    ]
