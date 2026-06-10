from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.TextChoices):
    ADMIN = "admin", "مدیر سیستم"
    ASSESSOR = "assessor", "ارزیاب"
    REVIEWER = "reviewer", "بازبین"
    QA_LEAD = "qa_lead", "مسئول تضمین کیفیت"


class User(AbstractUser):
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.ASSESSOR)
    # Printed as "کد آزمونگر" in generated documents.
    assessor_code = models.CharField(max_length=32, blank=True)
    must_change_password = models.BooleanField(default=False)

    class Meta:
        ordering = ["username"]

    @property
    def is_admin_role(self) -> bool:
        return self.role == Role.ADMIN

    @property
    def is_elevated(self) -> bool:
        """Admin and QA Lead share most management permissions."""
        return self.role in (Role.ADMIN, Role.QA_LEAD)
