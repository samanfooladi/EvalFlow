"""Generate the TRP (سند گزارش آزمون کارکردی) Word document, matching the
structure and RTL formatting of the lab's official template.

The front matter (info page, change-log, assessor specs, product profile,
quality-control) is emitted as a blank fillable template — placeholder cells
only, no assessment data — exactly like the lab's master template. The
per-clause detail tables in section 6 remain data-driven."""
from __future__ import annotations

import io

from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches

from .common import (
    add_clause_result_table,
    add_cover,
    add_diagram_placeholder,
    new_document,
)
from .docx_utils import (
    BLACK,
    FIELD_LABEL_FILL,
    GROUP_LABEL_FILL,
    HEADER_BLUE,
    LABEL_SHADE,
    ROW_BLUE_DARK,
    ROW_BLUE_LIGHT,
    WHITE,
    add_heading_fa,
    add_rtl_paragraph,
    add_toc,
    fa_num,
    make_table,
    set_cell_text,
    set_update_fields,
    shade_cell,
)

DOC_TITLE = "سند گزارش آزمون کارکردی"

CENTER = WD_ALIGN_PARAGRAPH.CENTER
PLACEHOLDER = "؟"

QUALITY_CONTROL_ROWS = [
    "۱-مستند به لحاظ رعایت مسائل املایی",
    "۲-ادبیات فارسی",
    "۳-نگارش علمی",
    "۴-مسائل فنی و تخصصی",
    "۵-پاسخگویی نیاز متقاضی خدمت",
    "۶-شرایط استاندارد 17025",
]


def _ordered_clause_assessments(assessment):
    return list(
        assessment.clause_assessments.select_related(
            "clause", "clause__requirement", "assessment", "updated_by"
        ).order_by("clause__requirement__order", "clause__order")
    )


def _header_cell(cell, text, *, fill=HEADER_BLUE, color=WHITE):
    set_cell_text(cell, text, bold=True, color=color, align=CENTER)
    shade_cell(cell, fill)


def _zebra(table, *, start=1, light=ROW_BLUE_LIGHT, dark=ROW_BLUE_DARK):
    """Apply alternating row shading to a table's data rows."""
    for offset, row in enumerate(table.rows[start:]):
        fill = light if offset % 2 == 0 else dark
        for cell in row.cells:
            shade_cell(cell, fill)


# --------------------------------------------------------------------------
# 1 — Cover / document-information page (before the table of contents)
# --------------------------------------------------------------------------
def _add_info_table(document) -> None:
    product_fields = [
        ("عنوان شرکت", "نام شرکت"),
        ("عنوان سامانه", "نام محصول"),
        ("نسخه محصول", PLACEHOLDER),
    ]
    test_fields = [
        ("شناسه سند", PLACEHOLDER),
        ("نسخه گزارش", PLACEHOLDER),
        ("روش آزمون", PLACEHOLDER),
        ("شناسه آزمون", PLACEHOLDER),
        ("شرایط محیطی", PLACEHOLDER),
        ("ابزارهای آزمون", PLACEHOLDER),
        ("تایید کننده", "تأییدکننده: ؟           امضا:"),
        ("تعداد صفحات", PLACEHOLDER),
    ]
    fields = product_fields + test_fields
    n = len(fields)  # 11
    table = make_table(document, rows=n + 1, cols=3)  # +1 توضیحات row

    # middle = field label (dark gray), left = placeholder value
    for idx, (label, value) in enumerate(fields):
        set_cell_text(table.rows[idx].cells[1], label, bold=True, color=WHITE)
        shade_cell(table.rows[idx].cells[1], FIELD_LABEL_FILL)
        set_cell_text(table.rows[idx].cells[2], value)

    # right = vertically merged group labels (dark blue, white, bold)
    prod = table.cell(0, 0).merge(table.cell(len(product_fields) - 1, 0))
    set_cell_text(prod, "مشخصات محصول", bold=True, color=WHITE, align=CENTER)
    shade_cell(prod, GROUP_LABEL_FILL)
    prod.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER

    test = table.cell(len(product_fields), 0).merge(table.cell(n - 1, 0))
    set_cell_text(test, "مشخصات آزمون", bold=True, color=WHITE, align=CENTER)
    shade_cell(test, GROUP_LABEL_FILL)
    test.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER

    # full-width توضیحات row
    notes = table.cell(n, 0).merge(table.cell(n, 2))
    set_cell_text(notes, "توضیحات:", bold=True)

    table.columns[0].width = Inches(1.4)
    table.columns[1].width = Inches(1.9)
    table.columns[2].width = Inches(3.2)
    document.add_page_break()


# --------------------------------------------------------------------------
# 2 — تغییرات سند + مشخصات ارزیابی (same page)
# --------------------------------------------------------------------------
def _add_change_log(document) -> None:
    add_rtl_paragraph(document, "تغییرات سند", size=13, bold=True, align=CENTER)
    table = make_table(document, rows=9, cols=4)  # header + 8 rows
    for col, text in enumerate(["", "نسخه", "تاریخ", "شرح تغییرات"]):
        _header_cell(table.rows[0].cells[col], text)
    for idx in range(1, 9):
        set_cell_text(table.rows[idx].cells[0], fa_num(idx), align=CENTER)
        for col in (1, 2, 3):
            set_cell_text(table.rows[idx].cells[col], "")
    _zebra(table)


