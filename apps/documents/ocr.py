import os
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pytesseract
from PIL import Image

from .models import PatientDocument


EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_PATTERN = re.compile(r"(?:\+?\d{1,3}[\s-]?)?(?:\d[\s-]?){10,14}\d")
DATE_PATTERN = re.compile(r"\b(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\d{2}-\d{2}-\d{4})\b")
REF_RANGE_PATTERN = re.compile(r"(?P<range>\d+(?:\.\d+)?\s*[-–]\s*\d+(?:\.\d+)?)$")
NUMERIC_TOKEN_PATTERN = re.compile(r"^\d+(?:\.\d+)?$")


FIELD_ALIASES = {
    "patient_name": ["patient name", "name"],
    "patient_email": ["patient email", "email", "mail"],
    "patient_phone": ["patient phone", "phone", "mobile", "contact"],
    "patient_id": ["patient id", "uhid", "mrn", "id"],
    "doctor_name": ["doctor name", "doctor", "physician", "consultant"],
    "hospital_name": ["hospital name", "hospital", "clinic"],
    "report_date": ["report date", "date", "test date"],
    "clinical_note": ["clinical note", "note", "remarks", "comment"],
    "lab_name": ["lab name", "laboratory", "pathology department"],
}


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


def _normalize_key(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9\s]", " ", value.lower())
    return " ".join(cleaned.split())


def _extract_key_values(lines: list[str]) -> dict[str, str]:
    kv = {}
    for line in lines:
        raw = line.strip()
        if not raw:
            continue
        if ":" in raw:
            key, value = raw.split(":", 1)
        elif " - " in raw and len(raw.split(" - ", 1)[0].split()) <= 5:
            key, value = raw.split(" - ", 1)
        else:
            continue
        norm_key = _normalize_key(key)
        kv[norm_key] = value.strip()
    return kv


def _kv_lookup(kv: dict[str, str], logical_key: str) -> str:
    aliases = FIELD_ALIASES.get(logical_key, [logical_key])
    for alias in aliases:
        for key, value in kv.items():
            if alias in key:
                return value
    return ""


def _line_alias_lookup(lines: list[str], logical_key: str) -> str:
    aliases = sorted(FIELD_ALIASES.get(logical_key, [logical_key]), key=len, reverse=True)
    for alias in aliases:
        alias_regex = re.sub(r"\s+", r"\\s+", re.escape(alias))
        if " " in alias:
            pattern = re.compile(rf"^\s*{alias_regex}\s*[:\-]?\s*(.+)$", re.IGNORECASE)
        else:
            # For single-token aliases, require explicit delimiter to avoid false positives.
            pattern = re.compile(rf"^\s*{alias_regex}\s*[:\-]\s*(.+)$", re.IGNORECASE)
        for line in lines:
            match = pattern.match(line.strip())
            if match and match.group(1).strip():
                return match.group(1).strip()

    # OCR typo-tolerant fallback for keys like "Doctor Nane"
    for line in lines:
        raw = line.strip()
        if not raw:
            continue
        if ":" in raw:
            key_part, value_part = raw.split(":", 1)
        else:
            pieces = raw.split()
            if len(pieces) < 3:
                continue
            key_part = " ".join(pieces[:2])
            value_part = " ".join(pieces[2:])
        key_norm = _normalize_key(key_part)
        for alias in aliases:
            ratio = SequenceMatcher(None, key_norm, _normalize_key(alias)).ratio()
            if ratio >= 0.72 and value_part.strip():
                return value_part.strip()
    return ""


def _find_line_value(lines: list[str], keywords: tuple[str, ...]) -> str:
    for line in lines:
        lower = line.lower()
        if all(token in lower for token in keywords):
            if ":" in line:
                return line.split(":", 1)[-1].strip()
            return line.strip()
    return ""


