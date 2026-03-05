from django.contrib import admin
from .models import DoctorProfile


@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "specialization", "approval_status", "approved_at")
    list_filter = ("approval_status", "specialization")
    search_fields = ("user__email", "user__full_name", "license_number")
