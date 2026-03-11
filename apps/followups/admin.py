from django.contrib import admin

from .models import FollowUpPlan


@admin.register(FollowUpPlan)
class FollowUpPlanAdmin(admin.ModelAdmin):
    list_display = ("id", "patient", "doctor", "due_date", "status", "reminder_date", "created_at")
    list_filter = ("status", "due_date")
    search_fields = ("patient__user__full_name", "patient__user__email", "follow_up_text")
