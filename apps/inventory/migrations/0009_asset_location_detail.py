from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0008_document_movement_request_owner"),
    ]

    operations = [
        migrations.AddField(
            model_name="assetintakerequest",
            name="location_detail",
            field=models.CharField(
                blank=True,
                help_text=(
                    "Ejemplo: rack del cuarto piso, oficina 204 o almacén norte."
                ),
                max_length=255,
                verbose_name="Detalle de ubicación física",
            ),
        ),
        migrations.AddField(
            model_name="asset",
            name="location_detail",
            field=models.CharField(
                blank=True,
                help_text=(
                    "Referencia precisa dentro de la sede: piso, oficina, rack o almacén."
                ),
                max_length=255,
                verbose_name="Detalle de ubicación física",
            ),
        ),
    ]
