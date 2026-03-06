from django.urls import path
from . import views

app_name = "patients"

urlpatterns = [
    path("dashboard/patient/", views.dashboard, name="dashboard"),
    path("patients/", views.patient_list, name="list"),
    path("patients/add/", views.add_patient, name="add"),
    path("patients/<int:patient_id>/", views.detail, name="detail"),
    path("patients/<int:patient_id>/assign-doctor/", views.assign_doctor, name="assign_doctor"),
    path("patients/assignments/<int:assignment_id>/edit/", views.assignment_edit, name="assignment_edit"),
    path("patients/assignments/<int:assignment_id>/delete/", views.assignment_delete, name="assignment_delete"),
]
