from django.urls import path
from . import views

app_name = "patients"

urlpatterns = [
    path("dashboard/patient/", views.dashboard, name="dashboard"),
    path("patients/", views.patient_list, name="list"),
    path("patients/add/", views.add_patient, name="add"),
    path("patients/<int:patient_id>/", views.detail, name="detail"),
    path("patients/<int:patient_id>/assign-doctor/", views.assign_doctor, name="assign_doctor"),
]
