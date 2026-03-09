from __future__ import annotations

import re

from django.utils import timezone

from .models import (
    DocumentExtractedField,
    DocumentExtraction,
    DocumentLabTest,
    PatientDocument,
    PatientDocumentSummary,
)
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
    document_fields = parsed.get("document_fields", []) if isinstance(parsed, dict) else []
    doc_field_map = {}
    if isinstance(document_fields, list):
        for item in document_fields:
            if not isinstance(item, dict):
                continue
            key = _clean_text(item.get("key"))
            if not key:
                continue
            doc_field_map[key] = {
                "value_short": _clean_text(item.get("value_short")),
                "value_text": _clean_text(item.get("value_text")),
            }

    extraction.patient_name = defaults["patient_name"]
    extraction.patient_email = defaults["patient_email"]
    extraction.patient_phone = defaults["patient_phone"]
    extraction.patient_dob_text = defaults["patient_dob_text"]

    extraction.report_date_text = _clean_text(parsed.get("report_date"))
    extraction.hospital_name = (
        _clean_text(parsed.get("hospital_name"))
        or doc_field_map.get("lab_name", {}).get("value_short", "")
        or doc_field_map.get("lab_name", {}).get("value_text", "")
    )
    extraction.doctor_name = (
        _clean_text(parsed.get("doctor_name"))
        or doc_field_map.get("ordering_doctor", {}).get("value_short", "")
        or doc_field_map.get("ordering_doctor", {}).get("value_text", "")
    )
    extraction.notes = _clean_text(parsed.get("notes"))
    if not extraction.notes:
        extraction.notes = doc_field_map.get("findings_summary", {}).get("value_text", "")
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


def _to_float(value: str) -> float | None:
    match = re.search(r"-?\d+(?:\.\d+)?", str(value or ""))
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _range_bounds(reference_range: str) -> tuple[float | None, float | None]:
    normalized = str(reference_range or "").replace("to", "-").replace("–", "-")
    nums = re.findall(r"\d+(?:\.\d+)?", normalized)
    if len(nums) < 2:
        return (None, None)
    try:
        return (float(nums[0]), float(nums[1]))
    except ValueError:
        return (None, None)


def _dedupe_keep_order(items: list[str]) -> list[str]:
    seen = set()
    out = []
    for item in items:
        key = item.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item.strip())
    return out


def _extract_year(text: str, fallback_year: int) -> int:
    match = re.search(r"(19|20)\d{2}", str(text or ""))
    if match:
        return int(match.group(0))
    return fallback_year


