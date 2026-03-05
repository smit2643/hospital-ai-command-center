from django.urls import path
from . import views

app_name = "doctors"

urlpatterns = [
    path("dashboard/doctor/", views.dashboard, name="dashboard"),
    path("admin/doctor-approvals/", views.approval_list, name="approval_list"),
    path("admin/doctor-approvals/<int:profile_id>/<str:decision>/", views.approval_action, name="approval_action"),
]
