from django.conf import settings
from django.db import models


class Action(models.TextChoices):
    LOGIN_OK = "login_ok", "ورود موفق"
    LOGIN_FAIL = "login_fail", "ورود ناموفق"
    CREATE = "create", "ایجاد"
    UPDATE = "update", "ویرایش"
    DELETE = "delete", "حذف"
    STATUS_CHANGE = "status_change", "تغییر وضعیت"
    EXPORT_DOCX = "export_docx", "خروجی سند"
    UPLOAD = "upload", "بارگذاری فایل"


class AuditLog(models.Model):
    """Append-only audit trail. There is intentionally no API or admin
    affordance to modify or delete rows."""

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=32, choices=Action.choices)
    model = models.CharField(max_length=64, blank=True)
    object_id = models.CharField(max_length=64, blank=True)
    object_repr = models.CharField(max_length=256, blank=True)
    changes = models.JSONField(null=True, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=256, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["action", "created_at"]),
            models.Index(fields=["model", "object_id"]),
        ]

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValueError("Audit log entries are append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Audit log entries cannot be deleted.")
