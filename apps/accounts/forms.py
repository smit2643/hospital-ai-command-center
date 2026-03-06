from django import forms
from django.contrib.auth.forms import AuthenticationForm
from apps.doctors.models import DoctorProfile
from .models import User


class BaseRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ["full_name", "email", "phone", "password"]


class DoctorRegistrationForm(BaseRegistrationForm):
    specialization = forms.CharField(max_length=120)
    license_number = forms.CharField(max_length=120)
    years_experience = forms.IntegerField(min_value=0)

    def clean_license_number(self):
        license_number = self.cleaned_data["license_number"].strip()
        if DoctorProfile.objects.filter(license_number__iexact=license_number).exists():
            raise forms.ValidationError("A doctor with this license number is already registered.")
        return license_number


class PatientRegistrationForm(BaseRegistrationForm):
    dob = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    gender = forms.CharField(max_length=20, required=False)
    blood_group = forms.CharField(max_length=10, required=False)
    emergency_contact = forms.CharField(max_length=60, required=False)


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(label="Email")
