from django import forms
from apps.doctors.models import DoctorProfile
from .models import PatientDoctorAssignment, PatientProfile


class AssignmentForm(forms.ModelForm):
    doctor = forms.ModelChoiceField(
        queryset=DoctorProfile.objects.filter(approval_status=DoctorProfile.ApprovalStatus.APPROVED),
        empty_label=None,
    )

    class Meta:
        model = PatientDoctorAssignment
        fields = ["doctor"]


class PatientProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = PatientProfile
        fields = ["dob", "gender", "blood_group", "emergency_contact"]
        widgets = {
            "dob": forms.DateInput(attrs={"type": "date"}),
        }
