from rest_framework import decorators, permissions, response, status, viewsets
from apps.core.permissions import doctor_can_access_patient, doctor_is_approved
from .models import OCRResult, PatientDocument
from .serializers import OCRResultSerializer, PatientDocumentSerializer
from .tasks import process_document_ocr


class PatientDocumentViewSet(viewsets.ModelViewSet):
    queryset = PatientDocument.objects.select_related("patient", "uploaded_by").all()
    serializer_class = PatientDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        if user.is_superuser or user.role == user.Role.ADMIN:
            return qs
        if user.role == user.Role.PATIENT:
            return qs.filter(patient__user=user)
        if user.role == user.Role.DOCTOR and not doctor_is_approved(user):
            return qs.none()
        return qs.filter(patient__assignments__doctor__user=user, patient__assignments__is_active=True).distinct()

    def perform_create(self, serializer):
        patient = serializer.validated_data["patient"]
        if not doctor_can_access_patient(self.request.user, patient):
            raise permissions.PermissionDenied("Cannot upload for this patient")

        previous = (
            PatientDocument.objects.filter(patient=patient, document_type=serializer.validated_data["document_type"])
            .order_by("-version")
            .first()
        )
        extra = {"uploaded_by": self.request.user}
        if previous:
            extra["version"] = previous.version + 1
            extra["previous_version"] = previous
        serializer.save(**extra)

    @decorators.action(detail=True, methods=["post"])
    def trigger_ocr(self, request, pk=None):
        doc = self.get_object()
        if request.user.role not in {request.user.Role.ADMIN, request.user.Role.DOCTOR}:
            raise permissions.PermissionDenied("Only admin/doctor can run OCR")
        if request.user.role == request.user.Role.DOCTOR and not doctor_is_approved(request.user):
            raise permissions.PermissionDenied("Doctor account is pending approval")
        process_document_ocr.delay(doc.id)
        return response.Response({"detail": "OCR started"}, status=status.HTTP_202_ACCEPTED)


class OCRResultViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = OCRResult.objects.select_related("document").all()
    serializer_class = OCRResultSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        if user.is_superuser or user.role == user.Role.ADMIN:
            return qs
        if user.role == user.Role.PATIENT:
            return qs.none()
        if user.role == user.Role.DOCTOR and not doctor_is_approved(user):
            return qs.none()
        return qs.filter(document__patient__assignments__doctor__user=user).distinct()
