"""Single source of role-based access control.

Usage:
    class CompanyViewSet(ModelViewSet):
        permission_classes = [RolePermission]
        allowed_roles = {
            "list": ALL_ROLES,
            "retrieve": ALL_ROLES,
            "create": ELEVATED,
            "update": ELEVATED,
            "partial_update": ELEVATED,
            "destroy": ELEVATED,
        }

For plain APIViews the mapping key is the lowercase HTTP method
("get", "post", ...). Anything not listed is denied.
"""
from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import Role

ALL_ROLES = frozenset({Role.ADMIN, Role.ASSESSOR, Role.REVIEWER, Role.QA_LEAD})
ELEVATED = frozenset({Role.ADMIN, Role.QA_LEAD})
ADMIN_ONLY = frozenset({Role.ADMIN})


class RolePermission(BasePermission):
    """Deny-by-default declarative role check against ``view.allowed_roles``."""

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        mapping = getattr(view, "allowed_roles", None)
        if mapping is None:
            return False
        action = getattr(view, "action", None) or request.method.lower()
        allowed = mapping.get(action, frozenset())
        return user.role in allowed


class IsAssignedOrElevated(BasePermission):
    """Object-level check: assessors/reviewers may only touch assessments
    they are assigned to; Admin and QA Lead bypass.

    The object must expose ``assessor_id`` and ``reviewer_id`` (Assessment),
    an ``assessment`` relation (ClauseAssessment, Attachment), or a
    ``clause_assessment`` relation (SubClauseAssessment).
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_elevated:
            return True
        if hasattr(obj, "clause_assessment"):
            obj = obj.clause_assessment
        assessment = getattr(obj, "assessment", obj)
        if user.role == Role.ASSESSOR:
            return assessment.assessor_id == user.id
        if user.role == Role.REVIEWER:
            # Reviewers get read access plus the transitions explicitly
            # allowed in their views; writes elsewhere are view-restricted.
            if request.method in SAFE_METHODS:
                return assessment.reviewer_id == user.id
            return assessment.reviewer_id == user.id
        return False
