from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def backfill_extractions(apps, schema_editor):
    PatientDocument = apps.get_model("documents", "PatientDocument")
    DocumentExtraction = apps.get_model("documents", "DocumentExtraction")
    DocumentLabTest = apps.get_model("documents", "DocumentLabTest")

    for document in PatientDocument.objects.all().iterator():
        payload = document.extracted_summary or {}
        extraction, _ = DocumentExtraction.objects.get_or_create(
            document=document,
            defaults={
                "patient_name": str(payload.get("patient_name", "")).strip(),
                "report_date_text": str(payload.get("report_date", "")).strip(),
                "hospital_name": str(payload.get("hospital_name", "")).strip(),
                "doctor_name": str(payload.get("doctor_name", "")).strip(),
                "notes": str(payload.get("notes", "")).strip(),
            },
        )
        tests = payload.get("tests", [])
        if isinstance(tests, list):
            rows = []
            for idx, item in enumerate(tests):
                if not isinstance(item, dict):
                    continue
                rows.append(
                    DocumentLabTest(
                        extraction=extraction,
                        test_name=str(item.get("test_name", "")).strip(),
                        value=str(item.get("value", "")).strip(),
                        unit=str(item.get("unit", "")).strip(),
                        reference_range=str(item.get("reference_range", "")).strip(),
                        order_index=idx,
                    )
                )
            if rows:
                DocumentLabTest.objects.bulk_create(rows)


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DocumentExtraction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("patient_name", models.CharField(blank=True, max_length=255)),
                ("report_date_text", models.CharField(blank=True, max_length=100)),
                ("hospital_name", models.CharField(blank=True, max_length=255)),
                ("doctor_name", models.CharField(blank=True, max_length=255)),
                ("notes", models.TextField(blank=True)),
                ("is_reviewed", models.BooleanField(default=False)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("document", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="extraction", to="documents.patientdocument")),
                ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-updated_at"]},
        ),
        migrations.CreateModel(
            name="DocumentLabTest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("test_name", models.CharField(max_length=255)),
                ("value", models.CharField(blank=True, max_length=64)),
                ("unit", models.CharField(blank=True, max_length=32)),
                ("reference_range", models.CharField(blank=True, max_length=128)),
                ("order_index", models.PositiveIntegerField(default=0)),
                ("extraction", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tests", to="documents.documentextraction")),
            ],
            options={"ordering": ["order_index", "id"]},
        ),
        migrations.RunPython(backfill_extractions, migrations.RunPython.noop),
    ]
