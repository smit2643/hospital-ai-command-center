from django.db import migrations, models
import django.db.models.deletion


def backfill_identity_and_fields(apps, schema_editor):
    PatientDocument = apps.get_model("documents", "PatientDocument")
    DocumentExtraction = apps.get_model("documents", "DocumentExtraction")
    DocumentExtractedField = apps.get_model("documents", "DocumentExtractedField")

    for document in PatientDocument.objects.select_related("patient__user").all().iterator():
        extraction, _ = DocumentExtraction.objects.get_or_create(document=document)
        user = document.patient.user
        extraction.patient_name = user.full_name or ""
        extraction.patient_email = user.email or ""
        extraction.patient_phone = user.phone or ""
        extraction.patient_dob_text = document.patient.dob.isoformat() if document.patient.dob else ""
        extraction.save()

        if not DocumentExtractedField.objects.filter(extraction=extraction).exists():
            DocumentExtractedField.objects.create(
                extraction=extraction,
                field_key="raw_ocr_text",
                label="Full OCR Text",
                value_type="TEXT",
                value_text="",
                order_index=999,
            )


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0002_documentextraction_documentlabtest"),
    ]

    operations = [
        migrations.AddField(
            model_name="documentextraction",
            name="identity_message",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="documentextraction",
            name="identity_verified",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="documentextraction",
            name="patient_dob_text",
            field=models.CharField(blank=True, max_length=40),
        ),
        migrations.AddField(
            model_name="documentextraction",
            name="patient_email",
            field=models.EmailField(blank=True, max_length=254),
        ),
        migrations.AddField(
            model_name="documentextraction",
            name="patient_phone",
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.CreateModel(
            name="DocumentExtractedField",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("field_key", models.CharField(max_length=64)),
                ("label", models.CharField(max_length=128)),
                (
                    "value_type",
                    models.CharField(
                        choices=[("SHORT", "Short"), ("TEXT", "Text")],
                        default="SHORT",
                        max_length=8,
                    ),
                ),
                ("value_short", models.CharField(blank=True, max_length=255)),
                ("value_text", models.TextField(blank=True)),
                ("order_index", models.PositiveIntegerField(default=0)),
                (
                    "extraction",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="extra_fields",
                        to="documents.documentextraction",
                    ),
                ),
            ],
            options={"ordering": ["order_index", "id"], "unique_together": {("extraction", "field_key")}},
        ),
        migrations.RunPython(backfill_identity_and_fields, migrations.RunPython.noop),
    ]
