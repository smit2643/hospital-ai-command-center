from django import forms
from apps.accounts.models import User
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
    full_name = forms.CharField(required=False, max_length=255)
    email = forms.EmailField(required=False)
    phone = forms.CharField(required=False, max_length=20)

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and getattr(self.instance, "user", None):
            self.fields["full_name"].initial = self.instance.user.full_name
            self.fields["email"].initial = self.instance.user.email
            self.fields["phone"].initial = self.instance.user.phone

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if not email:
            return email
        qs = User.objects.filter(email=email)
        if self.instance and getattr(self.instance, "user_id", None):
            qs = qs.exclude(id=self.instance.user_id)
        if qs.exists():
            raise forms.ValidationError("This email is already in use.")
        return email

    def save(self, commit=True):
        profile = super().save(commit=commit)
        user = profile.user
        user.full_name = (self.cleaned_data.get("full_name") or user.full_name).strip()
        user.email = (self.cleaned_data.get("email") or user.email).strip().lower()
        user.phone = (self.cleaned_data.get("phone") or user.phone).strip()
        if commit:
            user.save(update_fields=["full_name", "email", "phone"])
        else:
            user.save()
        return profile
