from django.contrib import admin
from .models import OCRResult, PatientDocument


@admin.register(PatientDocument)
class PatientDocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "patient", "document_type", "ocr_status", "version", "created_at")
    list_filter = ("document_type", "ocr_status")
    search_fields = ("patient__user__full_name",)


@admin.register(OCRResult)
class OCRResultAdmin(admin.ModelAdmin):
    list_display = ("id", "document", "parser_version", "created_at")
