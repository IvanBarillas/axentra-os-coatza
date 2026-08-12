from django.db import migrations


def seed_department_disposal_request(apps, schema_editor):
    Requirement = apps.get_model(
        "inventory", "DisposalStageDocumentRequirement"
    )
    Requirement.objects.update_or_create(
        stage="DEPARTMENT",
        disposal_reason="",
        document_type="DISPOSAL_REQUEST",
        defaults={
            "requirement_level": "REQUIRED",
            "instructions": (
                "Oficio o solicitud de baja emitida por la dependencia responsable."
            ),
            "is_active": True,
            "is_deleted": False,
        },
    )


def remove_department_disposal_request(apps, schema_editor):
    Requirement = apps.get_model(
        "inventory", "DisposalStageDocumentRequirement"
    )
    Requirement.objects.filter(
        stage="DEPARTMENT",
        disposal_reason="",
        document_type="DISPOSAL_REQUEST",
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0015_custody_document_batches"),
    ]

    operations = [
        migrations.RunPython(
            seed_department_disposal_request,
            remove_department_disposal_request,
        ),
    ]
