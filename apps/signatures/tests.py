from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from apps.accounts.models import User
from apps.doctors.models import DoctorProfile
from apps.patients.models import PatientProfile
from apps.documents.models import PatientDocument
from .models import SignatureRequest
from .services import sign_request_expired


class SignatureTests(TestCase):
    def test_expiry_check(self):
        doctor = User.objects.create_user(
            email="doc2@example.com", full_name="Doc", role=User.Role.DOCTOR, password="Secret123!"
        )
        DoctorProfile.objects.create(user=doctor, specialization="General", license_number="LIC-2", years_experience=2)
        patient_user = User.objects.create_user(
            email="pat2@example.com", full_name="Pat", role=User.Role.PATIENT, password="Secret123!"
        )
        patient = PatientProfile.objects.create(user=patient_user)
        document = PatientDocument.objects.create(patient=patient, uploaded_by=doctor, file="patients/1/documents/x.png")
        req = SignatureRequest.objects.create(
            document=document,
            requester=doctor,
            signer_email="pat2@example.com",
            expires_at=timezone.now() - timedelta(hours=1),
        )
        self.assertTrue(sign_request_expired(req))
