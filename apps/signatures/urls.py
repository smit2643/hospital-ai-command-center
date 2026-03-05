from django.urls import path
from . import views

app_name = "signatures"

urlpatterns = [
    path("signatures/request/<int:document_id>/", views.request_signature, name="request_signature"),
    path("sign/<uuid:token>/", views.sign_public, name="sign_public"),
    path("signatures/<int:request_id>/status/", views.status, name="status"),
]
