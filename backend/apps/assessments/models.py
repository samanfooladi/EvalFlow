import uuid
from pathlib import Path

from django.conf import settings
from django.db import models
from django.db.models import Count, Q

from apps.catalog.models import ProductSystem
from apps.frameworks.models import Clause, ClauseStatus, Framework, FrameworkKind


class AssessmentStatus(models.TextChoices):
    UNDER_ASSESSMENT = "under_assessment", "در حال ارزیابی"
    UNDER_REVIEW = "under_review", "در حال بازبینی"
    COMPLETED = "completed", "تکمیل‌شده"


class Assessment(models.Model):
    """One assessment round of a system against a framework (TRP or VTR)."""

    system = models.ForeignKey(
        ProductSystem, on_delete=models.PROTECT, related_name="assessments"
    )
    framework = models.ForeignKey(
        Framework, on_delete=models.PROTECT, related_name="assessments"
    )
    kind = models.CharField(max_length=8, choices=FrameworkKind.choices, editable=False)
    status = models.CharField(
        max_length=24,
        choices=AssessmentStatus.choices,
        default=AssessmentStatus.UNDER_ASSESSMENT,
    )
    assessor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assigned_assessments",
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="review_assessments",
    )
    tester_code = models.CharField("کد آزمونگر", max_length=64, blank=True)
    approver_code = models.CharField("کد تأییدکننده", max_length=64, blank=True)
    test_completed_date = models.DateField("تاریخ اتمام آزمون", null=True, blank=True)
    architecture_overview = models.TextField("نمای کلی معماری", blank=True)
    test_configuration = models.TextField("پیکربندی آزمون", blank=True)
    doc_version = models.CharField("نسخه سند", max_length=16, default="1.0")
    # List of {"version": "...", "date": "1404/...", "description": "..."}
    change_log = models.JSONField(default=list, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.kind} {self.system}"

    def save(self, *args, **kwargs):
        if not self.kind:
            self.kind = self.framework.kind
        super().save(*args, **kwargs)

    def create_clause_assessments(self):
        """Fan out one ClauseAssessment per framework clause (idempotent)."""
        existing = set(
            self.clause_assessments.values_list("clause_id", flat=True)
        )
        missing = Clause.objects.filter(
            requirement__framework=self.framework
        ).exclude(pk__in=existing)
        ClauseAssessment.objects.bulk_create(
            ClauseAssessment(assessment=self, clause=clause) for clause in missing
        )

    def status_counts(self) -> dict:
        agg = self.clause_assessments.aggregate(
            total=Count("id"),
            compliant=Count("id", filter=Q(status=ClauseStatus.COMPLIANT)),
            finding=Count("id", filter=Q(status=ClauseStatus.FINDING)),
            not_applicable=Count("id", filter=Q(status=ClauseStatus.NOT_APPLICABLE)),
            unreviewed=Count("id", filter=Q(status=ClauseStatus.UNREVIEWED)),
        )
        return agg

    @property
    def compliance_percent(self) -> int | None:
        """compliant / (total - not_applicable), rounded; None if no basis."""
        counts = self.status_counts()
        basis = counts["total"] - counts["not_applicable"]
        if basis <= 0:
            return None
        return round(100 * counts["compliant"] / basis)


class ClauseAssessment(models.Model):
    """Verdict + assessor text for a single clause within an assessment."""

    assessment = models.ForeignKey(
        Assessment, on_delete=models.CASCADE, related_name="clause_assessments"
    )
    clause = models.ForeignKey(Clause, on_delete=models.PROTECT, related_name="+")
    status = models.CharField(
        max_length=16, choices=ClauseStatus.choices, default=ClauseStatus.UNREVIEWED
    )
    # تشریح آزمون انجام شده — pre-filled from DefaultTextTemplate.
    text = models.TextField(blank=True)
    text_edited = models.BooleanField(default=False)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["clause__requirement__order", "clause__order"]
        constraints = [
            models.UniqueConstraint(
                fields=["assessment", "clause"], name="uniq_clause_per_assessment"
            )
        ]

    def __str__(self):
        return f"{self.clause.code} [{self.status}]"

    def render_default_text(self) -> str:
        template = self.assessment.framework.default_texts.filter(
            status=self.status
        ).first()
        if template is None:
            return ""
        system = self.assessment.system
        return template.render(
            {
                "clause_code": self.clause.code,
                "clause_title": self.clause.title,
                "requirement_title": self.clause.requirement.title,
                "product_name": system.name,
                "company_name": system.company.name,
            }
        )

    def apply_status(self, new_status: str, user=None) -> None:
        """Set status; refresh default text unless the assessor edited it."""
        self.status = new_status
        if new_status != ClauseStatus.UNREVIEWED and not self.text_edited:
            self.text = self.render_default_text()
        self.updated_by = user
        self.save()


def attachment_upload_path(instance, filename):
    # Random name: never trust/expose the client-supplied filename on disk.
    ext = Path(filename).suffix.lower().lstrip(".")
    return f"attachments/{instance.assessment_id}/{uuid.uuid4().hex}.{ext}"


class Attachment(models.Model):
    assessment = models.ForeignKey(
        Assessment, on_delete=models.CASCADE, related_name="attachments"
    )
    file = models.FileField(upload_to=attachment_upload_path, max_length=255)
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=128)
    size = models.PositiveBigIntegerField()
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.original_name
