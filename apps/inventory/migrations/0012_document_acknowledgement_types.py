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
    ("SERVICE_ORDER", "Orden de servicio"),
    ("REPAIR_EVIDENCE", "Evidencia de reparación"),
    ("DISPOSAL_REQUEST", "Oficio de solicitud de baja"),
    ("DISPOSAL_MINUTES", "Acta de baja generada"),
    ("SIGNED_DISPOSAL_MINUTES", "Acuse firmado del acta de baja"),
    ("COUNCIL_MINUTES", "Acta de Cabildo"),
    ("POLICE_REPORT", "Denuncia ante el Ministerio Público"),
    ("DISINCORPORATION_AUTHORIZATION", "Autorización de desincorporación"),
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

OWNER_TYPES = [
    ("INTAKE_REQUEST", "Solicitud de alta"),
    ("ASSET", "Activo patrimonial"),
    ("CUSTODY_ASSIGNMENT", "Resguardo"),
    ("CUSTODY_DOCUMENT", "Documento agrupador de resguardo"),
    ("MOVEMENT", "Movimiento patrimonial"),
    ("MOVEMENT_REQUEST", "Solicitud de movimiento"),
    ("LOAN", "Préstamo"),
    ("DISPOSAL_REQUEST", "Expediente de baja"),
    ("DISPOSAL_APPROVAL", "Etapa de aprobación de baja"),
    ("PHYSICAL_AUDIT_SESSION", "Auditoría física"),
    ("PHYSICAL_AUDIT_ITEM", "Partida de auditoría física"),
    ("SERVICE_ORDER", "Orden de servicio"),
    ("TECHNICAL_DIAGNOSIS", "Diagnóstico técnico"),
    ("TECHNICAL_REPORT", "Dictamen técnico"),
    ("COMPONENT", "Componente o refacción"),
    ("OTHER", "Otro expediente"),
]


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0011_custody_documents"),
    ]

    operations = [
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
            model_name="assetdocument",
            name="owner_type",
            field=models.CharField(
                choices=OWNER_TYPES,
                db_index=True,
                max_length=40,
                verbose_name="Tipo de expediente propietario",
            ),
        ),
        migrations.AlterField(
            model_name="assetphoto",
            name="owner_type",
            field=models.CharField(
                choices=OWNER_TYPES,
                db_index=True,
                max_length=40,
                verbose_name="Tipo de expediente propietario",
            ),
        ),
    ]
