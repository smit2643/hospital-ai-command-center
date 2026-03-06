# OCR Review and Signature Flow

## Objective
Ensure OCR output is mapped into visible, editable UI fields per document type, with patient-identity guardrails and a one-click signature handoff.

## Current End-to-End Flow
1. Upload document at `/documents/upload/` and select `Document Type`.
2. Trigger OCR from `/patients/<id>/documents/`.
3. OCR page (`/documents/<id>/ocr/result/`) auto-polls status (no manual refresh needed).
4. OCR extraction is persisted into:
- Core extraction fields (`patient/report/hospital/doctor/notes`)
- Dynamic schema fields (`DocumentExtractedField`) per document type
- Lab test rows (`DocumentLabTest`) for lab reports
5. If OCR text has unmatched content, it is always retained in `Full OCR Text` field.
6. User reviews/edits values and saves.
7. Optional: send signature request from same page.

## Identity Guard
- OCR compares selected patient identity against extracted identity signals.
- Name mismatch blocks OCR finalize.
- If secondary identity data (email/dob/phone) is absent, system continues with warning and keeps full OCR text visible.

## Document-Type Field Schemas
- `LAB_REPORT`: lab_name, sample_id, ordering_doctor, findings_summary, raw_ocr_text
- `PRESCRIPTION`: prescription_date, diagnosis, medications, instructions, follow_up, raw_ocr_text
- `DISCHARGE_SUMMARY`: admission_date, discharge_date, primary_diagnosis, procedures, discharge_medications, follow_up_plan, raw_ocr_text
- `OTHER`: document_title, document_date, summary, raw_ocr_text

## Signature Status Visibility
Document table shows:
- `NOT SENT`
- `SENT`
- `VIEWED`
- `SIGNED`

## OCR Provider Notes
- Default: open-source Tesseract (`OCR_PROVIDER=tesseract`)
- Optional: Gemini provider (`OCR_PROVIDER=gemini` + key)
- Parser includes typo-tolerant key matching and schema-mapping fallback.
