from rest_framework import serializers
from .models import DocumentExtractedField, DocumentExtraction, DocumentLabTest, OCRResult, PatientDocument


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
    extra_fields = serializers.SerializerMethodField()

    def get_extra_fields(self, obj):
        rows = obj.extra_fields.all()
        return [
            {
                "id": row.id,
                "field_key": row.field_key,
                "label": row.label,
                "value_type": row.value_type,
                "value": row.value_text if row.value_type == DocumentExtractedField.ValueType.TEXT else row.value_short,
                "order_index": row.order_index,
            }
            for row in rows
        ]

    class Meta:
        model = DocumentExtraction
        fields = [
            "id",
            "patient_name",
            "patient_email",
            "patient_phone",
            "patient_dob_text",
            "report_date_text",
            "hospital_name",
            "doctor_name",
            "notes",
            "identity_verified",
            "identity_message",
            "is_reviewed",
            "reviewed_by",
            "reviewed_at",
            "tests",
            "extra_fields",
        ]


class PatientDocumentSerializer(serializers.ModelSerializer):
    extraction = DocumentExtractionSerializer(read_only=True)

    class Meta:
        model = PatientDocument
        fields = "__all__"
        read_only_fields = ["uploaded_by", "version", "previous_version", "ocr_status", "extracted_summary", "extracted_confidence"]
