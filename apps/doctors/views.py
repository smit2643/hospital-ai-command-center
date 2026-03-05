from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from apps.core.permissions import require_role
from apps.core.services import log_audit
from apps.patients.models import PatientDoctorAssignment
from .models import DoctorProfile


@login_required
def dashboard(request):
    require_role(request.user, request.user.Role.DOCTOR)
    doctor_profile = get_object_or_404(DoctorProfile, user=request.user)
    if not doctor_profile.is_approved:
        return render(request, "doctors/pending_approval.html", {"doctor_profile": doctor_profile})

    assignments = (
        PatientDoctorAssignment.objects.select_related("patient__user")
        .filter(doctor=doctor_profile, is_active=True)
        .order_by("patient__user__full_name")
    )
    return render(request, "doctors/dashboard.html", {"doctor_profile": doctor_profile, "assignments": assignments})


@login_required
def approval_list(request):
    require_role(request.user, request.user.Role.ADMIN)
    pending_profiles = DoctorProfile.objects.select_related("user").filter(
        approval_status=DoctorProfile.ApprovalStatus.PENDING
    )
    return render(request, "doctors/approval_list.html", {"pending_profiles": pending_profiles})


@login_required
def approval_action(request, profile_id: int, decision: str):
    require_role(request.user, request.user.Role.ADMIN)
    profile = get_object_or_404(DoctorProfile, id=profile_id)
    if decision not in {DoctorProfile.ApprovalStatus.APPROVED, DoctorProfile.ApprovalStatus.REJECTED}:
        messages.error(request, "Invalid decision")
        return redirect("doctors:approval_list")

    profile.approval_status = decision
    profile.approved_by = request.user
    profile.approved_at = timezone.now()
    profile.save(update_fields=["approval_status", "approved_by", "approved_at"])

    log_audit(
        actor=request.user,
        action=f"doctor.{decision.lower()}",
        object_type="DoctorProfile",
        object_id=profile.id,
        metadata={"doctor_user_id": profile.user_id},
    )

    messages.success(request, f"Doctor {profile.user.full_name} marked as {decision.lower()}.")
    return redirect("doctors:approval_list")
