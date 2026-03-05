from rest_framework import serializers
from .models import DoctorProfile


class DoctorProfileSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source="user.full_name", read_only=True)

    class Meta:
        model = DoctorProfile
        fields = [
            "id",
            "user",
            "doctor_name",
            "specialization",
            "license_number",
            "years_experience",
            "approval_status",
            "approved_by",
            "approved_at",
            "created_at",
        ]
        read_only_fields = ["approval_status", "approved_by", "approved_at", "created_at"]
