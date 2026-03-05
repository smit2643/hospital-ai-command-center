from rest_framework import permissions, response, viewsets, views

from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related("actor").all()
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAdminUser]


class HealthAPIView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return response.Response({"status": "ok", "service": "hospital_ai"})
