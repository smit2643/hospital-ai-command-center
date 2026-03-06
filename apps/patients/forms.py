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


class AssignmentAdminUpdateForm(forms.ModelForm):
    doctor = forms.ModelChoiceField(
        queryset=DoctorProfile.objects.filter(approval_status=DoctorProfile.ApprovalStatus.APPROVED),
        empty_label=None,
    )

    class Meta:
        model = PatientDoctorAssignment
        fields = ["doctor", "is_active"]


class PatientProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = PatientProfile
        fields = [
            "dob",
            "gender",
            "blood_group",
            "marital_status",
            "occupation",
            "address_line1",
            "address_line2",
            "city",
            "state",
            "postal_code",
            "country",
            "allergies",
            "chronic_conditions",
            "current_medications",
            "insurance_provider",
            "insurance_policy_number",
            "emergency_contact_name",
            "emergency_contact_relation",
            "emergency_contact",
        ]
        widgets = {
            "dob": forms.DateInput(attrs={"type": "date"}),
            "allergies": forms.Textarea(attrs={"rows": 2}),
            "chronic_conditions": forms.Textarea(attrs={"rows": 2}),
            "current_medications": forms.Textarea(attrs={"rows": 2}),
        }
