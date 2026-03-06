from __future__ import annotations

from django.utils import timezone

from .models import DocumentExtractedField, DocumentExtraction, DocumentLabTest, PatientDocument
from .schema import get_schema_for_document_type


def _clean_text(value: object) -> str:
    return str(value or "").strip()


def _patient_defaults(document: PatientDocument) -> dict[str, str]:
    user = document.patient.user
    return {
        "patient_name": _clean_text(user.full_name),
        "patient_email": _clean_text(user.email),
        "patient_phone": _clean_text(user.phone),
        "patient_dob_text": document.patient.dob.isoformat() if document.patient.dob else "",
    }


def sync_extracted_fields(
    *,
    extraction: DocumentExtraction,
    document_type: str,
    parsed_fields: dict | None = None,
    raw_text: str = "",
) -> None:
    parsed_fields = parsed_fields or {}
    field_rows = parsed_fields.get("document_fields", []) if isinstance(parsed_fields, dict) else []
    parsed_by_key = {}
    if isinstance(field_rows, list):
        for item in field_rows:
            if not isinstance(item, dict):
                continue
            key = _clean_text(item.get("key"))
            if key:
                parsed_by_key[key] = item

    existing_rows = {row.field_key: row for row in extraction.extra_fields.all()}
    keep_keys = []
    ordered_rows = []

    for idx, spec in enumerate(get_schema_for_document_type(document_type)):
        key = spec["key"]
        keep_keys.append(key)
        row = existing_rows.get(key) or DocumentExtractedField(extraction=extraction, field_key=key)
        row.label = spec["label"]
        row.value_type = spec["value_type"]
        row.order_index = idx

        incoming = parsed_by_key.get(key, {})
        incoming_text = _clean_text(incoming.get("value_text"))
        incoming_short = _clean_text(incoming.get("value_short"))

        if key == "raw_ocr_text":
            incoming_text = raw_text

        if row.value_type == DocumentExtractedField.ValueType.TEXT:
            row.value_text = incoming_text
            if incoming_short and not row.value_text:
                row.value_text = incoming_short
            row.value_short = ""
        else:
            row.value_short = incoming_short
            if incoming_text and not row.value_short:
                row.value_short = incoming_text[:255]
            row.value_text = ""

        ordered_rows.append(row)

    extraction.extra_fields.exclude(field_key__in=keep_keys).delete()
    for row in ordered_rows:
        row.save()


def upsert_extraction_from_parsed(
    document: PatientDocument,
    parsed: dict,
    *,
    raw_text: str = "",
    identity_verified: bool = False,
    identity_message: str = "",
) -> DocumentExtraction:
    extraction, _ = DocumentExtraction.objects.get_or_create(document=document)
    defaults = _patient_defaults(document)

    extraction.patient_name = defaults["patient_name"]
    extraction.patient_email = defaults["patient_email"]
    extraction.patient_phone = defaults["patient_phone"]
    extraction.patient_dob_text = defaults["patient_dob_text"]

    extraction.report_date_text = _clean_text(parsed.get("report_date"))
    extraction.hospital_name = _clean_text(parsed.get("hospital_name"))
    extraction.doctor_name = _clean_text(parsed.get("doctor_name"))
    extraction.notes = _clean_text(parsed.get("notes"))
    extraction.identity_verified = bool(identity_verified)
    extraction.identity_message = _clean_text(identity_message)
    extraction.is_reviewed = False
    extraction.reviewed_by = None
    extraction.reviewed_at = None
    extraction.save()

    tests = parsed.get("tests", [])
    extraction.tests.all().delete()
    if isinstance(tests, list):
        rows = []
        for idx, item in enumerate(tests):
            if not isinstance(item, dict):
                continue
            name = _clean_text(item.get("test_name"))
            value = _clean_text(item.get("value"))
            unit = _clean_text(item.get("unit"))
            ref = _clean_text(item.get("reference_range"))
            if not any([name, value, unit, ref]):
                continue
            rows.append(
                DocumentLabTest(
                    extraction=extraction,
                    test_name=name,
                    value=value,
                    unit=unit,
                    reference_range=ref,
                    order_index=idx,
                )
            )
        if rows:
            DocumentLabTest.objects.bulk_create(rows)

    sync_extracted_fields(
        extraction=extraction,
        document_type=document.document_type,
        parsed_fields=parsed,
        raw_text=raw_text,
    )
    return extraction


def mark_extraction_reviewed(extraction: DocumentExtraction, reviewer) -> None:
    extraction.is_reviewed = True
    extraction.reviewed_by = reviewer
    extraction.reviewed_at = timezone.now()
    extraction.save(update_fields=["is_reviewed", "reviewed_by", "reviewed_at", "updated_at"])
