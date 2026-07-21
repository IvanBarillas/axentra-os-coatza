from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0003_assetloan_optional_borrower"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="assetintakerequest",
            name="captured_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name="Fecha de captura",
            ),
        ),
        migrations.AddField(
            model_name="assetintakerequest",
            name="captured_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="inventory_intake_requests_captured",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Capturado por",
            ),
        ),
        migrations.AlterField(
            model_name="assetintakerequest",
            name="submitted_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="inventory_intake_requests_submitted",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Enviado por",
            ),
        ),
        migrations.AddField(
            model_name="assetintakerequest",
            name="source_app",
            field=models.CharField(
                blank=True,
                max_length=80,
                verbose_name="Aplicación de origen",
            ),
        ),
        migrations.AddField(
            model_name="assetintakerequest",
            name="source_model",
            field=models.CharField(
                blank=True,
                max_length=120,
                verbose_name="Modelo de origen",
            ),
        ),
        migrations.AddField(
            model_name="assetintakerequest",
            name="source_object_id",
            field=models.UUIDField(
                blank=True,
                db_index=True,
                null=True,
                verbose_name="UUID del registro de origen",
            ),
        ),
        migrations.AddField(
            model_name="assetintakerequest",
            name="source_folio",
            field=models.CharField(
                blank=True,
                db_index=True,
                max_length=120,
                verbose_name="Folio del registro de origen",
            ),
        ),
        migrations.AddIndex(
            model_name="assetintakerequest",
            index=models.Index(
                fields=["captured_by", "status"],
                name="idx_inv_intake_capture_st",
            ),
        ),
        migrations.AddIndex(
            model_name="assetintakerequest",
            index=models.Index(
                fields=["source_app", "source_object_id"],
                name="idx_inv_intake_source_ref",
            ),
        ),
    ]
