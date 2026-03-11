from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

from apps.core.services import log_audit

from .models import FollowUpPlan


@shared_task
def send_followup_reminders():
    today = timezone.now().date()
    plans = FollowUpPlan.objects.select_related("patient__user", "doctor").filter(
        reminder_date=today,
        status=FollowUpPlan.Status.PENDING,
    )
    sent_count = 0
    for plan in plans:
        patient_user = plan.patient.user
        if not patient_user.email:
            continue
        subject = "Your follow-up appointment is due tomorrow"
        appointment_url = f"{settings.SITE_BASE_URL}/patients/{plan.patient_id}/"
        context = {
            "patient_name": patient_user.full_name,
            "doctor_name": plan.doctor.full_name if plan.doctor else "Your doctor",
            "due_date": plan.due_date,
            "appointment_url": appointment_url,
            "clinic_name": getattr(plan.source_document, "document_type", "Hospital AI"),
        }
        text_body = render_to_string("followups/email_followup_reminder.txt", context)
        html_body = render_to_string("followups/email_followup_reminder.html", context)
        message = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[patient_user.email],
        )
        message.attach_alternative(html_body, "text/html")
        message.send(fail_silently=False)
        plan.status = FollowUpPlan.Status.REMINDER_SENT
        plan.reminder_sent_at = timezone.now()
        plan.save(update_fields=["status", "reminder_sent_at", "updated_at"])
        log_audit(
            actor=plan.doctor,
            action="followup.reminder_sent",
            object_type="FollowUpPlan",
            object_id=plan.id,
            metadata={"patient_id": plan.patient_id, "due_date": str(plan.due_date)},
        )
        sent_count += 1
    return sent_count
