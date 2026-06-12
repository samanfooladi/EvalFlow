from django.http import FileResponse
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.accounts.models import Role
from apps.accounts.permissions import (
    ALL_ROLES,
    ELEVATED,
    IsAssignedOrElevated,
    RolePermission,
)
from apps.audit.services import log_event

from .models import (
    Assessment,
    AssessmentStatus,
    Attachment,
    ClauseAssessment,
    SubClauseAssessment,
)
from .serializers import (
    AssessmentSerializer,
    AssessmentUpdateSerializer,
    AttachmentSerializer,
    ClauseAssessmentSerializer,
    SubClauseAssessmentSerializer,
)
from .transitions import transition


def _scope_assessments(user, qs):
    """Pre-filter by role: assessors/reviewers only see assigned work.
    This is the IDOR guard — unassigned objects 404, never 200."""
    if user.is_elevated:
        return qs
    if user.role == Role.ASSESSOR:
        return qs.filter(assessor=user)
    if user.role == Role.REVIEWER:
        return qs.filter(reviewer=user)
    return qs.none()


class AssessmentViewSet(viewsets.ModelViewSet):
    permission_classes = [RolePermission, IsAssignedOrElevated]
    allowed_roles = {
        "list": ALL_ROLES,
        "retrieve": ALL_ROLES,
        "create": ELEVATED,
        "update": frozenset({Role.ADMIN, Role.QA_LEAD, Role.ASSESSOR}),
        "partial_update": frozenset({Role.ADMIN, Role.QA_LEAD, Role.ASSESSOR}),
        "destroy": ELEVATED,
        "transition": ALL_ROLES,  # edges themselves are role-gated in the service
        "clause_assessments": ALL_ROLES,
        "attachments": ALL_ROLES,
    }

    def get_queryset(self):
        qs = Assessment.objects.select_related(
            "system", "system__company", "framework", "assessor", "reviewer"
        )
        qs = _scope_assessments(self.request.user, qs)
        # Filters apply to the list view only; on detail actions params like
        # ?status= belong to the sub-resource, not the assessment lookup.
        if self.action == "list":
            params = self.request.query_params
            if status_param := params.get("status"):
                qs = qs.filter(status=status_param)
            if kind := params.get("kind"):
                qs = qs.filter(kind=kind)
            if system := params.get("system"):
                qs = qs.filter(system_id=system)
            if company := params.get("company"):
                qs = qs.filter(system__company_id=company)
        return qs

    def get_serializer_class(self):
        if self.action in ("update", "partial_update"):
            return AssessmentUpdateSerializer
        return AssessmentSerializer

    def perform_create(self, serializer):
        assessment = serializer.save(created_by=self.request.user)
        assessment.create_clause_assessments()
        log_event(self.request, action="create", model="assessments.Assessment",
                  object_id=str(assessment.pk), object_repr=str(assessment))

    def perform_update(self, serializer):
        instance = self.get_object()
        # Assessors may only edit while the work is in progress.
        if (
            self.request.user.role == Role.ASSESSOR
            and instance.status != AssessmentStatus.UNDER_ASSESSMENT
        ):
            raise PermissionDenied("ارزیابی در وضعیت قابل ویرایش نیست.")
        assessment = serializer.save()
        log_event(self.request, action="update", model="assessments.Assessment",
                  object_id=str(assessment.pk), object_repr=str(assessment))

    def perform_destroy(self, instance):
        repr_, pk = str(instance), instance.pk
        instance.delete()
        log_event(self.request, action="delete", model="assessments.Assessment",
                  object_id=str(pk), object_repr=repr_)

    @action(detail=True, methods=["post"])
    def transition(self, request, pk=None):
        assessment = self.get_object()
        to_status = str(request.data.get("status", ""))
        transition(assessment, to_status, request.user, request=request)
        return Response(AssessmentSerializer(assessment).data)

    @action(detail=True, methods=["get"], url_path="clause-assessments")
    def clause_assessments(self, request, pk=None):
        assessment = self.get_object()
        qs = assessment.clause_assessments.select_related(
            "clause", "clause__requirement"
        ).prefetch_related("sub_assessments__sub_clause", "sub_assessments__attachments")
        params = request.query_params
        if status_param := params.get("status"):
            qs = qs.filter(status=status_param)
        if requirement := params.get("requirement"):
            qs = qs.filter(clause__requirement_id=requirement)
        serializer = ClauseAssessmentSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get", "post"])
    def attachments(self, request, pk=None):
        assessment = self.get_object()
        if request.method == "GET":
            serializer = AttachmentSerializer(
                assessment.attachments.all(), many=True
            )
            return Response(serializer.data)
        # POST (upload): reviewers are read-only here.
        if request.user.role == Role.REVIEWER:
            raise PermissionDenied("بازبین مجاز به بارگذاری فایل نیست.")
        serializer = AttachmentSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        sub = serializer.validated_data.get("sub_clause_assessment")
        if sub is not None and sub.clause_assessment.assessment_id != assessment.pk:
            raise ValidationError({"sub_clause_assessment": "بند متعلق به این ارزیابی نیست."})
        attachment = serializer.save(assessment=assessment)
        log_event(request, action="upload", model="assessments.Attachment",
                  object_id=str(attachment.pk), object_repr=attachment.original_name)
        return Response(
            AttachmentSerializer(attachment).data, status=status.HTTP_201_CREATED
        )


