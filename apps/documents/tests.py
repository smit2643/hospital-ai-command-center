from django.test import TestCase
from .ocr import parse_lab_report


class OCRParserTests(TestCase):
    def test_parse_lab_report(self):
        text = """
        Patient Name: John Doe
        Report Date: 2026-03-01
        Hemoglobin 13.5 g/dL 12.0-16.0
        """
        result = parse_lab_report(text)
        self.assertIn("patient_name", result["parsed"])
        self.assertGreaterEqual(result["confidence"], 50)
