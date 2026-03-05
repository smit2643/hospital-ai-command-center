from celery import shared_task
from apps.core.services import log_audit
from .models import OCRResult, PatientDocument
from .ocr import run_ocr_pipeline


@shared_task
def process_document_ocr(document_id: int):
    document = PatientDocument.objects.select_related("patient", "uploaded_by").get(id=document_id)
    document.ocr_status = PatientDocument.OCRStatus.PROCESSING
    document.save(update_fields=["ocr_status", "updated_at"])

    try:
        result = run_ocr_pipeline(document.file.path)
        OCRResult.objects.create(
            document=document,
            raw_text=result["raw_text"],
            parsed_fields=result["parsed"],
            parser_version="v1",
        )
        document.extracted_summary = result["parsed"]
        document.extracted_confidence = result["confidence"]
        document.ocr_status = PatientDocument.OCRStatus.DONE
        document.save(update_fields=["extracted_summary", "extracted_confidence", "ocr_status", "updated_at"])

        log_audit(
            actor=document.uploaded_by,
            action="document.ocr_completed",
            object_type="PatientDocument",
            object_id=document.id,
            metadata={"confidence": result["confidence"]},
        )
    except Exception as exc:  # noqa: BLE001
        document.ocr_status = PatientDocument.OCRStatus.FAILED
        document.save(update_fields=["ocr_status", "updated_at"])
        OCRResult.objects.create(
            document=document,
            raw_text="",
            parsed_fields={"error": str(exc)},
            parser_version="v1",
        )

    return document_id
