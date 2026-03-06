import re
from datetime import datetime

from celery import shared_task

from apps.core.services import log_audit

from .models import OCRResult, PatientDocument
from .ocr import run_ocr_pipeline
from .services import upsert_extraction_from_parsed


def _normalize_name(value: str) -> str:
    return " ".join((value or "").strip().lower().split())


def _normalize_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    return digits[-10:] if len(digits) >= 10 else digits


def _normalize_date(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return raw


def _verify_patient_identity(document: PatientDocument, identity: dict) -> tuple[bool, str]:
    patient_user = document.patient.user

    extracted_name = _normalize_name(identity.get("patient_name", ""))
    extracted_email = (identity.get("patient_email", "") or "").strip().lower()
    extracted_phone = _normalize_phone(identity.get("patient_phone", ""))
    extracted_dob = _normalize_date(identity.get("patient_dob", ""))

    expected_name = _normalize_name(patient_user.full_name)
    expected_email = (patient_user.email or "").strip().lower()
    expected_phone = _normalize_phone(patient_user.phone)
    expected_dob = document.patient.dob.isoformat() if document.patient.dob else ""

    if not extracted_name:
        return False, "Patient verification failed: patient name not found in document OCR text."
    if extracted_name != expected_name:
        return False, "Patient selected is wrong. Name in document does not match selected patient."

    secondary_checked = 0
    secondary_matched = 0

    if extracted_email:
        secondary_checked += 1
        if extracted_email == expected_email:
            secondary_matched += 1
        else:
            return False, "Patient selected is wrong. Email in document does not match selected patient."

    if extracted_dob:
        secondary_checked += 1
        if extracted_dob == expected_dob:
            secondary_matched += 1
        else:
            return False, "Patient selected is wrong. DOB in document does not match selected patient."

    if extracted_phone:
        secondary_checked += 1
        if extracted_phone == expected_phone:
            secondary_matched += 1
        else:
            return False, "Patient selected is wrong. Phone in document does not match selected patient."

    if secondary_checked == 0:
        return True, "Patient verified by name. Secondary identity fields (email/dob/phone) not found in OCR."

    if secondary_matched == 0:
        return False, "Patient selected is wrong combination of name, dob, email and phone."

    return True, "Patient identity verified successfully."


@shared_task
def process_document_ocr(document_id: int):
    document = PatientDocument.objects.select_related("patient__user", "uploaded_by").get(id=document_id)
    document.ocr_status = PatientDocument.OCRStatus.PROCESSING
    document.save(update_fields=["ocr_status", "updated_at"])

    try:
        result = run_ocr_pipeline(document.file.path, document.document_type)
        is_valid, verify_message = _verify_patient_identity(document, result.get("identity", {}))

        parsed_fields = result["parsed"]
        if not is_valid:
            parsed_fields = {
                "error": verify_message,
                "identity": result.get("identity", {}),
                "document_type": document.document_type,
            }
            OCRResult.objects.create(
                document=document,
                raw_text=result["raw_text"],
                parsed_fields=parsed_fields,
                parser_version="v2",
            )
            document.extracted_summary = {}
            document.extracted_confidence = 0.0
            document.ocr_status = PatientDocument.OCRStatus.FAILED
            document.save(update_fields=["extracted_summary", "extracted_confidence", "ocr_status", "updated_at"])
            upsert_extraction_from_parsed(
                document,
                {},
                raw_text=result["raw_text"],
                identity_verified=False,
                identity_message=verify_message,
            )
            return document_id

        OCRResult.objects.create(
            document=document,
            raw_text=result["raw_text"],
            parsed_fields=parsed_fields,
            parser_version="v2",
        )
        upsert_extraction_from_parsed(
            document,
            parsed_fields,
            raw_text=result["raw_text"],
            identity_verified=True,
            identity_message=verify_message,
        )
        document.extracted_summary = {}
        document.extracted_confidence = result["confidence"]
        document.ocr_status = PatientDocument.OCRStatus.DONE
        document.save(update_fields=["extracted_summary", "extracted_confidence", "ocr_status", "updated_at"])

        log_audit(
            actor=document.uploaded_by,
            action="document.ocr_completed",
            object_type="PatientDocument",
            object_id=document.id,
            metadata={
                "confidence": result["confidence"],
                "provider": result.get("provider", "tesseract"),
                "identity_verified": True,
            },
        )
    except Exception as exc:  # noqa: BLE001
        document.ocr_status = PatientDocument.OCRStatus.FAILED
        document.save(update_fields=["ocr_status", "updated_at"])
        OCRResult.objects.create(
            document=document,
            raw_text="",
            parsed_fields={"error": str(exc)},
            parser_version="v2",
        )

    return document_id
