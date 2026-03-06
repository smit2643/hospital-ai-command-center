from django.test import TestCase
from .ocr import parse_lab_report


class OCRParserTests(TestCase):
    def test_parse_lab_report(self):
        text = """
        CITY CARE MULTISPECIALTY HOSPITAL
        Pathology Department - Laboratory Report
        Patient Name: Rohan Shah
        Patient ID: CCMH-PT-2026-0091
        Doctor Name: Dr. Aria Menon
        Hospital Name: City Care Multispecialty Hospital
        Report Date: 2026-03-05
        Test Name Value Unit Reference Range
        Hemoglobin 13.5 g/dL 12.0-16.0
        WBC Count 7800 ful 4000-11000
        Platelet Count 2.7 lakh/uL 1.5-4.5
        Clinical Note: Mild iron deficiency trend. Continue diet plan and hydration.
        """
        result = parse_lab_report(text)
        parsed = result["parsed"]
        self.assertEqual(parsed["patient_name"], "Rohan Shah")
        self.assertEqual(parsed["doctor_name"], "Dr. Aria Menon")
        self.assertEqual(parsed["hospital_name"], "City Care Multispecialty Hospital")
        self.assertGreaterEqual(len(parsed["tests"]), 3)
        field_map = {item["key"]: item for item in parsed["document_fields"]}
        self.assertEqual(field_map["sample_id"]["value_short"], "CCMH-PT-2026-0091")
        self.assertIn("Clinical Note", field_map["findings_summary"]["value_text"])
        self.assertGreaterEqual(result["confidence"], 50)
