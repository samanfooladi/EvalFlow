"""Assessment workflow state machine.

Transitions happen ONLY through this service — the status field is
read-only in every serializer. Allowed edges per role:

  Admin / QA Lead : any edge
  Assessor (own)  : under_assessment -> under_review
  Reviewer (own)  : under_review -> completed
                    under_review -> under_assessment   (send back to fix)
"""
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.models import Role
from apps.audit.services import log_event

from .models import Assessment, AssessmentStatus

_ALL_EDGES = {
    (AssessmentStatus.UNDER_ASSESSMENT, AssessmentStatus.UNDER_REVIEW),
    (AssessmentStatus.UNDER_REVIEW, AssessmentStatus.COMPLETED),
    (AssessmentStatus.UNDER_REVIEW, AssessmentStatus.UNDER_ASSESSMENT),
    (AssessmentStatus.COMPLETED, AssessmentStatus.UNDER_REVIEW),
}

_ROLE_EDGES = {
    Role.ADMIN: _ALL_EDGES,
    Role.QA_LEAD: _ALL_EDGES,
    Role.ASSESSOR: {
        (AssessmentStatus.UNDER_ASSESSMENT, AssessmentStatus.UNDER_REVIEW),
    },
    Role.REVIEWER: {
        (AssessmentStatus.UNDER_REVIEW, AssessmentStatus.COMPLETED),
        (AssessmentStatus.UNDER_REVIEW, AssessmentStatus.UNDER_ASSESSMENT),
    },
}


def transition(assessment: Assessment, to_status: str, user, request=None) -> Assessment:
    if to_status not in AssessmentStatus.values:
        raise ValidationError({"status": "وضعیت نامعتبر است."})

    edge = (assessment.status, to_status)
    if edge not in _ALL_EDGES:
        raise ValidationError(
            {"status": f"گذار از «{assessment.get_status_display()}» به این وضعیت مجاز نیست."}
        )
    if edge not in _ROLE_EDGES.get(user.role, set()):
        raise PermissionDenied("شما مجاز به انجام این گذار نیستید.")

    # Assessors/reviewers may only transition their own assessments.
    if user.role == Role.ASSESSOR and assessment.assessor_id != user.id:
        raise PermissionDenied("این ارزیابی به شما تخصیص داده نشده است.")
    if user.role == Role.REVIEWER and assessment.reviewer_id != user.id:
        raise PermissionDenied("بازبینی این ارزیابی به شما تخصیص داده نشده است.")

    old_status = assessment.status
    assessment.status = to_status
    assessment.save(update_fields=["status", "updated_at"])
    log_event(
        request,
        action="status_change",
        model="assessments.Assessment",
        object_id=str(assessment.pk),
        object_repr=str(assessment),
        changes={"status": [old_status, to_status]},
        actor=user,
    )
    return assessment
