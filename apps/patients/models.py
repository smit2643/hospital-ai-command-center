from django.conf import settings
from django.db import models
from apps.doctors.models import DoctorProfile


class PatientProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="patient_profile")
    dob = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, blank=True)
    blood_group = models.CharField(max_length=10, blank=True)
    marital_status = models.CharField(max_length=20, blank=True)
    occupation = models.CharField(max_length=120, blank=True)
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=80, blank=True)
    state = models.CharField(max_length=80, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=80, blank=True)
    allergies = models.TextField(blank=True)
    chronic_conditions = models.TextField(blank=True)
    current_medications = models.TextField(blank=True)
    insurance_provider = models.CharField(max_length=120, blank=True)
    insurance_policy_number = models.CharField(max_length=120, blank=True)
    emergency_contact_name = models.CharField(max_length=120, blank=True)
    emergency_contact_relation = models.CharField(max_length=60, blank=True)
    emergency_contact = models.CharField(max_length=60, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.user.full_name


class PatientDoctorAssignment(models.Model):
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name="assignments")
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name="assignments")
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="patient_assignments_created",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("patient", "doctor")

    def __str__(self) -> str:
        return f"{self.patient} -> {self.doctor.user.full_name}"
