from django.test import TestCase
from apps.accounts.models import User
from apps.patients.models import PatientProfile

from .models import PatientDocument
from .ocr import parse_lab_report
from .services import upsert_extraction_from_parsed


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

    def test_parse_lab_report_with_ocr_style_key_noise(self):
        text = """
        CITY CARE MULTISPECIALTY HOSPITAL
        Patient Name Rohan Shah
        Doctor Nane Dr. Aria Menon
        Hospital Name City Care Multispecialty Hospital
        Report Date 2026-03-05
        Hemoglobin 13.5 g/dL 12.0-16.0
        """
        result = parse_lab_report(text)
        parsed = result["parsed"]
        self.assertEqual(parsed["doctor_name"], "Dr. Aria Menon")
        self.assertEqual(parsed["hospital_name"], "City Care Multispecialty Hospital")

    def test_upsert_maps_doctor_hospital_from_document_fields(self):
        doctor = User.objects.create_user(
            email="doc-map@example.com",
            full_name="Doc Map",
            role=User.Role.DOCTOR,
            password="Secret123!",
        )
        patient_user = User.objects.create_user(
            email="pat-map@example.com",
            full_name="Pat Map",
            role=User.Role.PATIENT,
            password="Secret123!",
        )
        patient = PatientProfile.objects.create(user=patient_user)
        document = PatientDocument.objects.create(
            patient=patient,
            uploaded_by=doctor,
            file="patients/1/documents/map.png",
            document_type=PatientDocument.DocumentType.LAB_REPORT,
        )
        parsed = {
            "report_date": "2026-03-05",
            "hospital_name": "",
            "doctor_name": "",
            "notes": "",
            "document_fields": [
                {"key": "lab_name", "value_short": "City Care Multispecialty Hospital"},
                {"key": "ordering_doctor", "value_short": "Dr. Aria Menon"},
                {"key": "findings_summary", "value_text": "Mild iron deficiency trend."},
            ],
            "tests": [],
        }
        extraction = upsert_extraction_from_parsed(document, parsed, raw_text="x")
        self.assertEqual(extraction.hospital_name, "City Care Multispecialty Hospital")
        self.assertEqual(extraction.doctor_name, "Dr. Aria Menon")
        self.assertEqual(extraction.notes, "Mild iron deficiency trend.")
