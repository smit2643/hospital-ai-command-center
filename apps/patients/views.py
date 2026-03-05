from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from apps.core.permissions import doctor_can_access_patient, require_role
from apps.core.services import log_audit
from .forms import AssignmentForm, PatientProfileUpdateForm
from .models import PatientDoctorAssignment, PatientProfile


@login_required
def dashboard(request):
    require_role(request.user, request.user.Role.PATIENT)
    profile = get_object_or_404(PatientProfile, user=request.user)
    assignments = profile.assignments.select_related("doctor__user").filter(is_active=True)

    if request.method == "POST":
        form = PatientProfileUpdateForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated")
            return redirect("patients:dashboard")
    else:
        form = PatientProfileUpdateForm(instance=profile)

    return render(
        request,
        "patients/dashboard.html",
        {"profile": profile, "assignments": assignments, "form": form},
    )


@login_required
def assign_doctor(request, patient_id: int):
    require_role(request.user, request.user.Role.ADMIN)
    patient = get_object_or_404(PatientProfile, id=patient_id)
    if request.method == "POST":
        form = AssignmentForm(request.POST)
        if form.is_valid():
            assignment, _created = PatientDoctorAssignment.objects.update_or_create(
                patient=patient,
                doctor=form.cleaned_data["doctor"],
                defaults={"assigned_by": request.user, "is_active": True},
            )
            log_audit(
                actor=request.user,
                action="patient.assigned_doctor",
                object_type="PatientDoctorAssignment",
                object_id=assignment.id,
                metadata={"patient_id": patient.id, "doctor_profile_id": assignment.doctor_id},
            )
            messages.success(request, "Doctor assigned")
            return redirect("patients:list")
    else:
        form = AssignmentForm()
    return render(request, "patients/assign_doctor.html", {"patient": patient, "form": form})


@login_required
def patient_list(request):
    require_role(request.user, request.user.Role.ADMIN, request.user.Role.DOCTOR)
    if request.user.role == request.user.Role.ADMIN:
        patients = PatientProfile.objects.select_related("user").all().order_by("user__full_name")
    else:
        patients = PatientProfile.objects.select_related("user").filter(
            assignments__doctor__user=request.user, assignments__is_active=True
        )
    return render(request, "patients/list.html", {"patients": patients})


@login_required
def detail(request, patient_id: int):
    patient = get_object_or_404(PatientProfile.objects.select_related("user"), id=patient_id)
    if not doctor_can_access_patient(request.user, patient):
        require_role(request.user, request.user.Role.ADMIN)
    return render(request, "patients/detail.html", {"patient": patient})
