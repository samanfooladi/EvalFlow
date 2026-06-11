import pytest
from django.core.management import call_command
from django.db import IntegrityError

from apps.assessments.models import Assessment
from apps.catalog.models import Company, ProductSystem
from apps.frameworks.models import (
    Clause,
    ClauseStatus,
    DefaultTextTemplate,
    Framework,
    Requirement,
)

from .factories import AssessorFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def framework(db):
    fw = Framework.objects.create(code="test-fw", title="چارچوب آزمایشی", kind="TRP")
    req = Requirement.objects.create(
        framework=fw, klass_title="کلاس ممیزی امنیت", code="FAU_GEN.1",
        title="تولید داده ممیزی", guidance="راهنمای آزمون این الزام", order=1,
    )
    Clause.objects.create(
        requirement=req, code="FAU_GEN.1.1", title="تولید داده ممیزی 1",
        description="FAU_GEN.1.1 (الزام اول)", objective="محصول باید ...", order=1,
    )
    Clause.objects.create(
        requirement=req, code="FAU_GEN.1.2", title="تولید داده ممیزی 2",
        description="FAU_GEN.1.2 (الزام دوم)", objective="محصول باید ...", order=2,
    )
    DefaultTextTemplate.objects.create(
        framework=fw, status="compliant",
        template="آزمون {{clause_code}} روی {{product_name}} انجام شد و قبول است.",
    )
    DefaultTextTemplate.objects.create(
        framework=fw, status="finding",
        template="در آزمون {{clause_code}} عدم انطباق مشاهده شد: ",
    )
    return fw


@pytest.fixture
def assessment(framework):
    company = Company.objects.create(name="شرکت نمونه")
    system = ProductSystem.objects.create(
        company=company, name="سامانه نمونه", version="1.0"
    )
    a = Assessment.objects.create(
        system=system, framework=framework, assessor=AssessorFactory()
    )
    a.create_clause_assessments()
    return a


def test_clause_assessment_fanout(assessment):
    assert assessment.clause_assessments.count() == 2
    assert set(
        assessment.clause_assessments.values_list("status", flat=True)
    ) == {ClauseStatus.UNREVIEWED}
    # idempotent
    assessment.create_clause_assessments()
    assert assessment.clause_assessments.count() == 2


def test_assessment_kind_denormalized(assessment):
    assert assessment.kind == "TRP"


def test_default_text_rendered_on_status_change(assessment):
    ca = assessment.clause_assessments.first()
    ca.apply_status(ClauseStatus.COMPLIANT)
    assert "FAU_GEN.1.1" in ca.text
    assert "سامانه نمونه" in ca.text


def test_edited_text_not_overwritten(assessment):
    ca = assessment.clause_assessments.first()
    ca.apply_status(ClauseStatus.COMPLIANT)
    ca.text = "متن ویرایش‌شده توسط ارزیاب"
    ca.text_edited = True
    ca.save()
    ca.apply_status(ClauseStatus.FINDING)
    assert ca.text == "متن ویرایش‌شده توسط ارزیاب"
    assert ca.status == ClauseStatus.FINDING


def test_template_render_ignores_unknown_placeholders(framework):
    tpl = framework.default_texts.get(status="compliant")
    out = tpl.render({"clause_code": "X", "product_name": "Y"})
    assert "{{" not in out


def test_compliance_percent(assessment):
    cas = list(assessment.clause_assessments.all())
    cas[0].apply_status(ClauseStatus.COMPLIANT)
    cas[1].apply_status(ClauseStatus.NOT_APPLICABLE)
    # basis = 2 - 1 = 1; compliant = 1 -> 100%
    assert assessment.compliance_percent == 100


def test_compliance_percent_none_when_all_na(assessment):
    for ca in assessment.clause_assessments.all():
        ca.apply_status(ClauseStatus.NOT_APPLICABLE)
    assert assessment.compliance_percent is None


def test_unique_clause_per_assessment(assessment):
    ca = assessment.clause_assessments.first()
    with pytest.raises(IntegrityError):
        type(ca).objects.create(assessment=assessment, clause=ca.clause)


def test_load_frameworks_command(db):
    call_command("load_frameworks")
    trp = Framework.objects.get(code="napp-cc")
    vtr = Framework.objects.get(code="owasp-otg")
    assert trp.kind == "TRP" and vtr.kind == "VTR"
    assert trp.requirements.count() >= 40
    assert Clause.objects.filter(requirement__framework=trp).count() >= 75
    assert vtr.requirements.count() == 13
    assert trp.default_texts.count() == 3
    # idempotent re-run does not duplicate
    n_before = Clause.objects.count()
    call_command("load_frameworks")
    assert Clause.objects.count() == n_before
    # spot-check Persian content survived the round trip
    clause = Clause.objects.get(
        requirement__framework=trp, code="FAU_GEN.1.1"
    )
    assert "ممیزی" in clause.title
    assert clause.objective
