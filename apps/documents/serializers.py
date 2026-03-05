from rest_framework import serializers
from .models import DocumentExtraction, DocumentLabTest, OCRResult, PatientDocument


class OCRResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = OCRResult
        fields = "__all__"


class DocumentLabTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentLabTest
        fields = ["id", "test_name", "value", "unit", "reference_range", "order_index"]


class DocumentExtractionSerializer(serializers.ModelSerializer):
    tests = DocumentLabTestSerializer(many=True, read_only=True)

    class Meta:
        model = DocumentExtraction
        fields = [
            "id",
            "patient_name",
            "report_date_text",
            "hospital_name",
            "doctor_name",
            "notes",
            "is_reviewed",
            "reviewed_by",
            "reviewed_at",
            "tests",
        ]


class PatientDocumentSerializer(serializers.ModelSerializer):
    extraction = DocumentExtractionSerializer(read_only=True)

    class Meta:
        model = PatientDocument
        fields = "__all__"
        read_only_fields = ["uploaded_by", "version", "previous_version", "ocr_status", "extracted_summary", "extracted_confidence"]
