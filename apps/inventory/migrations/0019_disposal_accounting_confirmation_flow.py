from django.db import migrations, models


DOCUMENT_TYPES = [
    ("INVOICE_XML", "Factura XML"),
    ("INVOICE_PDF", "Factura PDF"),
    ("PURCHASE_ORDER", "Orden de compra"),
    ("CONTRACT", "Contrato"),
    ("WARRANTY", "Garantía"),
    ("DELIVERY_RECEIPT", "Acta o constancia de entrega"),
    ("DEPARTMENT_ACCEPTANCE", "Aceptación de la dependencia"),
    ("PATRIMONY_VALIDATION", "Validación patrimonial"),
    ("DONATION_AGREEMENT", "Acta o contrato de donación"),
    ("TECHNICAL_VALUATION", "Avalúo técnico"),
    ("COMMERCIAL_VALUATION", "Estimación de valor comercial"),
    ("CUSTODY_RECEIPT", "Vale de resguardo generado"),
    ("SIGNED_CUSTODY_RECEIPT", "Acuse firmado de resguardo"),
    ("LOAN_RECEIPT", "Vale de préstamo generado"),
    ("SIGNED_LOAN_RECEIPT", "Acuse firmado de préstamo"),
    ("RETURN_RECEIPT", "Constancia de devolución generada"),
    ("SIGNED_RETURN_RECEIPT", "Acuse firmado de devolución"),
    ("TRANSFER_RECEIPT", "Acta de transferencia generada"),
    ("SIGNED_TRANSFER_RECEIPT", "Acuse firmado de transferencia"),
    ("TECHNICAL_DIAGNOSIS", "Diagnóstico técnico"),
    ("TECHNICAL_REPORT", "Dictamen técnico"),
    ("TECHNICAL_REPORT_REQUEST", "Oficio de solicitud de dictamen técnico"),
    ("SERVICE_ORDER", "Orden de servicio"),
    ("REPAIR_EVIDENCE", "Evidencia de reparación"),
    ("DISPOSAL_REQUEST", "Oficio de solicitud de baja"),
    ("DISPOSAL_MINUTES", "Acta de baja generada"),
    ("SIGNED_DISPOSAL_MINUTES", "Acuse firmado del acta de baja"),
    ("COUNCIL_MINUTES", "Acta de Cabildo"),
    ("POLICE_REPORT", "Denuncia ante el Ministerio Público"),
    ("DISINCORPORATION_AUTHORIZATION", "Autorización de desincorporación"),
    ("ACCOUNTING_DISPOSAL_REQUEST", "Oficio de solicitud de baja contable"),
    ("ACCOUNTING_DISPOSAL_CONFIRMATION", "Constancia de baja contable"),
    ("PHYSICAL_AUDIT_EVIDENCE", "Evidencia de auditoría física"),
    ("PHYSICAL_AUDIT_REPORT", "Reporte de auditoría física generado"),
    ("SIGNED_PHYSICAL_AUDIT_REPORT", "Acuse firmado de auditoría física"),
    ("RECONCILIATION_REPORT", "Reporte de conciliación"),
    ("PHOTO_FRONT", "Foto frontal"),
    ("PHOTO_SERIAL", "Foto serie / placa"),
    ("PHOTO_CONDITION", "Foto de condición física"),
    ("DEED", "Escritura / título"),
    ("CADASTRAL_CERTIFICATE", "Cédula / clave catastral"),
    ("OTHER", "Otro documento"),
]

STAGES = [
    ("DEPARTMENT", "Dependencia responsable"),
    ("TECHNICAL", "Dictamen técnico"),
    ("PATRIMONY", "Control Patrimonial"),
    ("LEGAL", "Área Jurídica"),
    ("INTERNAL_CONTROL", "Órgano Interno de Control"),
    ("COUNCIL", "Cabildo"),
    ("FINAL_AUTHORIZATION", "Confirmación de baja contable"),
]

STATUSES = [
    ("DRAFT", "Borrador"),
    ("SUBMITTED", "Solicitada"),
    ("EVIDENCE_PENDING", "Evidencia pendiente"),
    ("TECHNICAL_REVIEW", "En dictamen técnico"),
    ("ADMINISTRATIVE_REVIEW", "En revisión administrativa"),
    ("AUTHORIZATION_PENDING", "Pendiente de confirmación contable"),
    ("APPROVED", "Aprobada"),
    ("REJECTED", "Rechazada"),
    ("EXECUTED", "Ejecutada"),
    ("CANCELLED", "Cancelada"),
]

NEW_REQUIREMENTS = (
    (
        "TECHNICAL",
        "TECHNICAL_REPORT_REQUEST",
        "Oficio de Control Patrimonial solicitando el dictamen a Innovación/TI.",
    ),
    (
        "PATRIMONY",
        "ACCOUNTING_DISPOSAL_REQUEST",
        "Oficio de Control Patrimonial solicitando la baja contable.",
    ),
    (
        "FINAL_AUTHORIZATION",
        "ACCOUNTING_DISPOSAL_CONFIRMATION",
        "Constancia de Contabilidad con número y fecha efectiva de baja.",
    ),
)