def generate_patient_document_summary(patient, generated_by=None) -> PatientDocumentSummary:
    documents = (
        patient.documents.select_related("uploaded_by")
        .prefetch_related("ocr_results", "extraction__tests", "extraction__extra_fields")
        .order_by("-created_at")
    )
    docs = list(documents)

    lines = []
    abnormal_tests: list[dict] = []
    medications: list[str] = []
    diagnoses: list[str] = []
    notes: list[str] = []
    timeline: list[dict] = []
    doc_types: dict[str, int] = {}
    ocr_done = 0
    test_trend_map: dict[str, dict] = {}

    for document in docs:
        doc_types[document.document_type] = doc_types.get(document.document_type, 0) + 1
        if document.ocr_status == PatientDocument.OCRStatus.DONE:
            ocr_done += 1

        extraction = getattr(document, "extraction", None)
        created_label = document.created_at.strftime("%Y-%m-%d")
        timeline.append(
            {
                "document_id": document.id,
                "date": created_label,
                "type": document.get_document_type_display(),
                "ocr_status": document.ocr_status,
                "signed": bool(document.is_signed),
            }
        )

        brief = [f"Doc #{document.id} ({document.get_document_type_display()}) on {created_label}"]
        if extraction and extraction.doctor_name:
            brief.append(f"doctor: {extraction.doctor_name}")
        if extraction and extraction.hospital_name:
            brief.append(f"hospital: {extraction.hospital_name}")
        lines.append(" | ".join(brief))

        if extraction and extraction.notes:
            notes.append(extraction.notes.strip())

        if extraction:
            for row in extraction.extra_fields.all():
                label = (row.label or row.field_key or "").strip().lower()
                value = (row.value_text if row.value_type == DocumentExtractedField.ValueType.TEXT else row.value_short).strip()
                if not value:
                    continue
                if "medication" in label or "rx" in label:
                    medications.extend([v.strip("-• ").strip() for v in value.splitlines() if v.strip()])
                elif "diagnosis" in label:
                    diagnoses.extend([v.strip("-• ").strip() for v in value.splitlines() if v.strip()])

            for test in extraction.tests.all():
                value = _to_float(test.value)
                low, high = _range_bounds(test.reference_range)
                report_year = _extract_year(extraction.report_date_text, fallback_year=document.created_at.year)

                test_key = (test.test_name or "").strip().lower()
                if test_key and value is not None:
                    trend_bucket = test_trend_map.setdefault(
                        test_key,
                        {
                            "test_name": test.test_name.strip(),
                            "unit": (test.unit or "").strip(),
                            "points": [],
                        },
                    )
                    trend_bucket["points"].append(
                        {
                            "year": report_year,
                            "value": value,
                            "raw_value": test.value,
                            "document_id": document.id,
                        }
                    )

                if value is None or low is None or high is None:
                    continue
                if value < low or value > high:
                    abnormal_tests.append(
                        {
                            "test_name": test.test_name,
                            "value": test.value,
                            "unit": test.unit,
                            "reference_range": test.reference_range,
                            "document_id": document.id,
                        }
                    )

    medications = _dedupe_keep_order(medications)
    diagnoses = _dedupe_keep_order(diagnoses)
    notes = _dedupe_keep_order(notes)
    test_trends = []
    for trend in test_trend_map.values():
        points = sorted(trend["points"], key=lambda item: item["year"])
        pretty = [f'{point["year"]} -> {point["raw_value"]}' for point in points]
        test_trends.append(
            {
                "test_name": trend["test_name"],
                "unit": trend["unit"],
                "points": points,
                "trend_text": "\n".join(pretty),
            }
        )
    test_trends.sort(key=lambda item: item["test_name"].lower())

    if not docs:
        summary_text = "No documents are available for this patient yet."
        doctor_ready_summary = "No records available to build a clinical summary."
    else:
        summary_text = (
            f"{len(docs)} document(s) processed, OCR complete for {ocr_done}. "
            f"{len(abnormal_tests)} abnormal lab indicator(s), "
            f"{len(medications)} medication mention(s), and "
            f"{len(notes)} clinical note highlight(s) detected."
        )
        doctor_ready_parts = [
            f"Patient record consolidated from {len(docs)} uploaded document(s).",
            f"OCR completed for {ocr_done} document(s).",
        ]
        if diagnoses:
            doctor_ready_parts.append("Clinical diagnoses seen: " + "; ".join(diagnoses[:5]) + ".")
        if medications:
            doctor_ready_parts.append("Current/mentioned medications: " + "; ".join(medications[:6]) + ".")
        if abnormal_tests:
            markers = []
            for item in abnormal_tests[:6]:
                markers.append(f'{item["test_name"]} {item["value"]} {item["unit"]} (ref {item["reference_range"]})')
            doctor_ready_parts.append("Abnormal markers requiring review: " + "; ".join(markers) + ".")
        if notes:
            doctor_ready_parts.append("Clinical note highlights: " + " ".join(notes[:3]))
        if test_trends:
            trend_names = ", ".join(row["test_name"] for row in test_trends[:6])
            doctor_ready_parts.append(f"Trend-ready tests available: {trend_names}.")
        doctor_ready_summary = " ".join(doctor_ready_parts)

    summary_data = {
        "document_count": len(docs),
        "ocr_done_count": ocr_done,
        "document_type_breakdown": doc_types,
        "doctor_ready_summary": doctor_ready_summary,
        "abnormal_tests": abnormal_tests,
        "medications": medications[:20],
        "diagnoses": diagnoses[:20],
        "notes": notes[:10],
        "test_trends": test_trends,
        "timeline": timeline,
    }

    return PatientDocumentSummary.objects.create(
        patient=patient,
        generated_by=generated_by,
        source_document_count=len(docs),
        summary_text=summary_text,
        summary_data=summary_data,
    )