def _parse_test_line(line: str) -> dict[str, str] | None:
    working = line.strip()
    if not working or ":" in working:
        return None
    lowered = working.lower()
    if "test name" in lowered and "reference" in lowered:
        return None

    ref_range = ""
    range_match = REF_RANGE_PATTERN.search(working)
    if range_match:
        ref_range = range_match.group("range").strip()
        working = working[: range_match.start()].strip()

    tokens = working.split()
    if len(tokens) < 2:
        return None

    value_idx = -1
    for idx, token in enumerate(tokens):
        if NUMERIC_TOKEN_PATTERN.match(token):
            value_idx = idx
            break

    if value_idx <= 0:
        return None

    test_name = " ".join(tokens[:value_idx]).strip()
    value = tokens[value_idx]
    unit = " ".join(tokens[value_idx + 1 :]).strip()
    if not test_name:
        return None

    return {
        "test_name": test_name,
        "value": value,
        "unit": unit,
        "reference_range": ref_range,
    }


def _find_facility_name(lines: list[str]) -> str:
    for line in lines[:8]:
        lower = line.lower()
        if any(token in lower for token in ("hospital", "institute", "clinic", "medical center", "health center")):
            return line.strip()
    return ""


def _extract_prescription_blocks(lines: list[str]) -> tuple[str, str, str]:
    medications = []
    advice_lines = []
    follow_up = ""
    in_rx = False

    for line in lines:
        stripped = line.strip()
        lower = stripped.lower()
        if not stripped:
            continue

        if lower.startswith("rx") or lower == "rx":
            in_rx = True
            continue

        if lower.startswith("advice"):
            in_rx = False
            advice_value = stripped.split(":", 1)[-1].strip() if ":" in stripped else stripped
            if advice_value:
                advice_lines.append(advice_value)
            follow_match = re.search(r"(follow\s*up[^.,;]*)", advice_value, flags=re.IGNORECASE)
            if follow_match and not follow_up:
                follow_up = follow_match.group(1).strip()
            continue

        if "follow up" in lower and not follow_up:
            follow_up = stripped.split(":", 1)[-1].strip() if ":" in stripped else stripped

        if in_rx:
            item = re.sub(r"^\d+\)\s*", "", stripped)
            if item:
                medications.append(item)

    return ("\n".join(medications).strip(), "\n".join(advice_lines).strip(), follow_up.strip())


def extract_identity(raw_text: str) -> dict[str, str]:
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    kv = _extract_key_values(lines)

    email_match = EMAIL_PATTERN.search(raw_text)
    phone_match = PHONE_PATTERN.search(raw_text)

    dob_match = _find_line_value(lines, ("dob",)) or _find_line_value(lines, ("date", "birth"))
    if not dob_match:
        any_date = DATE_PATTERN.search(raw_text)
        dob_match = any_date.group(1) if any_date else ""

    patient_name = _kv_lookup(kv, "patient_name") or _line_alias_lookup(lines, "patient_name") or _find_line_value(lines, ("patient", "name"))

    return {
        "patient_name": patient_name,
        "patient_email": _kv_lookup(kv, "patient_email") or (email_match.group(0) if email_match else ""),
        "patient_phone": _kv_lookup(kv, "patient_phone") or (phone_match.group(0) if phone_match else ""),
        "patient_dob": dob_match,
    }


