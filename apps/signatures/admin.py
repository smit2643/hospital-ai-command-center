from django.contrib import admin
from .models import SignatureArtifact, SignatureRequest


@admin.register(SignatureRequest)
class SignatureRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "document", "signer_email", "status", "expires_at", "created_at")
    list_filter = ("status",)
    search_fields = ("signer_email",)


@admin.register(SignatureArtifact)
class SignatureArtifactAdmin(admin.ModelAdmin):
    list_display = ("id", "signature_request", "signature_type", "signed_at")
