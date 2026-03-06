from django.urls import path
from . import views

app_name = "documents"

urlpatterns = [
    path("documents/upload/", views.upload, name="upload"),
    path("patients/<int:patient_id>/documents/", views.patient_documents, name="patient_docs"),
    path("documents/<int:document_id>/ocr/trigger/", views.trigger_ocr, name="trigger_ocr"),
    path("documents/<int:document_id>/ocr/status/", views.ocr_status, name="ocr_status"),
    path("documents/<int:document_id>/ocr/result/", views.ocr_result, name="ocr_result"),
]
