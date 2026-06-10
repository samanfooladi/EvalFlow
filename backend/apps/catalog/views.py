from django.db.models import Count, ProtectedError
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError

from apps.accounts.permissions import ALL_ROLES, ELEVATED, RolePermission
from apps.audit.services import log_event

from .models import Company, ProductSystem
from .serializers import CompanySerializer, ProductSystemSerializer

_READ_ALL_WRITE_ELEVATED = {
    "list": ALL_ROLES,
    "retrieve": ALL_ROLES,
    "create": ELEVATED,
    "update": ELEVATED,
    "partial_update": ELEVATED,
    "destroy": ELEVATED,
}


class AuditedModelViewSet(viewsets.ModelViewSet):
    """ModelViewSet that writes an audit row for every mutation."""

    audit_model = ""

    def perform_create(self, serializer):
        instance = serializer.save()
        log_event(self.request, action="create", model=self.audit_model,
                  object_id=str(instance.pk), object_repr=str(instance))

    def perform_update(self, serializer):
        instance = serializer.save()
        log_event(self.request, action="update", model=self.audit_model,
                  object_id=str(instance.pk), object_repr=str(instance),
                  changes={k: str(v)[:200] for k, v in serializer.validated_data.items()})

    def perform_destroy(self, instance):
        repr_, pk = str(instance), instance.pk
        try:
            instance.delete()
        except ProtectedError:
            raise ValidationError(
                {"detail": "این مورد دارای وابستگی است و قابل حذف نیست."}
            )
        log_event(self.request, action="delete", model=self.audit_model,
                  object_id=str(pk), object_repr=repr_)


class CompanyViewSet(AuditedModelViewSet):
    serializer_class = CompanySerializer
    permission_classes = [RolePermission]
    allowed_roles = _READ_ALL_WRITE_ELEVATED
    audit_model = "catalog.Company"

    def get_queryset(self):
        return Company.objects.annotate(systems_count=Count("systems"))

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        log_event(self.request, action="create", model=self.audit_model,
                  object_id=str(instance.pk), object_repr=str(instance))


class ProductSystemViewSet(AuditedModelViewSet):
    serializer_class = ProductSystemSerializer
    permission_classes = [RolePermission]
    allowed_roles = _READ_ALL_WRITE_ELEVATED
    audit_model = "catalog.ProductSystem"

    def get_queryset(self):
        qs = ProductSystem.objects.select_related("company")
        if company := self.request.query_params.get("company"):
            qs = qs.filter(company_id=company)
        return qs
