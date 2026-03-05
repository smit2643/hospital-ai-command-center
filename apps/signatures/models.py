import uuid
from django.conf import settings
from django.db import models
from apps.documents.models import PatientDocument


def signature_image_path(instance, filename: str) -> str:
    return f"signatures/{instance.signature_request_id}/images/{filename}"


def signed_pdf_path(instance, filename: str) -> str:
    return f"signatures/{instance.signature_request_id}/signed/{filename}"


class SignatureRequest(models.Model):
    class Status(models.TextChoices):
        SENT = "SENT", "Sent"
        VIEWED = "VIEWED", "Viewed"
        SIGNED = "SIGNED", "Signed"
        EXPIRED = "EXPIRED", "Expired"
        CANCELLED = "CANCELLED", "Cancelled"

    document = models.ForeignKey(PatientDocument, on_delete=models.CASCADE, related_name="signature_requests")
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="requested_signatures")
    signer_email = models.EmailField()
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    expires_at = models.DateTimeField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.SENT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class SignatureArtifact(models.Model):
    class SignatureType(models.TextChoices):
        DRAWN = "DRAWN", "Drawn"
        TYPED = "TYPED", "Typed"

    signature_request = models.OneToOneField(SignatureRequest, on_delete=models.CASCADE, related_name="artifact")
    signature_type = models.CharField(max_length=16, choices=SignatureType.choices)
    signature_image = models.ImageField(upload_to=signature_image_path, null=True, blank=True)
    signed_pdf = models.FileField(upload_to=signed_pdf_path)
    document_hash_sha256 = models.CharField(max_length=64)
    signed_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
