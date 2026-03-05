import re
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

    raw_text = extract_text(file_path)
    parsed = parse_lab_report(raw_text)
    return {
        "raw_text": raw_text,
        "parsed": parsed["parsed"],
        "confidence": parsed["confidence"],
    }
