from django.test import TestCase
from django.utils import timezone
from apps.accounts.models import User
from .models import DoctorProfile


class DoctorModelTests(TestCase):
    def test_approval_state(self):
        admin = User.objects.create_user(
            email="admin@example.com", full_name="Admin", role=User.Role.ADMIN, password="Secret123!", is_staff=True
        )
        doctor_user = User.objects.create_user(
            email="doc@example.com", full_name="Doctor", role=User.Role.DOCTOR, password="Secret123!"
        )
        profile = DoctorProfile.objects.create(
            user=doctor_user,
            specialization="Cardiology",
            license_number="LIC-1",
            years_experience=5,
        )
        profile.approval_status = DoctorProfile.ApprovalStatus.APPROVED
        profile.approved_by = admin
        profile.approved_at = timezone.now()
        profile.save()
        self.assertTrue(profile.is_approved)
