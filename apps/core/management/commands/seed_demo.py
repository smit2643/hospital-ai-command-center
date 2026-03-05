from datetime import date

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import User
from apps.doctors.models import DoctorProfile
from apps.patients.models import PatientDoctorAssignment, PatientProfile


class Command(BaseCommand):
    help = "Seed demo users and assignments for presentation"

    def handle(self, *args, **options):
        admin_email = "admin@hospitalai.local"
        doctor_email = "doctor@hospitalai.local"
        patient_email = "patient@hospitalai.local"
        password = "DemoPass@123"

        admin, created = User.objects.get_or_create(
            email=admin_email,
            defaults={
                "full_name": "Platform Admin",
                "phone": "9999990001",
                "role": User.Role.ADMIN,
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if created:
            admin.set_password(password)
            admin.save(update_fields=["password"])

        doctor_user, created = User.objects.get_or_create(
            email=doctor_email,
            defaults={
                "full_name": "Dr. Aria Menon",
                "phone": "9999990002",
                "role": User.Role.DOCTOR,
            },
        )
        if created:
            doctor_user.set_password(password)
            doctor_user.save(update_fields=["password"])

        doctor_profile, _ = DoctorProfile.objects.get_or_create(
            user=doctor_user,
            defaults={
                "specialization": "Cardiology",
                "license_number": "LIC-CARD-2026-001",
                "years_experience": 8,
                "approval_status": DoctorProfile.ApprovalStatus.APPROVED,
                "approved_by": admin,
                "approved_at": timezone.now(),
            },
        )
        if doctor_profile.approval_status != DoctorProfile.ApprovalStatus.APPROVED:
            doctor_profile.approval_status = DoctorProfile.ApprovalStatus.APPROVED
            doctor_profile.approved_by = admin
            doctor_profile.approved_at = timezone.now()
            doctor_profile.save(update_fields=["approval_status", "approved_by", "approved_at"])

        patient_user, created = User.objects.get_or_create(
            email=patient_email,
            defaults={
                "full_name": "Rohan Shah",
                "phone": "9999990003",
                "role": User.Role.PATIENT,
            },
        )
        if created:
            patient_user.set_password(password)
            patient_user.save(update_fields=["password"])

        patient_profile, _ = PatientProfile.objects.get_or_create(
            user=patient_user,
            defaults={
                "dob": date(1999, 5, 14),
                "gender": "Male",
                "blood_group": "B+",
                "emergency_contact": "9876543210",
            },
        )

        PatientDoctorAssignment.objects.get_or_create(
            patient=patient_profile,
            doctor=doctor_profile,
            defaults={"assigned_by": admin, "is_active": True},
        )

        self.stdout.write(self.style.SUCCESS("Demo seed completed."))
        self.stdout.write("Credentials:")
        self.stdout.write(f"  Admin:   {admin_email} / {password}")
        self.stdout.write(f"  Doctor:  {doctor_email} / {password}")
        self.stdout.write(f"  Patient: {patient_email} / {password}")
