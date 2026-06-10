"""API integration tests: assessment lifecycle, clause editing, filters,
IDOR guards."""
import pytest

from apps.assessments.models import Assessment, AssessmentStatus
from apps.catalog.models import Company, ProductSystem
from apps.frameworks.models import (
    Clause,
    ClauseStatus,
    DefaultTextTemplate,
    Framework,
    Requirement,
)

from .factories import (
    AdminFactory,
    AssessorFactory,
    QALeadFactory,
    ReviewerFactory,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def setup(db):
    fw = Framework.objects.create(code="t-fw", title="چارچوب", kind="TRP")
    req = Requirement.objects.create(
        framework=fw, klass_title="کلاس آزمایشی", code="REQ.1",
        title="الزام نمونه", guidance="راهنما", order=1,
    )
    for i in (1, 2, 3):
        Clause.objects.create(
            requirement=req, code=f"REQ.1.{i}", title=f"بند {i}",
            description=f"شرح بند {i}", objective="هدف", order=i,
        )
    DefaultTextTemplate.objects.create(
        framework=fw, status="finding",
        template="عدم انطباق در {{clause_code}}: ",
    )
    company = Company.objects.create(name="شرکت یک")
    system = ProductSystem.objects.create(company=company, name="سامانه یک")
    assessor, reviewer = AssessorFactory(), ReviewerFactory()
    assessment = Assessment.objects.create(
        system=system, framework=fw, assessor=assessor, reviewer=reviewer
    )
    assessment.create_clause_assessments()
    return {
        "framework": fw, "company": company, "system": system,
        "assessment": assessment, "assessor": assessor, "reviewer": reviewer,
    }


# ---------- companies / systems ----------

def test_company_crud_elevated_only(api, as_user, setup):
    qa = QALeadFactory()
    as_user(qa)
    r = api.post("/api/v1/companies/", {"name": "شرکت دو"}, format="json")
    assert r.status_code == 201
    as_user(setup["assessor"])
    r = api.post("/api/v1/companies/", {"name": "شرکت سه"}, format="json")
    assert r.status_code == 403
    r = api.get("/api/v1/companies/")
    assert r.status_code == 200


def test_company_duplicate_name_rejected(api, as_user, setup):
    as_user(AdminFactory())
    r = api.post("/api/v1/companies/", {"name": "شرکت یک"}, format="json")
    assert r.status_code == 400


def test_protected_company_delete_handled(api, as_user, setup):
    as_user(AdminFactory())
    r = api.delete(f"/api/v1/companies/{setup['company'].pk}/")
    assert r.status_code == 400  # has systems -> ProtectedError -> 400


def test_systems_filter_by_company(api, as_user, setup):
    as_user(setup["assessor"])
    r = api.get(f"/api/v1/systems/?company={setup['company'].pk}")
    assert r.status_code == 200
    assert r.data["count"] == 1


# ---------- frameworks ----------

def test_framework_write_admin_only(api, as_user, setup):
    qa = QALeadFactory()
    as_user(qa)
    r = api.patch(
        f"/api/v1/frameworks/{setup['framework'].pk}/",
        {"title": "x"}, format="json",
    )
    assert r.status_code == 403
    as_user(AdminFactory())
    r = api.patch(
        f"/api/v1/frameworks/{setup['framework'].pk}/",
        {"title": "عنوان جدید"}, format="json",
    )
    assert r.status_code == 200


def test_framework_detail_includes_requirements(api, as_user, setup):
    as_user(setup["assessor"])
    r = api.get(f"/api/v1/frameworks/{setup['framework'].pk}/")
    assert r.status_code == 200
    assert len(r.data["requirements"]) == 1
    assert len(r.data["requirements"][0]["clauses"]) == 3


# ---------- assessments ----------

def test_assessment_create_fans_out_clauses(api, as_user, setup):
    as_user(QALeadFactory())
    r = api.post(
        "/api/v1/assessments/",
        {
            "system": setup["system"].pk,
            "framework": setup["framework"].pk,
            "assessor": AssessorFactory().pk,
        },
        format="json",
    )
    assert r.status_code == 201, r.content
    assessment = Assessment.objects.get(pk=r.data["id"])
    assert assessment.clause_assessments.count() == 3


def test_assessment_create_rejects_wrong_role_assessor(api, as_user, setup):
    as_user(AdminFactory())
    r = api.post(
        "/api/v1/assessments/",
        {
            "system": setup["system"].pk,
            "framework": setup["framework"].pk,
            "assessor": ReviewerFactory().pk,  # wrong role
        },
        format="json",
    )
    assert r.status_code == 400


def test_assessor_sees_only_own_assessments(api, as_user, setup):
    other = AssessorFactory()
    Assessment.objects.create(
        system=setup["system"], framework=setup["framework"], assessor=other
    )
    as_user(setup["assessor"])
    r = api.get("/api/v1/assessments/")
    assert r.data["count"] == 1
    assert r.data["results"][0]["id"] == setup["assessment"].pk


def test_idor_unassigned_assessment_404(api, as_user, setup):
    """Scoped querysets: outsiders get 404, not 403 — no existence oracle."""
    other = AssessorFactory()
    as_user(other)
    r = api.get(f"/api/v1/assessments/{setup['assessment'].pk}/")
    assert r.status_code == 404


def test_status_not_writable_via_patch(api, as_user, setup):
    as_user(setup["assessor"])
    r = api.patch(
        f"/api/v1/assessments/{setup['assessment'].pk}/",
        {"status": "completed", "tester_code": "AS-09"},
        format="json",
    )
    assert r.status_code == 200
    setup["assessment"].refresh_from_db()
    assert setup["assessment"].status == AssessmentStatus.UNDER_ASSESSMENT
    assert setup["assessment"].tester_code == "AS-09"


def test_transition_endpoint_full_cycle(api, as_user, setup):
    a = setup["assessment"]
    as_user(setup["assessor"])
    r = api.post(
        f"/api/v1/assessments/{a.pk}/transition/",
        {"status": "under_review"}, format="json",
    )
    assert r.status_code == 200
    as_user(setup["reviewer"])
    r = api.post(
        f"/api/v1/assessments/{a.pk}/transition/",
        {"status": "completed"}, format="json",
    )
    assert r.status_code == 200
    a.refresh_from_db()
    assert a.status == AssessmentStatus.COMPLETED


def test_transition_invalid_edge_400(api, as_user, setup):
    as_user(AdminFactory())
    r = api.post(
        f"/api/v1/assessments/{setup['assessment'].pk}/transition/",
        {"status": "completed"}, format="json",
    )
    assert r.status_code == 400


def test_assessor_cannot_edit_after_submission(api, as_user, setup):
    a = setup["assessment"]
    a.status = AssessmentStatus.UNDER_REVIEW
    a.save()
    as_user(setup["assessor"])
    r = api.patch(
        f"/api/v1/assessments/{a.pk}/",
        {"tester_code": "HACK"}, format="json",
    )
    assert r.status_code == 403


# ---------- clause assessments ----------

def test_clause_list_with_status_filter(api, as_user, setup):
    a = setup["assessment"]
    ca = a.clause_assessments.first()
    ca.apply_status(ClauseStatus.FINDING)
    as_user(setup["assessor"])
    r = api.get(f"/api/v1/assessments/{a.pk}/clause-assessments/?status=finding")
    assert r.status_code == 200
    assert len(r.data) == 1
    assert r.data[0]["clause_code"] == ca.clause.code
    assert r.data[0]["guidance"] == "راهنما"


def test_clause_status_change_renders_default_text(api, as_user, setup):
    a = setup["assessment"]
    ca = a.clause_assessments.first()
    as_user(setup["assessor"])
    r = api.patch(
        f"/api/v1/clause-assessments/{ca.pk}/",
        {"status": "finding"}, format="json",
    )
    assert r.status_code == 200
    assert r.data["text"].startswith("عدم انطباق در REQ.1.1")


def test_clause_text_edit_marks_edited_and_persists(api, as_user, setup):
    a = setup["assessment"]
    ca = a.clause_assessments.first()
    as_user(setup["assessor"])
    api.patch(
        f"/api/v1/clause-assessments/{ca.pk}/",
        {"status": "finding", "text": "متن سفارشی ارزیاب"}, format="json",
    )
    ca.refresh_from_db()
    assert ca.text == "متن سفارشی ارزیاب"
    assert ca.text_edited is True
    # later status change must not clobber the custom text
    api.patch(
        f"/api/v1/clause-assessments/{ca.pk}/",
        {"status": "compliant"}, format="json",
    )
    ca.refresh_from_db()
    assert ca.text == "متن سفارشی ارزیاب"


def test_clause_reset_text(api, as_user, setup):
    a = setup["assessment"]
    ca = a.clause_assessments.first()
    as_user(setup["assessor"])
    api.patch(
        f"/api/v1/clause-assessments/{ca.pk}/",
        {"status": "finding", "text": "دست‌نویس"}, format="json",
    )
    r = api.post(f"/api/v1/clause-assessments/{ca.pk}/reset-text/")
    assert r.status_code == 200
    assert r.data["text"].startswith("عدم انطباق در")
    assert r.data["text_edited"] is False


def test_clause_locked_outside_under_assessment(api, as_user, setup):
    a = setup["assessment"]
    a.status = AssessmentStatus.UNDER_REVIEW
    a.save()
    ca = a.clause_assessments.first()
    as_user(setup["assessor"])
    r = api.patch(
        f"/api/v1/clause-assessments/{ca.pk}/",
        {"status": "compliant"}, format="json",
    )
    assert r.status_code == 403


def test_reviewer_cannot_patch_clauses(api, as_user, setup):
    ca = setup["assessment"].clause_assessments.first()
    as_user(setup["reviewer"])
    r = api.patch(
        f"/api/v1/clause-assessments/{ca.pk}/",
        {"status": "compliant"}, format="json",
    )
    assert r.status_code == 403


def test_idor_clause_assessment_of_other_assessor_404(api, as_user, setup):
    other = AssessorFactory()
    as_user(other)
    ca = setup["assessment"].clause_assessments.first()
    r = api.patch(
        f"/api/v1/clause-assessments/{ca.pk}/",
        {"status": "compliant"}, format="json",
    )
    assert r.status_code == 404
