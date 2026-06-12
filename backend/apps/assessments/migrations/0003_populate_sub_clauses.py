"""Data-preserving migration to the sub-clause model.

For every existing Clause, create exactly one SubClause carrying the
clause's current description text unchanged (manual splitting happens
later, in the UI). For every existing ClauseAssessment, create one
SubClauseAssessment inheriting its current status, so no verdict is lost.
"""
from django.db import migrations


def forwards(apps, schema_editor):
    Clause = apps.get_model("frameworks", "Clause")
    SubClause = apps.get_model("frameworks", "SubClause")
    ClauseAssessment = apps.get_model("assessments", "ClauseAssessment")
    SubClauseAssessment = apps.get_model("assessments", "SubClauseAssessment")

    for clause in Clause.objects.all().iterator():
        if SubClause.objects.filter(clause=clause).exists():
            continue
        sub = SubClause.objects.create(
            clause=clause, text=clause.description, order=0
        )
        SubClauseAssessment.objects.bulk_create(
            SubClauseAssessment(
                clause_assessment=ca,
                sub_clause=sub,
                status=ca.status,
                updated_by_id=ca.updated_by_id,
            )
            for ca in ClauseAssessment.objects.filter(clause=clause).iterator()
        )


def backwards(apps, schema_editor):
    # The schema migrations drop the tables; nothing to restore — the
    # original clause text and statuses were never modified.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("frameworks", "0002_subclause"),
        (
            "assessments",
            "0002_subclauseassessment_attachment_sub_clause_assessment_and_more",
        ),
    ]

    operations = [migrations.RunPython(forwards, backwards)]
