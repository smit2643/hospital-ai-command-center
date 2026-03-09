from django.contrib import admin
from .models import (
    DocumentExtractedField,
    DocumentExtraction,
    DocumentLabTest,
    OCRResult,
    PatientDocument,
    PatientDocumentSummary,
)


@admin.register(PatientDocument)
class PatientDocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "patient", "document_type", "ocr_status", "version", "created_at")
    list_filter = ("document_type", "ocr_status")
    search_fields = ("patient__user__full_name",)


@admin.register(OCRResult)
class OCRResultAdmin(admin.ModelAdmin):
    list_display = ("id", "document", "parser_version", "created_at")


class DocumentLabTestInline(admin.TabularInline):
    model = DocumentLabTest
    extra = 0


class DocumentExtractedFieldInline(admin.TabularInline):
    model = DocumentExtractedField
    extra = 0


@admin.register(DocumentExtraction)
class DocumentExtractionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "document",
        "patient_name",
        "patient_email",
        "identity_verified",
        "hospital_name",
        "doctor_name",
        "is_reviewed",
        "updated_at",
    )
    search_fields = ("document__id", "patient_name", "hospital_name", "doctor_name")
    list_filter = ("is_reviewed", "identity_verified")
    inlines = [DocumentLabTestInline, DocumentExtractedFieldInline]


@admin.register(PatientDocumentSummary)
class PatientDocumentSummaryAdmin(admin.ModelAdmin):
    list_display = ("id", "patient", "source_document_count", "generated_by", "created_at")
    search_fields = ("patient__user__full_name", "summary_text")
