from django.urls import path
from . import views

app_name = "documents"

urlpatterns = [
    path("documents/upload/", views.upload, name="upload"),
    path("patients/<int:patient_id>/documents/", views.patient_documents, name="patient_docs"),
    path("patients/<int:patient_id>/documents/summary/generate/", views.generate_patient_summary, name="generate_patient_summary"),
    path("documents/<int:document_id>/ocr/trigger/", views.trigger_ocr, name="trigger_ocr"),
    path("documents/<int:document_id>/ocr/status/", views.ocr_status, name="ocr_status"),
    path("documents/<int:document_id>/ocr/result/", views.ocr_result, name="ocr_result"),
    path("documents/<int:document_id>/edit/", views.edit_document, name="edit_document"),
    path("documents/<int:document_id>/delete/", views.delete_document, name="delete_document"),
]
