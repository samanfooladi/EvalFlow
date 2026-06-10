from django.db.models import Count
from rest_framework import viewsets

from apps.accounts.permissions import ADMIN_ONLY, ALL_ROLES, RolePermission
from apps.catalog.views import AuditedModelViewSet

from .models import Clause, DefaultTextTemplate, Framework, Requirement
from .serializers import (
    ClauseSerializer,
    DefaultTextTemplateSerializer,
    FrameworkDetailSerializer,
    FrameworkSerializer,
    RequirementSerializer,
    RequirementWriteSerializer,
)

_READ_ALL_WRITE_ADMIN = {
    "list": ALL_ROLES,
    "retrieve": ALL_ROLES,
    "create": ADMIN_ONLY,
    "update": ADMIN_ONLY,
    "partial_update": ADMIN_ONLY,
    "destroy": ADMIN_ONLY,
}


class FrameworkViewSet(AuditedModelViewSet):
    permission_classes = [RolePermission]
    allowed_roles = _READ_ALL_WRITE_ADMIN
    audit_model = "frameworks.Framework"

    def get_queryset(self):
        return Framework.objects.annotate(
            requirements_count=Count("requirements", distinct=True),
            clauses_count=Count("requirements__clauses", distinct=True),
        )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return FrameworkDetailSerializer
        return FrameworkSerializer


class RequirementViewSet(AuditedModelViewSet):
    permission_classes = [RolePermission]
    allowed_roles = _READ_ALL_WRITE_ADMIN
    audit_model = "frameworks.Requirement"

    def get_queryset(self):
        qs = Requirement.objects.prefetch_related("clauses")
        if framework := self.request.query_params.get("framework"):
            qs = qs.filter(framework_id=framework)
        return qs

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return RequirementWriteSerializer
        return RequirementSerializer


class ClauseViewSet(AuditedModelViewSet):
    serializer_class = ClauseSerializer
    permission_classes = [RolePermission]
    allowed_roles = _READ_ALL_WRITE_ADMIN
    audit_model = "frameworks.Clause"

    def get_queryset(self):
        qs = Clause.objects.select_related("requirement")
        if requirement := self.request.query_params.get("requirement"):
            qs = qs.filter(requirement_id=requirement)
        return qs


class DefaultTextTemplateViewSet(AuditedModelViewSet):
    serializer_class = DefaultTextTemplateSerializer
    permission_classes = [RolePermission]
    allowed_roles = _READ_ALL_WRITE_ADMIN
    audit_model = "frameworks.DefaultTextTemplate"

    def get_queryset(self):
        qs = DefaultTextTemplate.objects.all()
        if framework := self.request.query_params.get("framework"):
            qs = qs.filter(framework_id=framework)
        return qs
