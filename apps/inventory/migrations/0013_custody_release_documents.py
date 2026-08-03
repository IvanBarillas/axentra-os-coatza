from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0012_document_acknowledgement_types"),
    ]

    operations = [
        migrations.AddField(
            model_name="custodydocument",
            name="document_type",
            field=models.CharField(
                choices=[
                    ("ASSIGNMENT", "Resguardo de entrega"),
                    ("RELEASE", "Constancia de entrega y liberación"),
                ],
                db_index=True,
                default="ASSIGNMENT",
                max_length=20,
                verbose_name="Tipo de documento",
            ),
        ),
        migrations.AddField(
            model_name="custodydocument",
            name="received_by_email_snapshot",
            field=models.EmailField(blank=True, max_length=254, verbose_name="Correo de quien recibe"),
        ),
        migrations.AddField(
            model_name="custodydocument",
            name="received_by_id_snapshot",
            field=models.UUIDField(blank=True, null=True, verbose_name="UUID de quien recibe"),
        ),
        migrations.AddField(
            model_name="custodydocument",
            name="received_by_name_snapshot",
            field=models.CharField(blank=True, max_length=300, verbose_name="Recibido por"),
        ),
        migrations.AddField(
            model_name="custodydocument",
            name="source_document",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="release_documents", to="inventory.custodydocument", verbose_name="Resguardo que se libera"),
        ),
        migrations.AlterField(
            model_name="custodydocumentitem",
            name="custody_assignment",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="document_items", to="inventory.custodyassignment", verbose_name="Resguardo individual"),
        ),
    ]
