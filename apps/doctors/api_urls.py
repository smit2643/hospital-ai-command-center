from django.urls import path
from .api_views import DoctorApprovalAPI, PendingDoctorListAPI

urlpatterns = [
    path("doctors/pending/", PendingDoctorListAPI.as_view(), name="api-doctor-pending"),
    path("doctors/<int:profile_id>/approval/", DoctorApprovalAPI.as_view(), name="api-doctor-approval"),
]
