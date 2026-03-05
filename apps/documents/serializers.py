from rest_framework import serializers
from .models import OCRResult, PatientDocument


class OCRResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = OCRResult
        fields = "__all__"


class PatientDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientDocument
        fields = "__all__"
        read_only_fields = ["uploaded_by", "version", "previous_version", "ocr_status", "extracted_summary", "extracted_confidence"]
