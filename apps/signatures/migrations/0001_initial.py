import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import apps.signatures.models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("documents", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="SignatureRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("signer_email", models.EmailField(max_length=254)),
                ("token", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("expires_at", models.DateTimeField()),
                (
                    "status",
                    models.CharField(
                        choices=[("SENT", "Sent"), ("VIEWED", "Viewed"), ("SIGNED", "Signed"), ("EXPIRED", "Expired"), ("CANCELLED", "Cancelled")],
                        default="SENT",
                        max_length=16,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "document",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="signature_requests",
                        to="documents.patientdocument",
                    ),
                ),
                (
                    "requester",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="requested_signatures",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="SignatureArtifact",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("signature_type", models.CharField(choices=[("DRAWN", "Drawn"), ("TYPED", "Typed")], max_length=16)),
                (
                    "signature_image",
                    models.ImageField(blank=True, null=True, upload_to=apps.signatures.models.signature_image_path),
                ),
                ("signed_pdf", models.FileField(upload_to=apps.signatures.models.signed_pdf_path)),
                ("document_hash_sha256", models.CharField(max_length=64)),
                ("signed_at", models.DateTimeField(auto_now_add=True)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.CharField(blank=True, max_length=255)),
                (
                    "signature_request",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="artifact",
                        to="signatures.signaturerequest",
                    ),
                ),
            ],
        ),
    ]
