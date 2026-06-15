"""Clause-text image library: upload returns placeholder tokens, scoped
strictly to (clause assessment, uploading user); inline serving is
similarly scoped."""
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.assessments.models import AssessmentStatus, Assessment
from apps.catalog.models import Company, ProductSystem
from apps.frameworks.models import Clause, Framework, Requirement, SubClause

from .factories import AssessorFactory, ReviewerFactory

pytestmark = pytest.mark.django_db

PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
)
PDF_BYTES = b"%PDF-1.4\n%test pdf content\n"


@pytest.fixture
def assessment(db):
    fw = Framework.objects.create(code="img-fw", title="t", kind="TRP")
    req = Requirement.objects.create(
        framework=fw, klass_title="کلاس", code="IMG.1", title="الزام", order=1
    )
    clause = Clause.objects.create(
        requirement=req, code="IMG.1.1", title="بند", description="شرح", order=1
    )
    SubClause.objects.create(clause=clause, text="شرح", order=0)
    company = Company.objects.create(name="شرکت تصویر")
    system = ProductSystem.objects.create(company=company, name="سامانه")
    a = Assessment.objects.create(
        system=system, framework=fw, assessor=AssessorFactory(),
        reviewer=ReviewerFactory(),
    )
    a.create_clause_assessments()
    return a


def upload(api, ca, content=PNG_BYTES, name="screenshot.png", content_type="image/png"):
    return api.post(
        f"/api/v1/clause-assessments/{ca.pk}/images/",
        {"file": SimpleUploadedFile(name, content, content_type=content_type)},
        format="multipart",
    )


def test_upload_returns_placeholder_token(api, as_user, assessment):
    ca = assessment.clause_assessments.first()
    as_user(assessment.assessor)
    r = upload(api, ca)
    assert r.status_code == 201, r.content
    assert r.data["filename_slug"] == "screenshot"
    assert r.data["placeholder_token"] == "[[screenshot]]"
    assert r.data["url"].endswith("/inline/")
    assert "file" not in r.data


def test_duplicate_filenames_get_unique_slugs(api, as_user, assessment):
    ca = assessment.clause_assessments.first()
    as_user(assessment.assessor)
    r1 = upload(api, ca)
    r2 = upload(api, ca)
    assert r1.data["filename_slug"] == "screenshot"
    assert r2.data["filename_slug"] == "screenshot-2"


def test_non_image_rejected(api, as_user, assessment):
    ca = assessment.clause_assessments.first()
    as_user(assessment.assessor)
    r = upload(api, ca, content=PDF_BYTES, name="report.pdf", content_type="application/pdf")
    assert r.status_code == 400


def test_reviewer_cannot_upload(api, as_user, assessment):
    ca = assessment.clause_assessments.first()
    as_user(assessment.reviewer)
    r = upload(api, ca)
    assert r.status_code == 403


def test_upload_blocked_outside_under_assessment(api, as_user, assessment):
    ca = assessment.clause_assessments.first()
    assessment.status = AssessmentStatus.UNDER_REVIEW
    assessment.save()
    as_user(assessment.assessor)
    r = upload(api, ca)
    assert r.status_code == 403


def test_images_scoped_to_uploading_user(api, as_user, assessment):
    """Each user only sees their own images for the clause — the assigned
    reviewer must not see the assessor's uploads."""
    ca = assessment.clause_assessments.first()
    as_user(assessment.assessor)
    upload(api, ca)

    as_user(assessment.reviewer)
    r = api.get(f"/api/v1/clause-assessments/{ca.pk}/images/")
    assert r.status_code == 200
    assert r.data == []

    as_user(assessment.assessor)
    r = api.get(f"/api/v1/clause-assessments/{ca.pk}/images/")
    assert r.status_code == 200
    assert len(r.data) == 1


def test_inline_serves_image_and_is_scoped_to_owner(api, as_user, assessment):
    ca = assessment.clause_assessments.first()
    as_user(assessment.assessor)
    uploaded = upload(api, ca)
    url = uploaded.data["url"]

    r = api.get(f"/api/v1{url}")
    assert r.status_code == 200
    assert r["Content-Disposition"] == "inline"
    assert r["X-Content-Type-Options"] == "nosniff"
    assert r["Content-Type"] == "image/png"

    # The assigned reviewer can see the assessment, but not this user's
    # image library — strictly scoped to (clause_assessment, uploaded_by).
    as_user(assessment.reviewer)
    r = api.get(f"/api/v1{url}")
    assert r.status_code == 403


def test_unassigned_user_cannot_list_or_upload(api, as_user, assessment):
    ca = assessment.clause_assessments.first()
    as_user(AssessorFactory())
    r = api.get(f"/api/v1/clause-assessments/{ca.pk}/images/")
    assert r.status_code == 404
    r = upload(api, ca)
    assert r.status_code == 404


def test_upload_audited(api, as_user, assessment):
    from apps.audit.models import AuditLog

    ca = assessment.clause_assessments.first()
    as_user(assessment.assessor)
    upload(api, ca)
    assert AuditLog.objects.filter(action="upload", object_repr="screenshot.png").exists()
