"""Shared document-building blocks used by the TRP/VTR/BRP generators."""
from __future__ import annotations

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH

from apps.frameworks.models import ClauseStatus

from .docx_utils import (
    RED,
    add_rtl_paragraph,
    build_header_footer,
    make_table,
    set_cell_text,
    set_page_letter,
    shade_cell,
    shamsi_date,
)

LAB_NAME = "مرکز ارزیابی ایمنی و امنیتی تبادل امن"

STATUS_RESULT_TEXT = {
    ClauseStatus.COMPLIANT: "قبول",
    ClauseStatus.FINDING: "عدم انطباق",
    ClauseStatus.NOT_APPLICABLE: "مصداق ندارد",
    ClauseStatus.UNREVIEWED: "",
}


def result_text_and_color(status: str) -> tuple[str, str | None]:
    text = STATUS_RESULT_TEXT.get(status, "")
    color = RED if status == ClauseStatus.FINDING else None
    return text, color


def new_document(*, doc_title: str, assessment, doc_code_prefix: str) -> Document:
    document = Document()
    set_page_letter(document)
    system = assessment.system
    build_header_footer(
        document,
        doc_title=doc_title,
        product=system.name,
        company=system.company.name,
        doc_code=f"{doc_code_prefix}-{system.name}",
    )
    return document


def add_cover(document, *, doc_title: str, assessment) -> None:
    system = assessment.system
    add_rtl_paragraph(document, "به نام خدا", size=14, bold=True,
                      align=WD_ALIGN_PARAGRAPH.CENTER)
    add_rtl_paragraph(document, "", align=WD_ALIGN_PARAGRAPH.CENTER)
    add_rtl_paragraph(document, doc_title, size=20, bold=True,
                      align=WD_ALIGN_PARAGRAPH.CENTER)
    add_rtl_paragraph(document, "", align=WD_ALIGN_PARAGRAPH.CENTER)
    add_rtl_paragraph(document, f"نام محصول: {system.name}", size=13,
                      align=WD_ALIGN_PARAGRAPH.CENTER)
    add_rtl_paragraph(document, f"نام شرکت: {system.company.name}", size=13,
                      align=WD_ALIGN_PARAGRAPH.CENTER)
    add_rtl_paragraph(document, "نام آزمایشگاه:", size=13,
                      align=WD_ALIGN_PARAGRAPH.CENTER)
    add_rtl_paragraph(document, LAB_NAME, size=13, bold=True,
                      align=WD_ALIGN_PARAGRAPH.CENTER)
    add_rtl_paragraph(document, f"نسخه سند: {assessment.doc_version}", size=11,
                      align=WD_ALIGN_PARAGRAPH.CENTER)
    document.add_page_break()


def add_change_log_table(document, assessment, *, min_rows: int = 8) -> None:
    add_rtl_paragraph(document, "تغییرات سند", size=13, bold=True,
                      align=WD_ALIGN_PARAGRAPH.CENTER)
    entries = list(assessment.change_log or [])
    n_rows = max(min_rows, len(entries)) + 1
    table = make_table(document, rows=n_rows, cols=4)
    headers = ["ردیف", "نسخه", "تاریخ", "شرح تغییرات"]
    for col, text in enumerate(headers):
        set_cell_text(table.rows[0].cells[col], text, bold=True,
                      align=WD_ALIGN_PARAGRAPH.CENTER)
        shade_cell(table.rows[0].cells[col])
    for idx in range(1, n_rows):
        entry = entries[idx - 1] if idx - 1 < len(entries) else {}
        set_cell_text(table.rows[idx].cells[0], str(idx),
                      align=WD_ALIGN_PARAGRAPH.CENTER)
        set_cell_text(table.rows[idx].cells[1], str(entry.get("version", "")),
                      align=WD_ALIGN_PARAGRAPH.CENTER)
        set_cell_text(table.rows[idx].cells[2], str(entry.get("date", "")),
                      align=WD_ALIGN_PARAGRAPH.CENTER)
        set_cell_text(table.rows[idx].cells[3], str(entry.get("description", "")))
    document.add_page_break()


def add_evaluation_specs(document, assessment, *, table_caption: str) -> None:
    """Section 1: مشخصات ارزیابی — tester/approver codes, completion date."""
    add_rtl_paragraph(document, table_caption, size=11)
    table = make_table(document, rows=3, cols=2)
    completed = (
        shamsi_date(assessment.test_completed_date)
        if assessment.test_completed_date
        else ""
    )
    rows = [
        ("کد آزمونگر", assessment.tester_code),
        ("کد تأییدکننده", assessment.approver_code),
        ("تاریخ اتمام آزمون", completed),
    ]
    for idx, (label, value) in enumerate(rows):
        set_cell_text(table.rows[idx].cells[0], label, bold=True)
        shade_cell(table.rows[idx].cells[0])
        set_cell_text(table.rows[idx].cells[1], value)


def add_clause_result_table(document, clause_assessment) -> None:
    """The per-clause 4-row table shared by TRP section 6 and the BRP."""
    clause = clause_assessment.clause
    result, color = result_text_and_color(clause_assessment.status)
    table = make_table(document, rows=4, cols=2)
    rows = [
        ("عنوان الزام", clause.description or f"{clause.code} {clause.title}", None),
        ("نتیجه نهایی آزمون", result, color),
        ("هدف الزام", clause.objective, None),
        ("تشریح آزمون انجام شده", clause_assessment.text, None),
    ]
    for idx, (label, value, value_color) in enumerate(rows):
        set_cell_text(table.rows[idx].cells[0], label, bold=True)
        shade_cell(table.rows[idx].cells[0])
        set_cell_text(table.rows[idx].cells[1], value, color=value_color,
                      bold=bool(value_color))
    # Label column ~25% width
    for row in table.rows:
        row.cells[0].width = document.sections[0].page_width * 1 // 4
        row.cells[1].width = document.sections[0].page_width * 3 // 4
