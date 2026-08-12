from django.db import migrations


REQUIREMENTS = (
    (
        "PATRIMONY",
        "DISPOSAL_MINUTES",
        "Acta administrativa integrada por Control Patrimonial.",
    ),
    (
        "FINAL_AUTHORIZATION",
        "DISINCORPORATION_AUTHORIZATION",
        "Resolución o autorización final de desincorporación.",
    ),
)


def seed_requirements(apps, schema_editor):
    Requirement = apps.get_model(
        "inventory", "DisposalStageDocumentRequirement"
    )
    for stage, document_type, instructions in REQUIREMENTS:
        Requirement.objects.update_or_create(
            stage=stage,
            disposal_reason="",
            document_type=document_type,
            defaults={
                "requirement_level": "REQUIRED",
                "instructions": instructions,
                "is_active": True,
                "is_deleted": False,
            },
        )


def remove_requirements(apps, schema_editor):
    Requirement = apps.get_model(
        "inventory", "DisposalStageDocumentRequirement"
    )
    for stage, document_type, _instructions in REQUIREMENTS:
        Requirement.objects.filter(
            stage=stage,
            disposal_reason="",
            document_type=document_type,
        ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0016_department_disposal_request_requirement"),
    ]

    operations = [
        migrations.RunPython(seed_requirements, remove_requirements),
    ]
