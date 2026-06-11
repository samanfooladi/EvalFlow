from django.contrib import admin

from .models import Clause, DefaultTextTemplate, Framework, Requirement


class RequirementInline(admin.TabularInline):
    model = Requirement
    extra = 0


class ClauseInline(admin.TabularInline):
    model = Clause
    extra = 0


@admin.register(Framework)
class FrameworkAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "kind", "is_active")
    inlines = [RequirementInline]


@admin.register(Requirement)
class RequirementAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "klass_title", "framework")
    list_filter = ("framework",)
    inlines = [ClauseInline]


admin.site.register(DefaultTextTemplate)
