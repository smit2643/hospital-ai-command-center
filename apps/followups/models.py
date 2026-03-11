from django.conf import settings
from django.db import models

from apps.documents.models import PatientDocument
from apps.patients.models import PatientProfile


class FollowUpPlan(models.Model):
    class FollowUpType(models.TextChoices):
        DATE = "DATE", "Date"
        INTERVAL = "INTERVAL", "Interval"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        REMINDER_SENT = "REMINDER_SENT", "Reminder Sent"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"
        OVERDUE = "OVERDUE", "Overdue"

    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name="followups")
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="followups_created",
    )
    source_document = models.ForeignKey(
        PatientDocument,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="followups",
    )
    follow_up_type = models.CharField(max_length=16, choices=FollowUpType.choices, default=FollowUpType.INTERVAL)
    follow_up_text = models.TextField(blank=True)
    interval_days = models.PositiveIntegerField(null=True, blank=True)
    follow_up_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    reminder_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-due_date", "-created_at"]

    def __str__(self) -> str:
        return f"Follow-up for patient #{self.patient_id} due {self.due_date or 'TBD'}"
