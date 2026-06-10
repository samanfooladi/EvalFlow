from rest_framework import viewsets

from apps.accounts.permissions import ELEVATED, RolePermission

from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditLogSerializer
    permission_classes = [RolePermission]
    allowed_roles = {"list": ELEVATED, "retrieve": ELEVATED}

    def get_queryset(self):
        qs = AuditLog.objects.select_related("actor")
        params = self.request.query_params
        if actor := params.get("actor"):
            qs = qs.filter(actor__username=actor)
        if action := params.get("action"):
            qs = qs.filter(action=action)
        if date_from := params.get("date_from"):
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to := params.get("date_to"):
            qs = qs.filter(created_at__date__lte=date_to)
        return qs
