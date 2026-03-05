from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .api_views import OCRResultViewSet, PatientDocumentViewSet

router = DefaultRouter()
router.register("documents", PatientDocumentViewSet, basename="document")
router.register("ocr-results", OCRResultViewSet, basename="ocr-result")

urlpatterns = [
    path("", include(router.urls)),
]
