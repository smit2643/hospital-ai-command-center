from __future__ import annotations

from django.utils import timezone

from .models import DocumentExtraction, DocumentLabTest, PatientDocument


def _clean_text(value: object) -> str:
    return str(value or "").strip()


def upsert_extraction_from_parsed(document: PatientDocument, parsed: dict) -> DocumentExtraction:
    extraction, _ = DocumentExtraction.objects.get_or_create(document=document)
    extraction.patient_name = _clean_text(parsed.get("patient_name"))
    extraction.report_date_text = _clean_text(parsed.get("report_date"))
    extraction.hospital_name = _clean_text(parsed.get("hospital_name"))
    extraction.doctor_name = _clean_text(parsed.get("doctor_name"))
    extraction.notes = _clean_text(parsed.get("notes"))
    extraction.is_reviewed = False
    extraction.reviewed_by = None
    extraction.reviewed_at = None
    extraction.save()

    tests = parsed.get("tests", [])
    if isinstance(tests, list):
        extraction.tests.all().delete()
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
    return extraction


def mark_extraction_reviewed(extraction: DocumentExtraction, reviewer) -> None:
    extraction.is_reviewed = True
    extraction.reviewed_by = reviewer
    extraction.reviewed_at = timezone.now()
    extraction.save(update_fields=["is_reviewed", "reviewed_by", "reviewed_at", "updated_at"])
