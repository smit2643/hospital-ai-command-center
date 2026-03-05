from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api_views import AuditLogViewSet, HealthAPIView

router = DefaultRouter()
router.register("audit-logs", AuditLogViewSet, basename="audit-log")

urlpatterns = [
    path("health/", HealthAPIView.as_view(), name="api-health"),
    path("", include(router.urls)),
    path("", include("apps.accounts.api_urls")),
    path("", include("apps.doctors.api_urls")),
    path("", include("apps.documents.api_urls")),
    path("", include("apps.signatures.api_urls")),
]
