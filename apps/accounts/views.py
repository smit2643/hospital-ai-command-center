from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render

from apps.core.services import log_audit
from apps.doctors.models import DoctorProfile
from apps.patients.models import PatientProfile

from .forms import DoctorRegistrationForm, EmailAuthenticationForm, PatientRegistrationForm
from .models import User


class UserLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = EmailAuthenticationForm


class UserLogoutView(LogoutView):
    next_page = "accounts:login"


def register_doctor(request):
    if request.method == "POST":
        form = DoctorRegistrationForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                email=form.cleaned_data["email"],
                full_name=form.cleaned_data["full_name"],
                phone=form.cleaned_data["phone"],
                password=form.cleaned_data["password"],
                role=User.Role.DOCTOR,
            )
            DoctorProfile.objects.create(
                user=user,
                specialization=form.cleaned_data["specialization"],
                license_number=form.cleaned_data["license_number"],
                years_experience=form.cleaned_data["years_experience"],
            )
            log_audit(actor=user, action="doctor.registered", object_type="User", object_id=user.id)
            messages.success(request, "Doctor registration submitted. Wait for admin approval.")
            return redirect("accounts:login")
    else:
        form = DoctorRegistrationForm()
    return render(request, "accounts/register_doctor.html", {"form": form})


def register_patient(request):
    if request.method == "POST":
        form = PatientRegistrationForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                email=form.cleaned_data["email"],
                full_name=form.cleaned_data["full_name"],
                phone=form.cleaned_data["phone"],
                password=form.cleaned_data["password"],
                role=User.Role.PATIENT,
            )
            PatientProfile.objects.create(
                user=user,
                dob=form.cleaned_data.get("dob"),
                gender=form.cleaned_data.get("gender", ""),
                blood_group=form.cleaned_data.get("blood_group", ""),
                emergency_contact=form.cleaned_data.get("emergency_contact", ""),
            )
            login(request, user)
            log_audit(actor=user, action="patient.registered", object_type="User", object_id=user.id)
            return redirect("patients:dashboard")
    else:
        form = PatientRegistrationForm()
    return render(request, "accounts/register_patient.html", {"form": form})
