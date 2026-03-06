from django.urls import path
from .views import UserLoginView, register_doctor, register_patient, user_logout

app_name = "accounts"

urlpatterns = [
    path("login/", UserLoginView.as_view(), name="login"),
    path("logout/", user_logout, name="logout"),
    path("register/doctor/", register_doctor, name="register_doctor"),
    path("register/patient/", register_patient, name="register_patient"),
]
