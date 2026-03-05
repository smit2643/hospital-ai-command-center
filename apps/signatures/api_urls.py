from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .api_views import SignatureRequestCreateAPI, SignatureRequestViewSet, SignatureStatusAPI

router = DefaultRouter()
router.register("signature-requests", SignatureRequestViewSet, basename="signature-request")
router.register("signature-create", SignatureRequestCreateAPI, basename="signature-create")
router.register("signature-status", SignatureStatusAPI, basename="signature-status")

urlpatterns = [
    path("", include(router.urls)),
]
