from django.contrib import admin
from .models import PatientDoctorAssignment, PatientProfile


@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "blood_group", "emergency_contact")
    search_fields = ("user__full_name", "user__email")


@admin.register(PatientDoctorAssignment)
class PatientDoctorAssignmentAdmin(admin.ModelAdmin):
    list_display = ("patient", "doctor", "is_active", "assigned_by", "created_at")
    list_filter = ("is_active",)
