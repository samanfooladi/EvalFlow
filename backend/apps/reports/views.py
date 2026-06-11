from urllib.parse import quote

from django.http import FileResponse
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Role
from apps.accounts.permissions import ALL_ROLES, IsAssignedOrElevated, RolePermission
from apps.assessments.models import Assessment
from apps.audit.services import log_event
from apps.frameworks.models import ClauseStatus

from .services.brp_generator import generate_brp
from .services.trp_generator import generate_trp
from .services.vtr_generator import generate_vtr

GENERATORS = {
    "trp": ("TRP", generate_trp),
    "vtr": ("VTR", generate_vtr),
    "brp": (None, generate_brp),  # BRP valid for both kinds
}


class AssessmentExportView(APIView):
    """GET /api/v1/assessments/{id}/export/?type=trp|vtr|brp"""

    permission_classes = [RolePermission, IsAssignedOrElevated]
    allowed_roles = {"get": ALL_ROLES}

    def get(self, request, pk: int):
        try:
            assessment = Assessment.objects.select_related(
                "system", "system__company", "framework"
            ).get(pk=pk)
        except Assessment.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(request, assessment)

        export_type = request.query_params.get("type", "").lower()
        if export_type not in GENERATORS:
            raise ValidationError({"type": "نوع خروجی باید trp یا vtr یا brp باشد."})
        required_kind, generator = GENERATORS[export_type]
        if required_kind and assessment.kind != required_kind:
            raise ValidationError(
                {"type": f"این ارزیابی از نوع {assessment.kind} است."}
            )

        # Unreviewed clauses block export unless an elevated role overrides.
        if export_type != "brp":
            unreviewed = assessment.clause_assessments.filter(
                status=ClauseStatus.UNREVIEWED
            ).count()
            allow_incomplete = (
                request.query_params.get("allow_incomplete") == "1"
                and request.user.role in (Role.ADMIN, Role.QA_LEAD)
            )
            if unreviewed and not allow_incomplete:
                raise ValidationError(
                    {
                        "detail": f"{unreviewed} بند هنوز بررسی نشده است. "
                        "خروجی نهایی پس از تکمیل بررسی امکان‌پذیر است."
                    }
                )

        buffer = generator(assessment)
        filename = f"{export_type.upper()}-{assessment.system.name}.docx"
        response = FileResponse(
            buffer,
            as_attachment=True,
            content_type=(
                "application/vnd.openxmlformats-officedocument"
                ".wordprocessingml.document"
            ),
        )
        response["Content-Disposition"] = (
            f"attachment; filename*=UTF-8''{quote(filename)}"
        )
        response["X-Content-Type-Options"] = "nosniff"
        log_event(
            request,
            action="export_docx",
            model="assessments.Assessment",
            object_id=str(assessment.pk),
            object_repr=f"{export_type.upper()} {assessment}",
        )
        return response
