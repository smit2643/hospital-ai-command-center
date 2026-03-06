from .models import PatientDocument


DOCUMENT_FIELD_SCHEMAS = {
    PatientDocument.DocumentType.LAB_REPORT: [
        {"key": "lab_name", "label": "Lab Name", "value_type": "SHORT"},
        {"key": "sample_id", "label": "Sample ID", "value_type": "SHORT"},
        {"key": "ordering_doctor", "label": "Ordering Doctor", "value_type": "SHORT"},
        {"key": "findings_summary", "label": "Findings Summary", "value_type": "TEXT"},
        {"key": "raw_ocr_text", "label": "Full OCR Text", "value_type": "TEXT"},
    ],
    PatientDocument.DocumentType.PRESCRIPTION: [
        {"key": "prescription_date", "label": "Prescription Date", "value_type": "SHORT"},
        {"key": "diagnosis", "label": "Diagnosis", "value_type": "TEXT"},
        {"key": "medications", "label": "Medications", "value_type": "TEXT"},
        {"key": "instructions", "label": "Instructions", "value_type": "TEXT"},
        {"key": "follow_up", "label": "Follow Up", "value_type": "TEXT"},
        {"key": "raw_ocr_text", "label": "Full OCR Text", "value_type": "TEXT"},
    ],
    PatientDocument.DocumentType.DISCHARGE_SUMMARY: [
        {"key": "admission_date", "label": "Admission Date", "value_type": "SHORT"},
        {"key": "discharge_date", "label": "Discharge Date", "value_type": "SHORT"},
        {"key": "primary_diagnosis", "label": "Primary Diagnosis", "value_type": "TEXT"},
        {"key": "procedures", "label": "Procedures", "value_type": "TEXT"},
        {"key": "discharge_medications", "label": "Discharge Medications", "value_type": "TEXT"},
        {"key": "follow_up_plan", "label": "Follow Up Plan", "value_type": "TEXT"},
        {"key": "raw_ocr_text", "label": "Full OCR Text", "value_type": "TEXT"},
    ],
    PatientDocument.DocumentType.OTHER: [
        {"key": "document_title", "label": "Document Title", "value_type": "SHORT"},
        {"key": "document_date", "label": "Document Date", "value_type": "SHORT"},
        {"key": "summary", "label": "Summary", "value_type": "TEXT"},
        {"key": "raw_ocr_text", "label": "Full OCR Text", "value_type": "TEXT"},
    ],
}


def get_schema_for_document_type(document_type: str) -> list[dict]:
    return DOCUMENT_FIELD_SCHEMAS.get(document_type, DOCUMENT_FIELD_SCHEMAS[PatientDocument.DocumentType.OTHER])