def parse_lab_report(raw_text: str) -> dict[str, Any]:
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    kv = _extract_key_values(lines)

    tests = []
    for line in lines:
        parsed = _parse_test_line(line)
        if parsed:
            tests.append(parsed)

    clinical_note = _kv_lookup(kv, "clinical_note") or _line_alias_lookup(lines, "clinical_note")
    patient_name = _kv_lookup(kv, "patient_name") or _line_alias_lookup(lines, "patient_name")
    report_date = _kv_lookup(kv, "report_date") or _line_alias_lookup(lines, "report_date")
    hospital_name = _kv_lookup(kv, "hospital_name") or _line_alias_lookup(lines, "hospital_name")
    doctor_name = _kv_lookup(kv, "doctor_name") or _line_alias_lookup(lines, "doctor_name")
    patient_id = _kv_lookup(kv, "patient_id") or _line_alias_lookup(lines, "patient_id")

    if not hospital_name and lines:
        for line in lines[:4]:
            if "hospital" in line.lower() or "clinic" in line.lower():
                hospital_name = line
                break

    if not report_date:
        date_match = DATE_PATTERN.search(raw_text)
        report_date = date_match.group(1) if date_match else ""

    findings = [f"{t['test_name']}: {t['value']} {t['unit']} (Ref: {t['reference_range']})".strip() for t in tests]
    if clinical_note:
        findings.append(f"Clinical Note: {clinical_note}")

    fields: dict[str, Any] = {
        "tests": tests,
        "patient_name": patient_name,
        "report_date": report_date,
        "hospital_name": hospital_name,
        "doctor_name": doctor_name,
        "notes": clinical_note,
        "document_fields": [
            {"key": "lab_name", "value_short": _kv_lookup(kv, "lab_name") or _line_alias_lookup(lines, "lab_name") or hospital_name},
            {"key": "sample_id", "value_short": patient_id},
            {"key": "ordering_doctor", "value_short": doctor_name},
            {"key": "findings_summary", "value_text": "\n".join(findings)},
            {"key": "raw_ocr_text", "value_text": raw_text},
        ],
    }

    total_signals = 5 + len(tests)
    matched_signals = sum(
        [
            int(bool(patient_name)),
            int(bool(report_date)),
            int(bool(hospital_name)),
            int(bool(doctor_name)),
            int(bool(patient_id)),
            len(tests),
        ]
    )
    confidence = round((matched_signals / max(total_signals, 1)) * 100, 2)

    return {"parsed": fields, "confidence": confidence}


def parse_key_value_document(raw_text: str, *, document_type: str) -> dict[str, Any]:
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    kv = _extract_key_values(lines)

    patient_name = _kv_lookup(kv, "patient_name") or _line_alias_lookup(lines, "patient_name")
    report_date = _kv_lookup(kv, "report_date") or _line_alias_lookup(lines, "report_date")
    hospital_name = _kv_lookup(kv, "hospital_name") or _line_alias_lookup(lines, "hospital_name")
    doctor_name = _kv_lookup(kv, "doctor_name") or _line_alias_lookup(lines, "doctor_name")
    if not hospital_name:
        hospital_name = _find_facility_name(lines)
    if not doctor_name:
        for line in lines:
            if line.strip().lower().startswith("dr."):
                doctor_name = line.strip()
                break

    fields: dict[str, Any] = {
        "tests": [],
        "patient_name": patient_name,
        "report_date": report_date,
        "hospital_name": hospital_name,
        "doctor_name": doctor_name,
        "notes": _kv_lookup(kv, "clinical_note") or _line_alias_lookup(lines, "clinical_note"),
        "document_fields": [],
    }

    if document_type == PatientDocument.DocumentType.PRESCRIPTION:
        rx_text, advice_text, follow_up_text = _extract_prescription_blocks(lines)
        fields["document_fields"] = [
            {"key": "prescription_date", "value_short": _kv_lookup(kv, "prescription_date") or report_date},
            {"key": "diagnosis", "value_text": kv.get("diagnosis", "") or kv.get("provisional diagnosis", "")},
            {"key": "medications", "value_text": kv.get("medications", "") or kv.get("medicine", "") or rx_text},
            {"key": "instructions", "value_text": kv.get("instructions", "") or advice_text},
            {"key": "follow_up", "value_text": kv.get("follow up", "") or follow_up_text},
            {"key": "raw_ocr_text", "value_text": raw_text},
        ]
        if not fields["notes"]:
            fields["notes"] = advice_text
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
            {"key": "document_date", "value_short": report_date},
            {"key": "summary", "value_text": "\n".join(lines[:20])},
            {"key": "raw_ocr_text", "value_text": raw_text},
        ]

    available = [v for v in [patient_name, report_date, doctor_name, hospital_name] if v]
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
