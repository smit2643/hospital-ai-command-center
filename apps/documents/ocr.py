import json
import os
import re
import urllib.error
import urllib.request
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pytesseract
from PIL import Image

from .models import PatientDocument
from .schema import get_schema_for_document_type


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
    "patient_dob": ["dob", "date of birth", "birth date"],
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

    dob_text = _kv_lookup(kv, "patient_dob") or _line_alias_lookup(lines, "patient_dob")
    date_match = DATE_PATTERN.search(dob_text)
    dob_match = date_match.group(1) if date_match else ""

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


def _extract_json_from_text(raw: str) -> dict:
    text = (raw or "").strip()
    if not text:
        return {}
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {}
    try:
        return json.loads(text[start : end + 1])
    except Exception:  # noqa: BLE001
        return {}


def _ollama_map_fields(raw_text: str, document_type: str) -> tuple[dict | None, str, str]:
    provider = os.getenv("OCR_LLM_PROVIDER", "ollama").strip().lower()
    if provider != "ollama":
        return None, "", ""

    base_url = os.getenv("OCR_OLLAMA_BASE_URL", "http://ollama:11434").strip().rstrip("/")
    model = os.getenv("OCR_OLLAMA_MODEL", "gpt-oss:120b-cloud").strip()
    fallback_model = os.getenv("OCR_OLLAMA_FALLBACK_MODEL", "qwen2.5:0.5b").strip()
    endpoint = f"{base_url}/api/generate"

    schema = get_schema_for_document_type(document_type)
    schema_keys = [item["key"] for item in schema]
    max_chars = int(os.getenv("OCR_OLLAMA_MAX_CHARS", "8000").strip() or "8000")
    ocr_text = raw_text[:max_chars]

    prompt = (
        "You are a medical document extraction assistant.\n"
        "Return ONLY valid JSON (no markdown fences, no extra text) with exactly these keys:\n"
        '{'
        '"report_date": "YYYY-MM-DD or empty", '
        '"hospital_name": "string", '
        '"doctor_name": "string", '
        '"notes": "string", '
        '"tests": [{"test_name":"", "value":"", "unit":"", "reference_range":""}], '
        '"document_fields": [{"key":"", "value_short":"", "value_text":""}]'
        "}\n"
        "Rules:\n"
        "- Use only the OCR text.\n"
        "- For document_fields, only use keys from this allowed list:\n"
        f"{schema_keys}\n"
        "- If a value is missing, use empty string.\n"
        "- Keep value_short for short values (dates, IDs, short names). Use value_text for paragraphs.\n"
        f"Document type: {document_type}\n"
        f"OCR text:\n{ocr_text}\n"
    )
    num_predict = int(os.getenv("OCR_OLLAMA_NUM_PREDICT", "400").strip() or "400")
    temperature = float(os.getenv("OCR_OLLAMA_TEMPERATURE", "0.1").strip() or "0.1")

    def _call_ollama(*, use_format: bool, compact_prompt: bool = False, model_name: str | None = None) -> tuple[str, str]:
        model_value = model_name or model
        body_obj = {
            "model": model_value,
            "prompt": prompt if not compact_prompt else (
                "Return ONLY valid JSON with keys: "
                "report_date, hospital_name, doctor_name, notes, tests, document_fields. "
                f"Doc type: {document_type}. "
                f"OCR: {ocr_text}"
            ),
            "stream": False,
            "options": {"temperature": temperature, "num_predict": num_predict},
        }
        if use_format:
            body_obj["format"] = "json"
        body = json.dumps(body_obj).encode("utf-8")
        req = urllib.request.Request(endpoint, data=body, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310
                return resp.read().decode("utf-8", errors="ignore"), ""
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            return "", f"Ollama HTTP {exc.code}: {detail[:240]}"
        except urllib.error.URLError as exc:
            reason = str(exc.reason)
            if "Connection refused" in reason or "refused" in reason.lower():
                return "", f"Ollama is not running at {base_url}."
            return "", f"Ollama connection error: {reason[:200]}"
        except Exception as exc:  # noqa: BLE001
            return "", f"Ollama call failed: {exc.__class__.__name__}: {exc}"

    def _parse_response(raw: str) -> tuple[dict, str]:
        if not raw:
            return {}, "empty response"
        envelope = _extract_json_from_text(raw)
        response_text = str(envelope.get("response", "")).strip()
        if not response_text and raw.strip():
            parts = []
            for line in raw.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    parts.append(str(obj.get("response", "")))
                except Exception:  # noqa: BLE001
                    pass
            response_text = "".join(parts).strip()
        if not response_text:
            return {}, "empty response"
        parsed = _extract_json_from_text(response_text)
        if not parsed:
            parsed = _extract_json_from_text(raw)
        if not parsed:
            return {}, "invalid json"
        return parsed, ""

    raw, err = _call_ollama(use_format=True, compact_prompt=False, model_name=model)
    if err:
        return None, model, err
    parsed, parse_err = _parse_response(raw)
    if not parsed:
        # Some cloud models ignore/struggle with the "format" param. Retry without it.
        raw, err = _call_ollama(use_format=False, compact_prompt=False, model_name=model)
        if err:
            return None, model, err
        parsed, parse_err = _parse_response(raw)
    if not parsed:
        # Final fallback: compact prompt, no format.
        raw, err = _call_ollama(use_format=False, compact_prompt=True, model_name=model)
        if err:
            return None, model, err
        parsed, parse_err = _parse_response(raw)
    if not parsed:
        if fallback_model and fallback_model != model:
            raw, err = _call_ollama(use_format=False, compact_prompt=True, model_name=fallback_model)
            if err:
                return None, model, err
            parsed, parse_err = _parse_response(raw)
            if parsed:
                return parsed, fallback_model, ""
        return None, model, f"Ollama response was {parse_err or 'empty'} for model '{model}'."

    parsed.setdefault("document_fields", [])
    parsed.setdefault("tests", [])
    return parsed, model, ""


def _merge_parsed(rule_based: dict[str, Any], llm_parsed: dict[str, Any] | None, document_type: str) -> dict[str, Any]:
    if not llm_parsed:
        return rule_based

    def _normalize_test_row(row: dict[str, Any]) -> dict[str, Any]:
        name = str(row.get("test_name", "") or "").strip()
        value = str(row.get("value", "") or "").strip()
        unit = str(row.get("unit", "") or "").strip()
        ref = str(row.get("reference_range", "") or "").strip()

        if value and not unit:
            match = re.match(r"^(-?\d+(?:\.\d+)?)(?:\s+)([A-Za-zµ/%].+)$", value)
            if match:
                value, unit = match.group(1), match.group(2).strip()

        if unit and len(unit) <= 2 and re.search(r"[A-Za-zµ/%]", value):
            match = re.match(r"^(-?\d+(?:\.\d+)?)(?:\s+)([A-Za-zµ/%].+)$", value)
            if match:
                value, unit = match.group(1), match.group(2).strip()

        if unit == "f" and ref:
            unit = "ful"

        return {"test_name": name, "value": value, "unit": unit, "reference_range": ref}

    def _merge_tests(rule_tests: list[dict[str, Any]], llm_tests: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not rule_tests and not llm_tests:
            return []

        def key_for(name: str) -> str:
            return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", name.lower())).strip()

        rule_norm = {}
        for row in rule_tests:
            norm = key_for(str(row.get("test_name", "")))
            if norm:
                rule_norm[norm] = row

        merged_rows = []
        for row in rule_tests:
            merged_rows.append(_normalize_test_row(row))

        for row in llm_tests:
            normalized = _normalize_test_row(row)
            name_key = key_for(normalized["test_name"])
            if not name_key:
                continue
            if name_key in rule_norm:
                base = _normalize_test_row(rule_norm[name_key])
                if not normalized["value"]:
                    normalized["value"] = base["value"]
                if not normalized["unit"]:
                    normalized["unit"] = base["unit"]
                if not normalized["reference_range"]:
                    normalized["reference_range"] = base["reference_range"]
                # Prefer rule-based row when it has a better unit/value pairing.
                if base["unit"] and len(base["unit"]) > len(normalized["unit"]):
                    normalized["unit"] = base["unit"]
                if base["value"] and re.search(r"[A-Za-zµ/%]", normalized["value"]):
                    normalized["value"] = base["value"]
                continue
            merged_rows.append(normalized)

        return merged_rows

    merged = dict(rule_based)
    for key in ("patient_name", "report_date", "hospital_name", "doctor_name", "notes"):
        value = str(llm_parsed.get(key, "") or "").strip()
        if value:
            merged[key] = value

    llm_tests = llm_parsed.get("tests")
    rule_tests = rule_based.get("tests", [])
    if isinstance(llm_tests, list) or isinstance(rule_tests, list):
        merged["tests"] = _merge_tests(
            rule_tests if isinstance(rule_tests, list) else [],
            llm_tests if isinstance(llm_tests, list) else [],
        )

    schema = get_schema_for_document_type(document_type)
    base_fields = {item.get("key"): item for item in rule_based.get("document_fields", []) if isinstance(item, dict)}
    llm_fields = {item.get("key"): item for item in llm_parsed.get("document_fields", []) if isinstance(item, dict)}

    merged_fields = []
    for spec in schema:
        key = spec["key"]
        incoming = llm_fields.get(key) or base_fields.get(key) or {}
        value_short = str(incoming.get("value_short", "") or "")
        value_text = str(incoming.get("value_text", "") or "")
        merged_fields.append({"key": key, "value_short": value_short, "value_text": value_text})

    merged["document_fields"] = merged_fields
    merged["mapping_provider"] = "ollama"
    merged["mapping_model"] = os.getenv("OCR_OLLAMA_MODEL", "gpt-oss:120b-cloud").strip()
    return merged


def run_ocr_pipeline(file_path: str, document_type: str) -> dict[str, Any]:
    suffix = Path(file_path).suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}:
        return {
            "raw_text": "",
            "parsed": {"error": "Unsupported format for direct OCR. Upload image formats in v1."},
            "confidence": 0.0,
            "identity": {},
        }

    provider = "tesseract"
    raw_text = extract_text(file_path)

    rule_based = parse_document(raw_text, document_type)
    llm_parsed, llm_model, llm_error = _ollama_map_fields(raw_text, document_type)
    parsed = _merge_parsed(rule_based["parsed"], llm_parsed, document_type)
    if llm_parsed and llm_model:
        parsed["mapping_provider"] = "ollama"
        parsed["mapping_model"] = llm_model
    confidence = rule_based.get("confidence", 0.0)
    if llm_parsed:
        confidence = max(confidence, 85.0)
    identity = extract_identity(raw_text)
    return {
        "raw_text": raw_text,
        "parsed": parsed,
        "confidence": confidence,
        "provider": provider,
        "identity": identity,
        "mapping_model": llm_model,
        "mapping_error": llm_error,
    }
