import os
import re
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pytesseract
from PIL import Image

from .models import PatientDocument


TEST_LINE_PATTERN = re.compile(
    r"(?P<test>[A-Za-z\s\-\(\)]+)\s+(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>[a-zA-Z/%]+)?\s*(?P<range>\d+(?:\.\d+)?\s*[-–]\s*\d+(?:\.\d+)?)?"
)
EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_PATTERN = re.compile(r"(?:\+?\d{1,3}[\s-]?)?(?:\d[\s-]?){10,14}\d")
DATE_PATTERN = re.compile(r"\b(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\d{2}-\d{2}-\d{4})\b")


def preprocess_image(file_path: str) -> np.ndarray:
    image = cv2.imread(file_path)
    if image is None:
        pil = Image.open(file_path).convert("RGB")
        image = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray)
    _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh


def extract_text(file_path: str) -> str:
    processed = preprocess_image(file_path)
    return pytesseract.image_to_string(processed)


def extract_text_with_gemini(file_path: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not configured")
    try:
        import google.generativeai as genai  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("google-generativeai dependency is missing") from exc

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-1.5-flash"))
    with open(file_path, "rb") as f:
        file_bytes = f.read()
    prompt = "Extract all readable text from this hospital document with line structure preserved."
    response = model.generate_content(
        [
            prompt,
            {"mime_type": "image/png", "data": file_bytes},
        ]
    )
    text = getattr(response, "text", "") or ""
    if not text.strip():
        raise RuntimeError("Gemini OCR response was empty")
    return text


def _find_line_value(lines: list[str], keywords: tuple[str, ...]) -> str:
    for line in lines:
        lower = line.lower()
        if all(token in lower for token in keywords):
            if ":" in line:
                return line.split(":", 1)[-1].strip()
            return line.strip()
    return ""


def extract_identity(raw_text: str) -> dict[str, str]:
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    email_match = EMAIL_PATTERN.search(raw_text)
    phone_match = PHONE_PATTERN.search(raw_text)
    dob_match = _find_line_value(lines, ("dob",)) or _find_line_value(lines, ("date", "birth"))
    if not dob_match:
        any_date = DATE_PATTERN.search(raw_text)
        dob_match = any_date.group(1) if any_date else ""

    patient_name = _find_line_value(lines, ("patient", "name"))
    if not patient_name and lines:
        # fallback for documents where heading begins with name
        for line in lines[:8]:
            if "patient" in line.lower():
                patient_name = line.split(":")[-1].strip()
                break

    return {
        "patient_name": patient_name,
        "patient_email": email_match.group(0) if email_match else "",
        "patient_phone": phone_match.group(0) if phone_match else "",
        "patient_dob": dob_match,
    }


def parse_lab_report(raw_text: str) -> dict[str, Any]:
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    fields: dict[str, Any] = {
        "tests": [],
        "document_fields": [
            {"key": "lab_name", "value_short": _find_line_value(lines, ("lab", "name"))},
            {"key": "sample_id", "value_short": _find_line_value(lines, ("sample", "id"))},
            {"key": "ordering_doctor", "value_short": _find_line_value(lines, ("doctor",))},
            {"key": "findings_summary", "value_text": ""},
            {"key": "raw_ocr_text", "value_text": raw_text},
        ],
    }

    for line in lines:
        if "patient" in line.lower() and "name" in line.lower():
            fields["patient_name"] = line.split(":")[-1].strip()
        if "date" in line.lower() and "report" in line.lower():
            fields["report_date"] = line.split(":")[-1].strip()
        if "hospital" in line.lower() or "clinic" in line.lower():
            fields["hospital_name"] = line.split(":")[-1].strip()

        match = TEST_LINE_PATTERN.search(line)
        if match:
            fields["tests"].append(
                {
                    "test_name": match.group("test").strip(),
                    "value": match.group("value"),
                    "unit": match.group("unit") or "",
                    "reference_range": match.group("range") or "",
                }
            )

    findings = [f"{t['test_name']}: {t['value']} {t['unit']} (Ref: {t['reference_range']})" for t in fields["tests"]]
    for row in fields["document_fields"]:
        if row["key"] == "findings_summary":
            row["value_text"] = "\n".join(findings)

    total_signals = 2 + len(fields["tests"])
    matched_signals = int("patient_name" in fields) + int("report_date" in fields) + len(fields["tests"])
    confidence = round((matched_signals / max(total_signals, 1)) * 100, 2)

    return {
        "parsed": fields,
        "confidence": confidence,
    }


def parse_key_value_document(raw_text: str, *, document_type: str) -> dict[str, Any]:
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    kv: dict[str, str] = {}
    for line in lines:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        kv[key.strip().lower()] = value.strip()

    fields: dict[str, Any] = {
        "tests": [],
        "patient_name": kv.get("patient name", ""),
        "report_date": kv.get("date", "") or kv.get("report date", ""),
        "hospital_name": kv.get("hospital", "") or kv.get("clinic", ""),
        "doctor_name": kv.get("doctor", "") or kv.get("physician", ""),
        "document_fields": [],
    }

    if document_type == PatientDocument.DocumentType.PRESCRIPTION:
        fields["document_fields"] = [
            {"key": "prescription_date", "value_short": kv.get("prescription date", fields["report_date"])},
            {"key": "diagnosis", "value_text": kv.get("diagnosis", "")},
            {"key": "medications", "value_text": kv.get("medications", "") or kv.get("medicine", "")},
            {"key": "instructions", "value_text": kv.get("instructions", "")},
            {"key": "follow_up", "value_text": kv.get("follow up", "")},
            {"key": "raw_ocr_text", "value_text": raw_text},
        ]
    elif document_type == PatientDocument.DocumentType.DISCHARGE_SUMMARY:
        fields["document_fields"] = [
            {"key": "admission_date", "value_short": kv.get("admission date", "")},
            {"key": "discharge_date", "value_short": kv.get("discharge date", "")},
            {"key": "primary_diagnosis", "value_text": kv.get("diagnosis", "")},
            {"key": "procedures", "value_text": kv.get("procedures", "")},
            {"key": "discharge_medications", "value_text": kv.get("medications", "")},
            {"key": "follow_up_plan", "value_text": kv.get("follow up", "")},
            {"key": "raw_ocr_text", "value_text": raw_text},
        ]
    else:
        fields["document_fields"] = [
            {"key": "document_title", "value_short": lines[0] if lines else ""},
            {"key": "document_date", "value_short": fields["report_date"]},
            {"key": "summary", "value_text": "\n".join(lines[:10])},
            {"key": "raw_ocr_text", "value_text": raw_text},
        ]

    available = [v for v in [fields["patient_name"], fields["report_date"], fields["doctor_name"]] if v]
    confidence = 80.0 if available else 45.0
    return {"parsed": fields, "confidence": confidence}


def parse_document(raw_text: str, document_type: str) -> dict[str, Any]:
    if document_type == PatientDocument.DocumentType.LAB_REPORT:
        return parse_lab_report(raw_text)
    if document_type in {PatientDocument.DocumentType.PRESCRIPTION, PatientDocument.DocumentType.DISCHARGE_SUMMARY}:
        return parse_key_value_document(raw_text, document_type=document_type)
    return parse_key_value_document(raw_text, document_type=PatientDocument.DocumentType.OTHER)


def run_ocr_pipeline(file_path: str, document_type: str) -> dict[str, Any]:
    suffix = Path(file_path).suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}:
        return {
            "raw_text": "",
            "parsed": {"error": "Unsupported format for direct OCR. Upload image formats in v1."},
            "confidence": 0.0,
            "identity": {},
        }

    provider = os.getenv("OCR_PROVIDER", "tesseract").strip().lower()
    if provider == "gemini":
        try:
            raw_text = extract_text_with_gemini(file_path)
        except Exception:
            raw_text = extract_text(file_path)
            provider = "tesseract_fallback"
    else:
        raw_text = extract_text(file_path)

    parsed = parse_document(raw_text, document_type)
    identity = extract_identity(raw_text)
    return {
        "raw_text": raw_text,
        "parsed": parsed["parsed"],
        "confidence": parsed["confidence"],
        "provider": provider,
        "identity": identity,
    }
