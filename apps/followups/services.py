import json
import os
import re
import urllib.error
import urllib.request
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


def _raw_ocr_text(document: PatientDocument) -> str:
    extraction = getattr(document, "extraction", None)
    if extraction:
        row = extraction.extra_fields.filter(field_key="raw_ocr_text").first()
        if row and row.value_text:
            return row.value_text
    latest = document.ocr_results.first()
    return latest.raw_text if latest else ""


def _ollama_extract_followup(raw_text: str) -> dict | None:
    base_url = os.getenv("OCR_OLLAMA_BASE_URL", "http://ollama:11434").strip().rstrip("/")
    model = os.getenv("OCR_OLLAMA_MODEL", "qwen2.5:0.5b").strip()
    endpoint = f"{base_url}/api/generate"
    if not raw_text.strip():
        return None

    prompt = (
        "Extract follow-up intent from the prescription text.\n"
        "Return ONLY valid JSON with keys:\n"
        '{"follow_up_text":"", "follow_up_date":"", "interval_days":0}\n'
        "Rules:\n"
        "- follow_up_date must be YYYY-MM-DD or empty.\n"
        "- interval_days must be integer days (e.g., 14 for 2 weeks).\n"
        "- If not found, return empty/0.\n"
        f"Text:\n{raw_text}\n"
    )
    body = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.1, "num_predict": 200},
        }
    ).encode("utf-8")
    req = urllib.request.Request(endpoint, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
            raw = resp.read().decode("utf-8", errors="ignore")
    except Exception:  # noqa: BLE001
        return None

    def _extract_json(raw: str) -> dict:
        if not raw:
            return {}
        try:
            envelope = json.loads(raw)
            response_text = str(envelope.get("response", "")).strip()
            if response_text.startswith("```"):
                response_text = re.sub(r"^```(?:json)?\s*", "", response_text)
                response_text = re.sub(r"\s*```$", "", response_text)
            return json.loads(response_text)
        except Exception:  # noqa: BLE001
            return {}

    parsed = _extract_json(raw)
    if not parsed:
        return None
    return parsed


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
        llm_raw = _raw_ocr_text(document)
        llm_data = _ollama_extract_followup(llm_raw)
        if llm_data:
            llm_text = (llm_data.get("follow_up_text") or "").strip()
            follow_text = llm_text or follow_text
            llm_date = _parse_date(str(llm_data.get("follow_up_date") or ""))
            llm_interval = llm_data.get("interval_days")
            try:
                llm_interval = int(llm_interval) if llm_interval else None
            except ValueError:
                llm_interval = None
            if llm_date:
                follow_type = FollowUpPlan.FollowUpType.DATE
                due_date = llm_date
                follow_date = llm_date
            elif llm_interval:
                follow_type = FollowUpPlan.FollowUpType.INTERVAL
                interval_days = llm_interval
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
