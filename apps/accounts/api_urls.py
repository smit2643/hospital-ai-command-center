from django.urls import path
from .api_views import SessionLoginAPI, SessionLogoutAPI, SessionMeAPI

urlpatterns = [
    path("auth/login/", SessionLoginAPI.as_view(), name="api-login"),
    path("auth/logout/", SessionLogoutAPI.as_view(), name="api-logout"),
    path("auth/me/", SessionMeAPI.as_view(), name="api-me"),
]
