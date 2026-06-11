from django.conf import settings
from django.db import models


class Company(models.Model):
    """The service requester / product vendor (شرکت)."""

    name = models.CharField("نام شرکت", max_length=200, unique=True)
    name_en = models.CharField("نام انگلیسی", max_length=200, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "companies"

    def __str__(self):
        return self.name


class ProductSystem(models.Model):
    """The product/system under assessment (سامانه)."""

    company = models.ForeignKey(
        Company, on_delete=models.PROTECT, related_name="systems"
    )
    name = models.CharField("نام سامانه", max_length=200)
    name_en = models.CharField("نام انگلیسی", max_length=200, blank=True)
    version = models.CharField("نسخه", max_length=64, blank=True)
    description = models.TextField("توضیحات", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["company__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "name", "version"], name="uniq_system_per_company"
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.company.name})"
