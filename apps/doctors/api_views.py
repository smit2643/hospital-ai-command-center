from rest_framework import permissions, response, status, views
from django.shortcuts import get_object_or_404
from django.utils import timezone
from apps.core.services import log_audit
from .models import DoctorProfile
from .serializers import DoctorProfileSerializer


class PendingDoctorListAPI(views.APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        queryset = DoctorProfile.objects.select_related("user").filter(
            approval_status=DoctorProfile.ApprovalStatus.PENDING
        )
        return response.Response(DoctorProfileSerializer(queryset, many=True).data)


class DoctorApprovalAPI(views.APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, profile_id: int):
        decision = request.data.get("decision", "").upper()
        if decision not in {DoctorProfile.ApprovalStatus.APPROVED, DoctorProfile.ApprovalStatus.REJECTED}:
            return response.Response({"detail": "Invalid decision"}, status=status.HTTP_400_BAD_REQUEST)

        profile = get_object_or_404(DoctorProfile, id=profile_id)
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
        return response.Response(DoctorProfileSerializer(profile).data)
