from django.db import migrations
from django.utils import timezone


def confirm_existing_department_stages(apps, schema_editor):
    Approval = apps.get_model("inventory", "DisposalApproval")
    Document = apps.get_model("inventory", "AssetDocument")

    approvals = Approval.objects.filter(
        stage="DEPARTMENT",
        decision__in=("PENDING", "OBSERVED"),
        disposal_request__status__in=(
            "SUBMITTED",
            "EVIDENCE_PENDING",
            "TECHNICAL_REVIEW",
            "ADMINISTRATIVE_REVIEW",
            "AUTHORIZATION_PENDING",
        ),
        is_deleted=False,
    ).select_related("disposal_request")

    now = timezone.now()
    for approval in approvals.iterator():
        has_validated_office = Document.objects.filter(
            owner_type="DISPOSAL_APPROVAL",
            owner_id=approval.id,
            document_type="DISPOSAL_REQUEST",
            validation_status="VALIDATED",
            is_current_version=True,
            is_deleted=False,
        ).exists()
        if not has_validated_office:
            continue
        disposal = approval.disposal_request
        approval.decision = "APPROVED"
        approval.decided_by_id = disposal.requested_by_id
        approval.decided_by_name_snapshot = disposal.requested_by_name_snapshot
        approval.decided_by_email_snapshot = disposal.requested_by_email_snapshot
        approval.decided_at = now
        approval.comment = (
            "Confirmación automática por oficio de solicitud validado."
        )
        approval.payload = {
            **(approval.payload or {}),
            "automatic_resolution": True,
            "trigger": "migration_validated_department_disposal_request",
            "validated_at": now.isoformat(),
        }
        approval.save()
        disposal.status = "EVIDENCE_PENDING"
        disposal.save(update_fields=["status", "updated_at"])


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0017_patrimony_and_final_disposal_requirements"),
    ]

    operations = [
        migrations.RunPython(
            confirm_existing_department_stages,
            migrations.RunPython.noop,
        ),
    ]
