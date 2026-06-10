import pytest
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.assessments.models import Assessment, AssessmentStatus
from apps.assessments.transitions import transition
from apps.audit.models import AuditLog
from apps.catalog.models import Company, ProductSystem
from apps.frameworks.models import Framework

from .factories import (
    AdminFactory,
    AssessorFactory,
    QALeadFactory,
    ReviewerFactory,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def assessment(db):
    fw = Framework.objects.create(code="t", title="t", kind="TRP")
    company = Company.objects.create(name="شرکت")
    system = ProductSystem.objects.create(company=company, name="سامانه")
    return Assessment.objects.create(
        system=system,
        framework=fw,
        assessor=AssessorFactory(),
        reviewer=ReviewerFactory(),
    )


def test_assessor_can_submit_own_for_review(assessment):
    transition(assessment, AssessmentStatus.UNDER_REVIEW, assessment.assessor)
    assert assessment.status == AssessmentStatus.UNDER_REVIEW
    assert AuditLog.objects.filter(action="status_change").exists()


def test_assessor_cannot_submit_others(assessment):
    other = AssessorFactory()
    with pytest.raises(PermissionDenied):
        transition(assessment, AssessmentStatus.UNDER_REVIEW, other)


def test_assessor_cannot_complete(assessment):
    assessment.status = AssessmentStatus.UNDER_REVIEW
    assessment.save()
    with pytest.raises(PermissionDenied):
        transition(assessment, AssessmentStatus.COMPLETED, assessment.assessor)


def test_reviewer_completes_own(assessment):
    assessment.status = AssessmentStatus.UNDER_REVIEW
    assessment.save()
    transition(assessment, AssessmentStatus.COMPLETED, assessment.reviewer)
    assert assessment.status == AssessmentStatus.COMPLETED


def test_reviewer_sends_back_for_correction(assessment):
    assessment.status = AssessmentStatus.UNDER_REVIEW
    assessment.save()
    transition(assessment, AssessmentStatus.UNDER_ASSESSMENT, assessment.reviewer)
    assert assessment.status == AssessmentStatus.UNDER_ASSESSMENT


def test_invalid_edge_rejected(assessment):
    # under_assessment -> completed skips review
    with pytest.raises(ValidationError):
        transition(assessment, AssessmentStatus.COMPLETED, AdminFactory())


def test_unknown_status_rejected(assessment):
    with pytest.raises(ValidationError):
        transition(assessment, "archived", AdminFactory())


def test_qa_lead_can_reopen_completed(assessment):
    assessment.status = AssessmentStatus.COMPLETED
    assessment.save()
    transition(assessment, AssessmentStatus.UNDER_REVIEW, QALeadFactory())
    assert assessment.status == AssessmentStatus.UNDER_REVIEW
