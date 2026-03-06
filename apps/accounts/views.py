from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.core.services import log_audit
from apps.doctors.models import DoctorProfile
from apps.patients.models import PatientProfile

from .forms import DoctorRegistrationForm, EmailAuthenticationForm, PatientRegistrationForm
from .models import User


class UserLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = EmailAuthenticationForm


@require_http_methods(["GET", "POST"])
def user_logout(request):
    if request.user.is_authenticated:
        log_audit(actor=request.user, action="auth.logout", object_type="User", object_id=request.user.id)
    logout(request)
    return redirect("core:home")


def register_doctor(request):
    if request.method == "POST":
        form = DoctorRegistrationForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
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
            except IntegrityError:
                form.add_error(None, "Unable to register doctor due to conflicting data. Please verify email/license.")
    else:
        form = DoctorRegistrationForm()
    return render(request, "accounts/register_doctor.html", {"form": form})


def register_patient(request):
    if request.method == "POST":
        form = PatientRegistrationForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
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
                    log_audit(actor=user, action="patient.registered", object_type="User", object_id=user.id)
                login(request, user)
                return redirect("patients:dashboard")
            except IntegrityError:
                form.add_error(None, "Unable to register patient due to conflicting data. Please verify details.")
    else:
        form = PatientRegistrationForm()
    return render(request, "accounts/register_patient.html", {"form": form})