def _add_assessor_specs(document) -> None:
    add_heading_fa(document, "۱- مشخصات ارزیابی")
    add_rtl_paragraph(document, "جدول ۱-۱ مشخصات آزمونگر", size=11)
    table = make_table(document, rows=3, cols=2)
    for idx, label in enumerate(
        ["کد آزمونگر", "کد تأییدکننده", "تاریخ اتمام آزمون"]
    ):
        set_cell_text(table.rows[idx].cells[0], label, bold=True)
        shade_cell(table.rows[idx].cells[0], LABEL_SHADE)
        set_cell_text(table.rows[idx].cells[1], PLACEHOLDER)


# --------------------------------------------------------------------------
# 3 — معرفی محصول مورد ارزیابی (شناسنامه محصول)
# --------------------------------------------------------------------------
def _add_product_identity(document) -> None:
    add_heading_fa(document, "۲- معرفی محصول مورد ارزیابی")
    add_rtl_paragraph(document, "جدول ۱-۲ شناسنامه محصول", size=11)
    components = [
        "سیستم‌عامل",
        "وب‌سرویس",
        "پایگاه داده",
        "زبان برنامه‌نویسی / تکنولوژی توسعه",
        "شماره سریال",
        "اجزا متن‌باز",
        "سایر موارد",
    ]
    table = make_table(document, rows=len(components) + 1, cols=3)
    for col, text in enumerate(["اجزا محصول", "نسخه", "توضیحات"]):
        _header_cell(table.rows[0].cells[col], text)
    for idx, name in enumerate(components, start=1):
        if name == "اجزا متن‌باز":
            set_cell_text(
                table.rows[idx].cells[0],
                "اجزا متن‌باز\n• ؟\n• ؟\n• ؟",
            )
        else:
            set_cell_text(table.rows[idx].cells[0], name)
        set_cell_text(table.rows[idx].cells[1], PLACEHOLDER, align=CENTER)
        set_cell_text(table.rows[idx].cells[2], PLACEHOLDER)
    _zebra(table, light=WHITE, dark=LABEL_SHADE)


# --------------------------------------------------------------------------
# 5 — کنترل کیفی
# --------------------------------------------------------------------------
def _add_quality_control(document) -> None:
    add_heading_fa(document, "۵- کنترل کیفی")
    table = make_table(document, rows=len(QUALITY_CONTROL_ROWS) + 1, cols=2)
    for col, text in enumerate(["توضیحات", "تاریخ"]):
        _header_cell(table.rows[0].cells[col], text)
    for idx, text in enumerate(QUALITY_CONTROL_ROWS, start=1):
        set_cell_text(table.rows[idx].cells[0], text)
        set_cell_text(table.rows[idx].cells[1], "")


# --------------------------------------------------------------------------
# 6 — نتایج و تشریح آزمون
# --------------------------------------------------------------------------
def _add_results_list(document, cas) -> None:
    add_heading_fa(document, "۶- نتایج و تشریح آزمون")
    table = make_table(document, rows=len(cas) + 1, cols=3)
    for col, text in enumerate(["ردیف", "عنوان الزام", "نتیجه آزمون"]):
        _header_cell(table.rows[0].cells[col], text, fill=GROUP_LABEL_FILL)
    for idx, ca in enumerate(cas, start=1):
        cells = table.rows[idx].cells
        set_cell_text(cells[0], fa_num(idx), align=CENTER)
        set_cell_text(
            cells[1], ca.clause.description or f"{ca.clause.code} {ca.clause.title}"
        )
        set_cell_text(cells[2], "", align=CENTER)  # filled in by the assessor


def generate_trp(assessment) -> io.BytesIO:
    document = new_document(
        doc_title=DOC_TITLE, assessment=assessment, doc_code_prefix="TRP"
    )
    set_update_fields(document)
    add_cover(document, doc_title=DOC_TITLE, assessment=assessment, logo=True)

    # cover/document-information page (before the TOC)
    _add_info_table(document)

    # table of contents
    add_rtl_paragraph(document, "فهرست", size=16, bold=True, align=CENTER)
    add_toc(document)
    document.add_page_break()

    cas = _ordered_clause_assessments(assessment)

    # تغییرات سند + ۱ مشخصات ارزیابی (same page)
    _add_change_log(document)
    _add_assessor_specs(document)

    # ۲ — معرفی محصول مورد ارزیابی
    _add_product_identity(document)

    # ۳ — نمای کلی معماری محصول (free text, kept from the assessment)
    add_heading_fa(document, "۳- نمای کلی معماری محصول")
    add_rtl_paragraph(document, assessment.architecture_overview or "", size=11)

    # ۴ — پیکربندی آزمون (starts on a new page)
    add_heading_fa(document, "۴- پیکربندی آزمون", page_break_before=True)
    add_rtl_paragraph(document, assessment.test_configuration or "", size=11)
    add_diagram_placeholder(document)

    # ۵ — کنترل کیفی
    _add_quality_control(document)

    # ۶ — نتایج و تشریح آزمون (summary list + per-clause detail tables)
    _add_results_list(document, cas)
    for idx, ca in enumerate(cas, start=1):
        add_heading_fa(
            document,
            f"۶-{fa_num(idx)} {ca.clause.title} ({ca.clause.code})",
            level=2,
            size=12,
        )
        add_clause_result_table(document, ca)

    buffer = io.BytesIO()
    document.save(buffer)
    buffer.seek(0)
    return buffer
