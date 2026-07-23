from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0009_asset_location_detail"),
    ]

    operations = [
        migrations.AddField(
            model_name="custodyassignment",
            name="assignee_mode",
            field=models.CharField(
                choices=[
                    (
                        "DEPARTMENT_MANAGER",
                        "Titular de la dependencia",
                    ),
                    (
                        "PUBLIC_SERVANT",
                        "Servidor público",
                    ),
                ],
                default="PUBLIC_SERVANT",
                max_length=30,
                verbose_name="Tipo de responsable",
            ),
        ),
    ]

