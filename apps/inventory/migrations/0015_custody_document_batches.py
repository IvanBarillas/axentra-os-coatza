import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0014_custody_document_active_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="custodydocument",
            name="batch_id",
            field=models.UUIDField(
                db_index=True,
                default=uuid.uuid4,
                help_text=(
                    "Agrupa documentos individuales creados en una "
                    "operación masiva."
                ),
                verbose_name="Lote operativo",
            ),
        ),
        migrations.AddField(
            model_name="custodydocument",
            name="batch_position",
            field=models.PositiveIntegerField(
                default=1,
                verbose_name="Posición en el lote",
            ),
        ),
        migrations.AddField(
            model_name="custodydocument",
            name="batch_size",
            field=models.PositiveIntegerField(
                default=1,
                verbose_name="Documentos en el lote",
            ),
        ),
    ]
