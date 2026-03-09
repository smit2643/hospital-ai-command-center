from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from apps.accounts.forms import PatientRegistrationForm
from apps.accounts.models import User
from apps.core.permissions import doctor_can_access_patient, require_approved_doctor, require_role
from apps.core.services import log_audit
from .forms import AssignmentAdminUpdateForm, AssignmentForm, PatientProfileUpdateForm
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
            return redirect("patients:detail", patient_id=patient.id)
    else:
        form = AssignmentForm()
    return render(request, "patients/assign_doctor.html", {"patient": patient, "form": form})


@login_required
def patient_list(request):
    require_role(request.user, request.user.Role.ADMIN, request.user.Role.DOCTOR)
    require_approved_doctor(request.user)
    if request.user.role == request.user.Role.ADMIN:
        patients = PatientProfile.objects.select_related("user").all().order_by("user__full_name")
    else:
        patients = PatientProfile.objects.select_related("user").filter(
            assignments__doctor__user=request.user, assignments__is_active=True
        )
    return render(request, "patients/list.html", {"patients": patients})


@login_required
def add_patient(request):
    require_role(request.user, request.user.Role.ADMIN)
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
                    profile = PatientProfile.objects.create(
                        user=user,
                        dob=form.cleaned_data.get("dob"),
                        gender=form.cleaned_data.get("gender", ""),
                        blood_group=form.cleaned_data.get("blood_group", ""),
                        marital_status=form.cleaned_data.get("marital_status", ""),
                        occupation=form.cleaned_data.get("occupation", ""),
                        address_line1=form.cleaned_data.get("address_line1", ""),
                        address_line2=form.cleaned_data.get("address_line2", ""),
                        city=form.cleaned_data.get("city", ""),
                        state=form.cleaned_data.get("state", ""),
                        postal_code=form.cleaned_data.get("postal_code", ""),
                        country=form.cleaned_data.get("country", ""),
                        allergies=form.cleaned_data.get("allergies", ""),
                        chronic_conditions=form.cleaned_data.get("chronic_conditions", ""),
                        current_medications=form.cleaned_data.get("current_medications", ""),
                        insurance_provider=form.cleaned_data.get("insurance_provider", ""),
                        insurance_policy_number=form.cleaned_data.get("insurance_policy_number", ""),
                        emergency_contact_name=form.cleaned_data.get("emergency_contact_name", ""),
                        emergency_contact_relation=form.cleaned_data.get("emergency_contact_relation", ""),
                        emergency_contact=form.cleaned_data.get("emergency_contact", ""),
                    )
                    log_audit(
                        actor=request.user,
                        action="patient.created_by_admin",
                        object_type="PatientProfile",
                        object_id=profile.id,
                        metadata={"patient_user_id": user.id},
                    )
                messages.success(request, "Patient created successfully.")
                return redirect("patients:list")
            except IntegrityError:
                form.add_error(None, "Unable to create patient due to conflicting data.")
    else:
        form = PatientRegistrationForm()
    return render(request, "patients/add_patient.html", {"form": form})


@login_required
def detail(request, patient_id: int):
    patient = get_object_or_404(PatientProfile.objects.select_related("user"), id=patient_id)
    if not doctor_can_access_patient(request.user, patient):
        require_role(request.user, request.user.Role.ADMIN)
    assignments = patient.assignments.select_related("doctor__user", "assigned_by").all()
    documents_qs = patient.documents.all()

    if request.method == "POST":
        require_role(request.user, request.user.Role.ADMIN)
        form = PatientProfileUpdateForm(request.POST, instance=patient)
        if form.is_valid():
            form.save()
            messages.success(request, "Patient profile updated.")
            return redirect("patients:detail", patient_id=patient.id)
    else:
        form = PatientProfileUpdateForm(instance=patient)

    return render(
        request,
        "patients/detail.html",
        {
            "patient": patient,
            "assignments": assignments,
            "documents_count": documents_qs.count(),
            "signed_documents_count": documents_qs.filter(signature_requests__status="SIGNED").distinct().count(),
            "form": form,
            "can_edit": request.user.role == request.user.Role.ADMIN,
        },
    )


@login_required
def assignment_edit(request, assignment_id: int):
    require_role(request.user, request.user.Role.ADMIN)
    assignment = get_object_or_404(PatientDoctorAssignment.objects.select_related("patient__user", "doctor__user"), id=assignment_id)

    if request.method == "POST":
        form = AssignmentAdminUpdateForm(request.POST, instance=assignment)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.assigned_by = request.user
            updated.save()
            messages.success(request, "Assignment updated.")
            return redirect("patients:detail", patient_id=assignment.patient_id)
    else:
        form = AssignmentAdminUpdateForm(instance=assignment)

    return render(
        request,
        "patients/assignment_edit.html",
        {"assignment": assignment, "form": form},
    )


@login_required
def assignment_delete(request, assignment_id: int):
    require_role(request.user, request.user.Role.ADMIN)
    assignment = get_object_or_404(PatientDoctorAssignment.objects.select_related("patient"), id=assignment_id)
    patient_id = assignment.patient_id
    if request.method == "POST":
        assignment.delete()
        messages.success(request, "Assignment removed.")
        return redirect("patients:detail", patient_id=patient_id)
    return render(request, "patients/assignment_delete.html", {"assignment": assignment})
