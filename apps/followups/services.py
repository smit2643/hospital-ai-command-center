import re
from datetime import date, timedelta

from django.utils import timezone

from apps.documents.models import DocumentExtractedField, PatientDocument
from apps.documents.services import _clean_text

from .models import FollowUpPlan


DATE_PATTERN = re.compile(r"\b(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\d{2}-\d{2}-\d{4})\b")
INTERVAL_PATTERN = re.compile(r"\b(after|in)\s+(\d+)\s+(day|days|week|weeks|month|months)\b", re.IGNORECASE)


def _parse_date(value: str) -> date | None:
    raw = (value or "").strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return timezone.datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def _interval_days(text: str) -> int | None:
    match = INTERVAL_PATTERN.search(text or "")
    if not match:
        return None
    count = int(match.group(2))
    unit = match.group(3).lower()
    if unit.startswith("day"):
        return count
    if unit.startswith("week"):
        return count * 7
    if unit.startswith("month"):
        return count * 30
    return None


def _extract_follow_up_text(document: PatientDocument) -> str:
    extraction = getattr(document, "extraction", None)
    if not extraction:
        return ""
    for key in ("follow_up", "follow_up_plan"):
        row = extraction.extra_fields.filter(field_key=key).first()
        if row and row.value_text:
            return row.value_text.strip()
    return _clean_text(extraction.notes)


def _anchor_date(document: PatientDocument) -> date:
    extraction = getattr(document, "extraction", None)
    if extraction and extraction.report_date_text:
        parsed = _parse_date(extraction.report_date_text)
        if parsed:
            return parsed
    return document.created_at.date()


def create_or_update_followup(document: PatientDocument) -> FollowUpPlan | None:
    if document.document_type != PatientDocument.DocumentType.PRESCRIPTION:
        return None

    follow_text = _extract_follow_up_text(document)
    if not follow_text:
        return None

    match_date = DATE_PATTERN.search(follow_text)
    explicit_date = _parse_date(match_date.group(1)) if match_date else None
    interval_days = _interval_days(follow_text)
    anchor = _anchor_date(document)

    follow_type = FollowUpPlan.FollowUpType.INTERVAL
    due_date = None
    follow_date = None

    if explicit_date:
        follow_type = FollowUpPlan.FollowUpType.DATE
        due_date = explicit_date
        follow_date = explicit_date
    elif interval_days:
        follow_type = FollowUpPlan.FollowUpType.INTERVAL
        due_date = anchor + timedelta(days=interval_days)

    if not due_date:
        return None

    reminder_date = due_date - timedelta(days=1)
    status = FollowUpPlan.Status.OVERDUE if due_date < timezone.now().date() else FollowUpPlan.Status.PENDING

    plan, _ = FollowUpPlan.objects.update_or_create(
        patient=document.patient,
        source_document=document,
        defaults={
            "doctor": document.uploaded_by,
            "follow_up_type": follow_type,
            "follow_up_text": follow_text,
            "interval_days": interval_days,
            "follow_up_date": follow_date,
            "due_date": due_date,
            "reminder_date": reminder_date,
            "status": status,
        },
    )
    return plan
