from pathlib import Path

import magic
from django.conf import settings
from rest_framework import serializers

from apps.accounts.models import Role, User
from apps.frameworks.models import ClauseStatus

from .models import (
    Assessment,
    Attachment,
    ClauseAssessment,
    SubClauseAssessment,
)

# Clause-text image library: only real images, sniffed by content.
_IMAGE_EXT_MIME = {
    "png": {"image/png"},
    "jpg": {"image/jpeg"},
    "jpeg": {"image/jpeg"},
}

# Extension -> acceptable MIME types from content sniffing. A mismatch
# (e.g. an .exe renamed to .pdf) is rejected.
_EXT_MIME = {
    "pdf": {"application/pdf"},
    "png": {"image/png"},
    "jpg": {"image/jpeg"},
    "jpeg": {"image/jpeg"},
    "docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/zip",  # docx is a zip; some libmagic builds report it as such
    },
    "xlsx": {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/zip",
    },
    "txt": {"text/plain"},
    "zip": {"application/zip"},
    "pcap": {"application/vnd.tcpdump.pcap", "application/octet-stream"},
}


class AssessmentSerializer(serializers.ModelSerializer):
    system_name = serializers.CharField(source="system.name", read_only=True)
    company_name = serializers.CharField(source="system.company.name", read_only=True)
    framework_title = serializers.CharField(source="framework.title", read_only=True)
    assessor_name = serializers.CharField(source="assessor.username", read_only=True)
    reviewer_name = serializers.CharField(
        source="reviewer.username", read_only=True, default=None
    )
    status_counts = serializers.SerializerMethodField()
    sub_status_counts = serializers.SerializerMethodField()
    compliance_percent = serializers.IntegerField(read_only=True, allow_null=True)

    class Meta:
        model = Assessment
        fields = [
            "id", "system", "system_name", "company_name", "framework",
            "framework_title", "kind", "status", "assessor", "assessor_name",
            "reviewer", "reviewer_name", "tester_code", "approver_code",
            "test_completed_date", "architecture_overview", "test_configuration",
            "doc_version", "change_log", "status_counts", "sub_status_counts",
            "compliance_percent", "created_at", "updated_at",
        ]
        # status only changes through the transition endpoint.
        read_only_fields = ["kind", "status", "created_at", "updated_at"]

    def get_status_counts(self, obj) -> dict:
        return obj.status_counts()

    def get_sub_status_counts(self, obj) -> dict:
        return obj.sub_status_counts()

    def validate_assessor(self, value):
        if value.role != Role.ASSESSOR:
            raise serializers.ValidationError("کاربر انتخاب‌شده نقش ارزیاب ندارد.")
        return value

    def validate_reviewer(self, value):
        if value is not None and value.role != Role.REVIEWER:
            raise serializers.ValidationError("کاربر انتخاب‌شده نقش بازبین ندارد.")
        return value

    def validate_change_log(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("قالب تغییرات سند نامعتبر است.")
        for entry in value:
            if not isinstance(entry, dict):
                raise serializers.ValidationError("قالب تغییرات سند نامعتبر است.")
            extra = set(entry) - {"version", "date", "description"}
            if extra:
                raise serializers.ValidationError("فیلد ناشناخته در تغییرات سند.")
            for v in entry.values():
                if not isinstance(v, str) or len(v) > 500:
                    raise serializers.ValidationError("مقدار نامعتبر در تغییرات سند.")
        return value


class AssessmentUpdateSerializer(AssessmentSerializer):
    """PATCH: metadata and free-text only — never system/framework/status."""

    class Meta(AssessmentSerializer.Meta):
        read_only_fields = AssessmentSerializer.Meta.read_only_fields + [
            "system", "framework", "assessor", "reviewer",
        ]


class ClauseAssessmentSerializer(serializers.ModelSerializer):
    clause_code = serializers.CharField(source="clause.code", read_only=True)
    clause_title = serializers.CharField(source="clause.title", read_only=True)
    clause_description = serializers.CharField(source="clause.description", read_only=True)
    clause_objective = serializers.CharField(source="clause.objective", read_only=True)
    requirement_id = serializers.IntegerField(source="clause.requirement_id", read_only=True)
    requirement_title = serializers.CharField(source="clause.requirement.title", read_only=True)
    klass_title = serializers.CharField(source="clause.requirement.klass_title", read_only=True)
    guidance = serializers.CharField(source="clause.requirement.guidance", read_only=True)

    sub_assessments = serializers.SerializerMethodField()

    class Meta:
        model = ClauseAssessment
        fields = [
            "id", "assessment", "clause", "clause_code", "clause_title",
            "clause_description", "clause_objective", "requirement_id",
            "requirement_title", "klass_title", "guidance", "status", "text",
            "text_edited", "sub_assessments", "updated_at",
        ]
        # status is derived from the sub-clause verdicts (recompute_status),
        # never set directly.
        read_only_fields = [
            "assessment", "clause", "status", "text_edited", "updated_at",
        ]

    def get_sub_assessments(self, obj) -> list:
        return SubClauseAssessmentSerializer(
            obj.sub_assessments.select_related("sub_clause").prefetch_related(
                "attachments"
            ),
            many=True,
        ).data

    def update(self, instance, validated_data):
        user = self.context["request"].user
        new_text = validated_data.get("text")
        if new_text is not None and new_text != instance.text:
            instance.text = new_text
            instance.text_edited = True
        instance.updated_by = user
        instance.save()
        return instance


class AttachmentSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True)
    # Optional evidence link to a sub-clause; the view verifies it belongs
    # to the same assessment before saving (no cross-assessment attach).
    sub_clause_assessment = serializers.PrimaryKeyRelatedField(
        queryset=SubClauseAssessment.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Attachment
        fields = ["id", "assessment", "sub_clause_assessment", "file",
                  "original_name", "content_type", "size", "uploaded_by",
                  "uploaded_at"]
        read_only_fields = ["assessment", "original_name", "content_type",
                            "size", "uploaded_by", "uploaded_at"]

    def validate_file(self, uploaded):
        if uploaded.size > settings.UPLOAD_MAX_BYTES:
            raise serializers.ValidationError(
                f"حداکثر حجم مجاز فایل {settings.UPLOAD_MAX_BYTES // (1024*1024)} مگابایت است."
            )
        name = Path(uploaded.name or "")
        # Reject double extensions like report.pdf.exe — only the final
        # suffix counts and the stem must not hide another known suffix.
        ext = name.suffix.lower().lstrip(".")
        if ext not in settings.UPLOAD_ALLOWED_EXTENSIONS:
            raise serializers.ValidationError("فرمت فایل مجاز نیست.")
        head = uploaded.read(8192)
        uploaded.seek(0)
        sniffed = magic.from_buffer(head, mime=True)
        allowed_mimes = _EXT_MIME.get(ext, set())
        if sniffed not in allowed_mimes and not (
            ext == "txt" and sniffed.startswith("text/")
        ):
            raise serializers.ValidationError(
                "محتوای فایل با پسوند آن همخوانی ندارد."
            )
        return uploaded

    def create(self, validated_data):
        uploaded = validated_data["file"]
        request = self.context["request"]
        head = uploaded.read(8192)
        uploaded.seek(0)
        return Attachment.objects.create(
            assessment=validated_data["assessment"],
            sub_clause_assessment=validated_data.get("sub_clause_assessment"),
            file=uploaded,
            original_name=Path(uploaded.name).name[:255],
            content_type=magic.from_buffer(head, mime=True),
            size=uploaded.size,
            uploaded_by=request.user,
        )


class ClauseImageSerializer(serializers.ModelSerializer):
    """A user's uploaded image for a clause's text, referenced via
    [[filename_slug]] placeholders. Strictly scoped to the uploading user
    and the clause assessment it was uploaded for."""

    file = serializers.FileField(write_only=True)
    placeholder_token = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = ["id", "filename_slug", "placeholder_token", "url", "file"]
        read_only_fields = ["id", "filename_slug", "placeholder_token", "url"]

    def validate_file(self, uploaded):
        if uploaded.size > settings.UPLOAD_MAX_BYTES:
            raise serializers.ValidationError(
                f"حداکثر حجم مجاز فایل {settings.UPLOAD_MAX_BYTES // (1024*1024)} مگابایت است."
            )
        name = Path(uploaded.name or "")
        ext = name.suffix.lower().lstrip(".")
        if ext not in _IMAGE_EXT_MIME:
            raise serializers.ValidationError("فقط تصاویر PNG یا JPEG مجاز است.")
        head = uploaded.read(8192)
        uploaded.seek(0)
        sniffed = magic.from_buffer(head, mime=True)
        if sniffed not in _IMAGE_EXT_MIME[ext]:
            raise serializers.ValidationError("محتوای فایل با پسوند آن همخوانی ندارد.")
        return uploaded

    def get_placeholder_token(self, obj) -> str:
        return f"[[{obj.filename_slug}]]"

    def get_url(self, obj) -> str:
        return f"/attachments/{obj.id}/inline/"

    def create(self, validated_data):
        uploaded = validated_data["file"]
        request = self.context["request"]
        clause_assessment = validated_data["clause_assessment"]
        head = uploaded.read(8192)
        uploaded.seek(0)
        slug = Attachment.unique_image_slug(clause_assessment, request.user, uploaded.name)
        return Attachment.objects.create(
            assessment=clause_assessment.assessment,
            clause_assessment=clause_assessment,
            file=uploaded,
            original_name=Path(uploaded.name).name[:255],
            filename_slug=slug,
            content_type=magic.from_buffer(head, mime=True),
            size=uploaded.size,
            uploaded_by=request.user,
        )


class SubClauseAssessmentSerializer(serializers.ModelSerializer):
    sub_clause_text = serializers.CharField(source="sub_clause.text", read_only=True)
    sub_clause_order = serializers.IntegerField(
        source="sub_clause.order", read_only=True
    )
    attachments = AttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = SubClauseAssessment
        fields = [
            "id", "clause_assessment", "sub_clause", "sub_clause_text",
            "sub_clause_order", "status", "notes", "attachments", "updated_at",
        ]
        read_only_fields = ["clause_assessment", "sub_clause", "updated_at"]

    def validate_status(self, value):
        if value not in ClauseStatus.values:
            raise serializers.ValidationError("وضعیت نامعتبر است.")
        return value
