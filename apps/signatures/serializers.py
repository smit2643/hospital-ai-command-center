from rest_framework import serializers
from .models import SignatureArtifact, SignatureRequest


class SignatureArtifactSerializer(serializers.ModelSerializer):
    class Meta:
        model = SignatureArtifact
        fields = "__all__"


class SignatureRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = SignatureRequest
        fields = "__all__"
        read_only_fields = ["token", "requester", "status", "expires_at", "created_at"]
