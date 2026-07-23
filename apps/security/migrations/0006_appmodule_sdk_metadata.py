from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("security", "0005_officialparameter")]

    operations = [
        migrations.AddField(model_name="appmodule", name="dependencies", field=models.JSONField(blank=True, default=list, verbose_name="Dependencias obligatorias")),
        migrations.AddField(model_name="appmodule", name="entry_url_name", field=models.CharField(blank=True, max_length=160, verbose_name="Ruta de entrada")),
        migrations.AddField(model_name="appmodule", name="health_message", field=models.CharField(blank=True, max_length=255, verbose_name="Detalle de salud")),
        migrations.AddField(model_name="appmodule", name="health_status", field=models.CharField(choices=[("HEALTHY", "Saludable"), ("WARNING", "Con advertencias"), ("UNAVAILABLE", "No disponible"), ("DISABLED", "Deshabilitado")], default="HEALTHY", max_length=20, verbose_name="Estado de salud")),
        migrations.AddField(model_name="appmodule", name="icon", field=models.CharField(default="blocks", max_length=80, verbose_name="Icono")),
        migrations.AddField(model_name="appmodule", name="last_health_check_at", field=models.DateTimeField(blank=True, null=True, verbose_name="Última comprobación")),
        migrations.AddField(model_name="appmodule", name="module_kind", field=models.CharField(choices=[("CORE", "Núcleo"), ("SATELLITE", "Satélite")], default="SATELLITE", max_length=20, verbose_name="Tipo de módulo")),
        migrations.AddField(model_name="appmodule", name="optional_integrations", field=models.JSONField(blank=True, default=list, verbose_name="Integraciones opcionales")),
        migrations.AddField(model_name="appmodule", name="version", field=models.CharField(default="1.0.0", max_length=40, verbose_name="Versión instalada")),
    ]
