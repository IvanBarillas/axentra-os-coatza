from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0002_asset_classification_authorized_at_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="assetloan",
            name="borrower_name_snapshot",
            field=models.CharField(
                blank=True,
                max_length=300,
                verbose_name="Nombre del receptor",
            ),
        ),
    ]
