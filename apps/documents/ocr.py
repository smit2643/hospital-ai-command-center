import re
import os
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pytesseract
from PIL import Image


TEST_LINE_PATTERN = re.compile(
    r"(?P<test>[A-Za-z\s\-\(\)]+)\s+(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>[a-zA-Z/%]+)?\s*(?P<range>\d+(?:\.\d+)?\s*[-–]\s*\d+(?:\.\d+)?)?"
)


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
    """
    Optional provider.
    Uses Gemini only when OCR_PROVIDER=gemini and GEMINI_API_KEY is configured.
    Falls back to Tesseract automatically if unavailable.
    """
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


def parse_lab_report(raw_text: str) -> dict[str, Any]:
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    fields: dict[str, Any] = {"tests": []}

    for line in lines:
        if "patient" in line.lower() and "name" in line.lower():
            fields["patient_name"] = line.split(":")[-1].strip()
        if "date" in line.lower() and "report" in line.lower():
            fields["report_date"] = line.split(":")[-1].strip()

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

    total_signals = 2 + len(fields["tests"])
    matched_signals = int("patient_name" in fields) + int("report_date" in fields) + len(fields["tests"])
    confidence = round((matched_signals / max(total_signals, 1)) * 100, 2)

    return {
        "parsed": fields,
        "confidence": confidence,
    }


def run_ocr_pipeline(file_path: str) -> dict[str, Any]:
    suffix = Path(file_path).suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}:
        # Basic v1 implementation supports image OCR only.
        return {
            "raw_text": "",
            "parsed": {"error": "Unsupported format for direct OCR. Upload image formats in v1."},
            "confidence": 0.0,
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
    parsed = parse_lab_report(raw_text)
    return {
        "raw_text": raw_text,
        "parsed": parsed["parsed"],
        "confidence": parsed["confidence"],
        "provider": provider,
    }
