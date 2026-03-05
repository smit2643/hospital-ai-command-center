from django.conf import settings
from django.db import models
from apps.patients.models import PatientProfile


def upload_path(instance, filename: str) -> str:
    return f"patients/{instance.patient_id}/documents/{filename}"


class PatientDocument(models.Model):
    class DocumentType(models.TextChoices):
        LAB_REPORT = "LAB_REPORT", "Lab Report"
        PRESCRIPTION = "PRESCRIPTION", "Prescription"
        DISCHARGE_SUMMARY = "DISCHARGE_SUMMARY", "Discharge Summary"
        OTHER = "OTHER", "Other"

    class OCRStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        DONE = "DONE", "Done"
        FAILED = "FAILED", "Failed"

    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name="documents")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    document_type = models.CharField(max_length=32, choices=DocumentType.choices, default=DocumentType.OTHER)
    file = models.FileField(upload_to=upload_path)
    status = models.CharField(max_length=32, default="ACTIVE")
    ocr_status = models.CharField(max_length=16, choices=OCRStatus.choices, default=OCRStatus.PENDING)
    extracted_summary = models.JSONField(default=dict, blank=True)
    extracted_confidence = models.FloatField(default=0.0)
    version = models.PositiveIntegerField(default=1)
    previous_version = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="next_versions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Document #{self.id} ({self.document_type})"

    @property
    def latest_signature_request(self):
        return self.signature_requests.order_by("-created_at").first()

    @property
    def signature_status(self) -> str:
        req = self.latest_signature_request
        if not req:
            return "NOT_SENT"
        return req.status

    @property
    def is_signed(self) -> bool:
        return self.signature_requests.filter(status="SIGNED").exists()


class OCRResult(models.Model):
    document = models.ForeignKey(PatientDocument, on_delete=models.CASCADE, related_name="ocr_results")
    raw_text = models.TextField(blank=True)
    parsed_fields = models.JSONField(default=dict, blank=True)
    parser_version = models.CharField(max_length=32, default="v1")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class DocumentExtraction(models.Model):
    document = models.OneToOneField(PatientDocument, on_delete=models.CASCADE, related_name="extraction")
    patient_name = models.CharField(max_length=255, blank=True)
    report_date_text = models.CharField(max_length=100, blank=True)
    hospital_name = models.CharField(max_length=255, blank=True)
    doctor_name = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    is_reviewed = models.BooleanField(default=False)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]


class DocumentLabTest(models.Model):
    extraction = models.ForeignKey(DocumentExtraction, on_delete=models.CASCADE, related_name="tests")
    test_name = models.CharField(max_length=255)
    value = models.CharField(max_length=64, blank=True)
    unit = models.CharField(max_length=32, blank=True)
    reference_range = models.CharField(max_length=128, blank=True)
    order_index = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order_index", "id"]