class ClauseAssessmentViewSet(
    mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet
):
    serializer_class = ClauseAssessmentSerializer
    permission_classes = [RolePermission, IsAssignedOrElevated]
    allowed_roles = {
        "retrieve": ALL_ROLES,
        "update": frozenset({Role.ADMIN, Role.QA_LEAD, Role.ASSESSOR}),
        "partial_update": frozenset({Role.ADMIN, Role.QA_LEAD, Role.ASSESSOR}),
        "reset_text": frozenset({Role.ADMIN, Role.QA_LEAD, Role.ASSESSOR}),
    }

    def get_queryset(self):
        qs = ClauseAssessment.objects.select_related(
            "assessment", "clause", "clause__requirement",
            "assessment__system", "assessment__system__company",
        )
        user = self.request.user
        if user.is_elevated:
            return qs
        if user.role == Role.ASSESSOR:
            return qs.filter(assessment__assessor=user)
        if user.role == Role.REVIEWER:
            return qs.filter(assessment__reviewer=user)
        return qs.none()

    def _check_editable(self, clause_assessment):
        if clause_assessment.assessment.status != AssessmentStatus.UNDER_ASSESSMENT:
            raise PermissionDenied(
                "بندها فقط در وضعیت «در حال ارزیابی» قابل ویرایش هستند."
            )

    def perform_update(self, serializer):
        self._check_editable(serializer.instance)
        old_status = serializer.instance.status
        instance = serializer.save()
        if instance.status != old_status:
            log_event(self.request, action="status_change",
                      model="assessments.ClauseAssessment",
                      object_id=str(instance.pk), object_repr=str(instance),
                      changes={"status": [old_status, instance.status]})
        else:
            log_event(self.request, action="update",
                      model="assessments.ClauseAssessment",
                      object_id=str(instance.pk), object_repr=str(instance))

    @action(detail=True, methods=["post"], url_path="reset-text")
    def reset_text(self, request, pk=None):
        ca = self.get_object()
        self._check_editable(ca)
        ca.text_edited = False
        ca.text = ca.render_default_text()
        ca.updated_by = request.user
        ca.save()
        log_event(request, action="update", model="assessments.ClauseAssessment",
                  object_id=str(ca.pk), object_repr=str(ca),
                  changes={"text": "reset_to_default"})
        return Response(ClauseAssessmentSerializer(ca).data)


class SubClauseAssessmentViewSet(
    mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet
):
    """PATCH status/notes on a single sub-clause. The parent ClauseAssessment
    verdict is recomputed automatically after every change."""

    serializer_class = SubClauseAssessmentSerializer
    permission_classes = [RolePermission, IsAssignedOrElevated]
    allowed_roles = {
        "retrieve": ALL_ROLES,
        "update": frozenset({Role.ADMIN, Role.QA_LEAD, Role.ASSESSOR}),
        "partial_update": frozenset({Role.ADMIN, Role.QA_LEAD, Role.ASSESSOR}),
    }

    def get_queryset(self):
        qs = SubClauseAssessment.objects.select_related(
            "sub_clause",
            "clause_assessment",
            "clause_assessment__assessment",
            "clause_assessment__clause",
        )
        user = self.request.user
        if user.is_elevated:
            return qs
        if user.role == Role.ASSESSOR:
            return qs.filter(clause_assessment__assessment__assessor=user)
        if user.role == Role.REVIEWER:
            return qs.filter(clause_assessment__assessment__reviewer=user)
        return qs.none()

    def perform_update(self, serializer):
        instance = serializer.instance
        if (
            instance.clause_assessment.assessment.status
            != AssessmentStatus.UNDER_ASSESSMENT
        ):
            raise PermissionDenied(
                "بندها فقط در وضعیت «در حال ارزیابی» قابل ویرایش هستند."
            )
        old_status = instance.status
        instance = serializer.save(updated_by=self.request.user)
        if instance.status != old_status:
            instance.clause_assessment.recompute_status(user=self.request.user)
            log_event(self.request, action="status_change",
                      model="assessments.SubClauseAssessment",
                      object_id=str(instance.pk), object_repr=str(instance),
                      changes={"status": [old_status, instance.status]})
        else:
            log_event(self.request, action="update",
                      model="assessments.SubClauseAssessment",
                      object_id=str(instance.pk), object_repr=str(instance))


class AttachmentViewSet(
    mixins.RetrieveModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet
):
    serializer_class = AttachmentSerializer
    permission_classes = [RolePermission, IsAssignedOrElevated]
    allowed_roles = {
        "retrieve": ALL_ROLES,
        "destroy": frozenset({Role.ADMIN, Role.QA_LEAD, Role.ASSESSOR}),
        "download": ALL_ROLES,
    }

    def get_queryset(self):
        qs = Attachment.objects.select_related("assessment")
        user = self.request.user
        if user.is_elevated:
            return qs
        if user.role == Role.ASSESSOR:
            return qs.filter(assessment__assessor=user)
        if user.role == Role.REVIEWER:
            return qs.filter(assessment__reviewer=user)
        return qs.none()

    def perform_destroy(self, instance):
        repr_, pk = instance.original_name, instance.pk
        instance.file.delete(save=False)
        instance.delete()
        log_event(self.request, action="delete", model="assessments.Attachment",
                  object_id=str(pk), object_repr=repr_)

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        attachment = self.get_object()
        response = FileResponse(
            attachment.file.open("rb"),
            as_attachment=True,
            filename=attachment.original_name,
        )
        # Force download; never render user content in the browser.
        response["X-Content-Type-Options"] = "nosniff"
        response["Content-Type"] = "application/octet-stream"
        return response
