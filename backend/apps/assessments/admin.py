from django.contrib import admin

from .models import Assessment, Attachment, ClauseAssessment


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ("system", "kind", "status", "assessor", "created_at")
    list_filter = ("kind", "status")


admin.site.register(ClauseAssessment)
admin.site.register(Attachment)
