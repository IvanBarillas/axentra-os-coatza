from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0013_custody_release_documents"),
    ]

    operations = [
        migrations.AlterField(
            model_name="custodydocument",
            name="status",
            field=models.CharField(
                choices=[
                    ("DRAFT", "Borrador"),
                    ("IN_PROCESS", "En proceso"),
                    ("ACTIVE", "Vigente"),
                    ("CLOSED", "Finalizado"),
                    ("REPLACED", "Sustituido por cambio de titular"),
                    ("CANCELLED", "Cancelado"),
                ],
                db_index=True,
                default="DRAFT",
                max_length=20,
                verbose_name="Estado",
            ),
        ),
    ]