def install_accounting_flow(apps, schema_editor):
    Requirement = apps.get_model(
        "inventory", "DisposalStageDocumentRequirement"
    )
    Disposal = apps.get_model("inventory", "DisposalRequest")
    Approval = apps.get_model("inventory", "DisposalApproval")

    Requirement.objects.filter(
        stage="PATRIMONY",
        document_type="DISPOSAL_MINUTES",
        disposal_reason="",
    ).update(is_active=False)
    Requirement.objects.filter(
        stage="FINAL_AUTHORIZATION",
        document_type="DISINCORPORATION_AUTHORIZATION",
        disposal_reason="",
    ).update(is_active=False)
    for stage, document_type, instructions in NEW_REQUIREMENTS:
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

    open_statuses = (
        "SUBMITTED",
        "EVIDENCE_PENDING",
        "TECHNICAL_REVIEW",
        "ADMINISTRATIVE_REVIEW",
        "AUTHORIZATION_PENDING",
    )
    for disposal in Disposal.objects.filter(
        status__in=open_statuses,
        is_deleted=False,
    ).iterator():
        snapshot = [
            item for item in (disposal.required_document_types_snapshot or [])
            if not (
                isinstance(item, dict)
                and (
                    (
                        item.get("stage") == "PATRIMONY"
                        and item.get("document_type") == "DISPOSAL_MINUTES"
                    )
                    or (
                        item.get("stage") == "FINAL_AUTHORIZATION"
                        and item.get("document_type")
                        == "DISINCORPORATION_AUTHORIZATION"
                    )
                )
            )
            and not (
                isinstance(item, str)
                and item in {
                    "DISPOSAL_MINUTES",
                    "DISINCORPORATION_AUTHORIZATION",
                }
            )
        ]
        technical_stage = Approval.objects.filter(
            disposal_request_id=disposal.id,
            stage="TECHNICAL",
            is_deleted=False,
        ).exists()
        required = [
            (
                "PATRIMONY",
                "ACCOUNTING_DISPOSAL_REQUEST",
                "Oficio de Control Patrimonial solicitando la baja contable.",
            ),
            (
                "FINAL_AUTHORIZATION",
                "ACCOUNTING_DISPOSAL_CONFIRMATION",
                "Constancia de Contabilidad con número y fecha efectiva de baja.",
            ),
        ]
        if technical_stage:
            required.insert(0, NEW_REQUIREMENTS[0])
        for stage, document_type, instructions in required:
            if not any(
                isinstance(item, dict)
                and item.get("stage") == stage
                and item.get("document_type") == document_type
                for item in snapshot
            ):
                snapshot.append({
                    "stage": stage,
                    "document_type": document_type,
                    "requirement_level": "REQUIRED",
                    "instructions": instructions,
                })
        disposal.required_document_types_snapshot = snapshot
        disposal.save(update_fields=[
            "required_document_types_snapshot",
            "updated_at",
        ])


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0018_auto_confirm_validated_department_disposals"),
    ]

    operations = [
        migrations.AddField(
            model_name="disposalrequest",
            name="accounting_disposal_date",
            field=models.DateField(
                blank=True,
                null=True,
                verbose_name="Fecha efectiva de baja contable",
            ),
        ),
        migrations.AddField(
            model_name="disposalrequest",
            name="accounting_disposal_number",
            field=models.CharField(
                blank=True,
                db_index=True,
                max_length=120,
                verbose_name="Número de baja contable",
            ),
        ),
        migrations.AlterField(
            model_name="assetdocument",
            name="document_type",
            field=models.CharField(
                choices=DOCUMENT_TYPES,
                db_index=True,
                max_length=60,
                verbose_name="Tipo de documento",
            ),
        ),
        migrations.AlterField(
            model_name="disposalstagedocumentrequirement",
            name="document_type",
            field=models.CharField(
                choices=DOCUMENT_TYPES,
                max_length=60,
                verbose_name="Tipo de documento",
            ),
        ),
        migrations.AlterField(
            model_name="disposalstagedocumentrequirement",
            name="stage",
            field=models.CharField(
                choices=STAGES,
                max_length=40,
                verbose_name="Etapa de baja",
            ),
        ),
        migrations.AlterField(
            model_name="disposalapproval",
            name="stage",
            field=models.CharField(
                choices=STAGES,
                max_length=40,
                verbose_name="Etapa",
            ),
        ),
        migrations.AlterField(
            model_name="disposalrequest",
            name="status",
            field=models.CharField(
                choices=STATUSES,
                db_index=True,
                default="DRAFT",
                max_length=40,
                verbose_name="Estado",
            ),
        ),
        migrations.RunPython(install_accounting_flow, migrations.RunPython.noop),
    ]
