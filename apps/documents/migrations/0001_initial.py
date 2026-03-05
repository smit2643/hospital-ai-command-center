from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import apps.documents.models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("patients", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="PatientDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "document_type",
                    models.CharField(
                        choices=[
                            ("LAB_REPORT", "Lab Report"),
                            ("PRESCRIPTION", "Prescription"),
                            ("DISCHARGE_SUMMARY", "Discharge Summary"),
                            ("OTHER", "Other"),
                        ],
                        default="OTHER",
                        max_length=32,
                    ),
                ),
                ("file", models.FileField(upload_to=apps.documents.models.upload_path)),
                ("status", models.CharField(default="ACTIVE", max_length=32)),
                (
                    "ocr_status",
                    models.CharField(
                        choices=[("PENDING", "Pending"), ("PROCESSING", "Processing"), ("DONE", "Done"), ("FAILED", "Failed")],
                        default="PENDING",
                        max_length=16,
                    ),
                ),
                ("extracted_summary", models.JSONField(blank=True, default=dict)),
                ("extracted_confidence", models.FloatField(default=0.0)),
                ("version", models.PositiveIntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "patient",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="documents",
                        to="patients.patientprofile",
                    ),
                ),
                (
                    "previous_version",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="next_versions",
                        to="documents.patientdocument",
                    ),
                ),
                (
                    "uploaded_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="OCRResult",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("raw_text", models.TextField(blank=True)),
                ("parsed_fields", models.JSONField(blank=True, default=dict)),
                ("parser_version", models.CharField(default="v1", max_length=32)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "document",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ocr_results",
                        to="documents.patientdocument",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
