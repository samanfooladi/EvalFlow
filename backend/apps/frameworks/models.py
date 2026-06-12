from django.db import models


class FrameworkKind(models.TextChoices):
    TRP = "TRP", "گزارش آزمون کارکردی"
    VTR = "VTR", "گزارش آزمون آسیب‌پذیری"


class ClauseStatus(models.TextChoices):
    UNREVIEWED = "unreviewed", "بررسی‌نشده"
    COMPLIANT = "compliant", "قبول"
    FINDING = "finding", "عدم انطباق"
    NOT_APPLICABLE = "not_applicable", "مصداق ندارد"


class Framework(models.Model):
    """A requirement framework, e.g. the Network Application protection
    profile (TRP) or the OWASP OTG category list (VTR)."""

    code = models.SlugField(max_length=64, unique=True)
    title = models.CharField("عنوان", max_length=255)
    kind = models.CharField(max_length=8, choices=FrameworkKind.choices)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} ({self.kind})"


class Requirement(models.Model):
    """Grouping level: an SFR component family (TRP) or an OWASP test
    category (VTR). Holds per-requirement guidance notes."""

    framework = models.ForeignKey(
        Framework, on_delete=models.CASCADE, related_name="requirements"
    )
    # SFR class title for TRP grouping (e.g. "کلاس ممیزی امنیت"); for VTR
    # equals the category title.
    klass_title = models.CharField("عنوان کلاس", max_length=255)
    code = models.CharField(max_length=64)
    title = models.CharField("عنوان", max_length=255)
    guidance = models.TextField("راهنمای ارزیاب", blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["framework", "order", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["framework", "code"], name="uniq_requirement_code"
            )
        ]

    def __str__(self):
        return f"{self.code} {self.title}"


class Clause(models.Model):
    """The assessable unit: FAU_GEN.1.1 (TRP) or OTG-INFO-001 (VTR)."""

    requirement = models.ForeignKey(
        Requirement, on_delete=models.CASCADE, related_name="clauses"
    )
    code = models.CharField(max_length=64)
    title = models.CharField("عنوان", max_length=255)
    # Text printed in the عنوان الزام row of the output document.
    description = models.TextField("شرح الزام", blank=True)
    # Printed in the هدف الزام row; newline-separated, "- " lines become bullets.
    objective = models.TextField("هدف الزام", blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["requirement", "order", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["requirement", "code"], name="uniq_clause_code"
            )
        ]

    def __str__(self):
        return f"{self.code} {self.title}"


class SubClause(models.Model):
    """A single assessable item inside a clause — e.g. one audit-event bullet
    of FAU_GEN.1.1. Each receives its own verdict/notes/evidence per
    assessment. Identified by (clause, order); existing single-text clauses
    are migrated into one sub-clause holding the original text."""

    clause = models.ForeignKey(
        Clause, on_delete=models.CASCADE, related_name="sub_clauses"
    )
    text = models.TextField("متن بند")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["clause", "order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["clause", "order"], name="uniq_subclause_order"
            )
        ]

    def __str__(self):
        return f"{self.clause.code}#{self.order}"


class DefaultTextTemplate(models.Model):
    """Status-driven default text for the تشریح آزمون field. Rendered with
    plain placeholder substitution (never a template engine — users are
    hostile and SSTI is a real risk)."""

    PLACEHOLDERS = (
        "clause_code",
        "clause_title",
        "requirement_title",
        "product_name",
        "company_name",
    )

    framework = models.ForeignKey(
        Framework, on_delete=models.CASCADE, related_name="default_texts"
    )
    status = models.CharField(
        max_length=16,
        choices=[c for c in ClauseStatus.choices if c[0] != ClauseStatus.UNREVIEWED],
    )
    template = models.TextField("قالب متن")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["framework", "status"], name="uniq_template_per_status"
            )
        ]

    def render(self, context: dict) -> str:
        text = self.template
        for key in self.PLACEHOLDERS:
            text = text.replace("{{" + key + "}}", str(context.get(key, "")))
        return text

    def __str__(self):
        return f"{self.framework.code}/{self.status}"
