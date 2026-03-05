from django.urls import path
from .views import UserLoginView, UserLogoutView, register_doctor, register_patient

app_name = "accounts"

urlpatterns = [
    path("login/", UserLoginView.as_view(), name="login"),
    path("logout/", UserLogoutView.as_view(), name="logout"),
    path("register/doctor/", register_doctor, name="register_doctor"),
    path("register/patient/", register_patient, name="register_patient"),
]
