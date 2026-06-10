"""Attachment upload security tests: magic-byte sniffing, size limits,
double extensions, traversal names, role checks, download hygiene."""
import io
import zipfile

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.assessments.models import Assessment
from apps.catalog.models import Company, ProductSystem
from apps.frameworks.models import Framework

from .factories import AssessorFactory, ReviewerFactory

pytestmark = pytest.mark.django_db

PDF_BYTES = b"%PDF-1.4\n%test pdf content\n"
PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
)
EXE_BYTES = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00"


@pytest.fixture
def assessment(db):
    fw = Framework.objects.create(code="up-fw", title="t", kind="TRP")
    company = Company.objects.create(name="شرکت بارگذاری")
    system = ProductSystem.objects.create(company=company, name="سامانه")
    return Assessment.objects.create(
        system=system, framework=fw, assessor=AssessorFactory(),
        reviewer=ReviewerFactory(),
    )


def upload(api, assessment, name, content, content_type="application/octet-stream"):
    return api.post(
        f"/api/v1/assessments/{assessment.pk}/attachments/",
        {"file": SimpleUploadedFile(name, content, content_type=content_type)},
        format="multipart",
    )


def test_valid_pdf_upload(api, as_user, assessment):
    as_user(assessment.assessor)
    r = upload(api, assessment, "گزارش.pdf", PDF_BYTES, "application/pdf")
    assert r.status_code == 201, r.content
    assert r.data["original_name"] == "گزارش.pdf"
    # stored name is randomized — uuid hex, never the user-supplied name
    att = assessment.attachments.first()
    assert "گزارش" not in att.file.name
    assert att.file.name.endswith(".pdf")


def test_disallowed_extension_rejected(api, as_user, assessment):
    as_user(assessment.assessor)
    r = upload(api, assessment, "shell.php", b"<?php echo 1;")
    assert r.status_code == 400


def test_exe_masquerading_as_pdf_rejected(api, as_user, assessment):
    as_user(assessment.assessor)
    r = upload(api, assessment, "report.pdf", EXE_BYTES, "application/pdf")
    assert r.status_code == 400


def test_double_extension_uses_final_suffix(api, as_user, assessment):
    as_user(assessment.assessor)
    # report.pdf.exe -> final suffix .exe -> rejected
    r = upload(api, assessment, "report.pdf.exe", EXE_BYTES)
    assert r.status_code == 400


def test_oversize_rejected(api, as_user, assessment, settings):
    settings.UPLOAD_MAX_BYTES = 1024
    as_user(assessment.assessor)
    r = upload(api, assessment, "big.pdf", PDF_BYTES + b"x" * 2048, "application/pdf")
    assert r.status_code == 400


def test_traversal_filename_neutralized(api, as_user, assessment):
    as_user(assessment.assessor)
    r = upload(api, assessment, "../../etc/passwd.png", PNG_BYTES, "image/png")
    assert r.status_code == 201
    att = assessment.attachments.first()
    assert ".." not in att.file.name
    assert "etc" not in att.file.name


def test_docx_zip_content_accepted(api, as_user, assessment):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", "<w:document/>")
    as_user(assessment.assessor)
    r = upload(api, assessment, "evidence.docx", buf.getvalue())
    assert r.status_code == 201


def test_reviewer_cannot_upload_but_can_list(api, as_user, assessment):
    as_user(assessment.reviewer)
    r = upload(api, assessment, "x.pdf", PDF_BYTES, "application/pdf")
    assert r.status_code == 403
    r = api.get(f"/api/v1/assessments/{assessment.pk}/attachments/")
    assert r.status_code == 200


def test_unassigned_assessor_cannot_upload(api, as_user, assessment):
    as_user(AssessorFactory())
    r = upload(api, assessment, "x.pdf", PDF_BYTES, "application/pdf")
    assert r.status_code == 404  # scoped queryset


def test_download_forces_attachment(api, as_user, assessment):
    as_user(assessment.assessor)
    upload(api, assessment, "evidence.png", PNG_BYTES, "image/png")
    att = assessment.attachments.first()
    r = api.get(f"/api/v1/attachments/{att.pk}/download/")
    assert r.status_code == 200
    assert "attachment" in r["Content-Disposition"]
    assert r["Content-Type"] == "application/octet-stream"
    assert r["X-Content-Type-Options"] == "nosniff"


def test_upload_audited(api, as_user, assessment):
    from apps.audit.models import AuditLog

    as_user(assessment.assessor)
    upload(api, assessment, "log.pdf", PDF_BYTES, "application/pdf")
    assert AuditLog.objects.filter(action="upload").exists()
