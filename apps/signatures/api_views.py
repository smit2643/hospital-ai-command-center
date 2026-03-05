from rest_framework import permissions, response, status, viewsets
from django.shortcuts import get_object_or_404
from apps.core.permissions import doctor_can_access_patient
from .models import SignatureRequest
from .serializers import SignatureRequestSerializer
from .services import build_signature_expiry
from .tasks import send_signature_request_email


class SignatureRequestViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SignatureRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = SignatureRequest.objects.select_related("document__patient__user", "requester")
        if user.is_superuser or user.role == user.Role.ADMIN:
            return qs
        if user.role == user.Role.PATIENT:
            return qs.filter(document__patient__user=user)
        return qs.filter(requester=user)


class SignatureRequestCreateAPI(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request):
        serializer = SignatureRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        document = serializer.validated_data["document"]
        if not doctor_can_access_patient(request.user, document.patient):
            return response.Response({"detail": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        sign_request = SignatureRequest.objects.create(
            document=document,
            requester=request.user,
            signer_email=serializer.validated_data["signer_email"],
            expires_at=build_signature_expiry(),
        )
        send_signature_request_email.delay(sign_request.id)
        return response.Response(SignatureRequestSerializer(sign_request).data, status=status.HTTP_201_CREATED)


class SignatureStatusAPI(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def retrieve(self, request, pk=None):
        sign_request = get_object_or_404(SignatureRequest.objects.select_related("document__patient__user", "requester"), id=pk)
        user = request.user
        if not (user.is_superuser or user.role == user.Role.ADMIN):
            if user.role == user.Role.PATIENT and sign_request.document.patient.user_id != user.id:
                return response.Response({"detail": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
            if user.role == user.Role.DOCTOR and sign_request.requester_id != user.id:
                return response.Response({"detail": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        return response.Response(SignatureRequestSerializer(sign_request).data)
