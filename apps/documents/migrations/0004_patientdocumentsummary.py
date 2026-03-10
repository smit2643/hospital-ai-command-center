from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("patients", "0002_patientprofile_extended_fields"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("documents", "0003_extraction_identity_and_dynamic_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="PatientDocumentSummary",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_document_count", models.PositiveIntegerField(default=0)),
                ("summary_text", models.TextField(blank=True)),
                ("summary_data", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "generated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "patient",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="document_summaries",
                        to="patients.patientprofile",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
