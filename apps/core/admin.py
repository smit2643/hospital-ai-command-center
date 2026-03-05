from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "object_type", "object_id", "actor", "timestamp")
    list_filter = ("action", "object_type")
    search_fields = ("object_id", "metadata")
