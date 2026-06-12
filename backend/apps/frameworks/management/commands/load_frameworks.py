"""Idempotently load framework fixtures (requirements, clauses, templates).

    python manage.py load_frameworks            # all fixtures
    python manage.py load_frameworks trp_napp   # one fixture
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.assessments.models import Assessment
from apps.frameworks.models import (
    Clause,
    DefaultTextTemplate,
    Framework,
    Requirement,
    SubClause,
)

FIXTURE_DIR = Path(__file__).resolve().parent.parent.parent / "fixtures"


class Command(BaseCommand):
    help = "Load or update framework definitions from fixture JSON files."

    def add_arguments(self, parser):
        parser.add_argument("names", nargs="*", help="fixture names without .json")

    @transaction.atomic
    def handle(self, *args, **options):
        names = options["names"] or [p.stem for p in FIXTURE_DIR.glob("*.json")]
        if not names:
            raise CommandError(f"No fixtures found in {FIXTURE_DIR}")
        for name in names:
            path = FIXTURE_DIR / f"{name}.json"
            if not path.exists():
                raise CommandError(f"Fixture not found: {path}")
            data = json.loads(path.read_text(encoding="utf-8"))
            framework = self._load(data)
            self._sync_assessments(framework)
            self.stdout.write(self.style.SUCCESS(f"Loaded {name}"))

    def _load(self, data: dict):
        fw_data = data["framework"]
        framework, _ = Framework.objects.update_or_create(
            code=fw_data["code"],
            defaults={"title": fw_data["title"], "kind": fw_data["kind"]},
        )
        for tpl in data.get("templates", []):
            DefaultTextTemplate.objects.update_or_create(
                framework=framework,
                status=tpl["status"],
                defaults={"template": tpl["template"]},
            )
        n_req = n_cl = 0
        for req_data in data["requirements"]:
            requirement, _ = Requirement.objects.update_or_create(
                framework=framework,
                code=req_data["code"],
                defaults={
                    "klass_title": req_data["klass_title"],
                    "title": req_data["title"],
                    "guidance": req_data.get("guidance", ""),
                    "order": req_data.get("order", 0),
                },
            )
            n_req += 1
            for cl_data in req_data.get("clauses", []):
                clause, _ = Clause.objects.update_or_create(
                    requirement=requirement,
                    code=cl_data["code"],
                    defaults={
                        "title": cl_data["title"],
                        "description": cl_data.get("description", ""),
                        "objective": cl_data.get("objective", ""),
                        "order": cl_data.get("order", 0),
                    },
                )
                n_cl += 1
                sub_items = cl_data.get("sub_clauses")
                if sub_items:
                    for i, sub in enumerate(sub_items):
                        SubClause.objects.update_or_create(
                            clause=clause,
                            order=sub.get("order", i),
                            defaults={"text": sub["text"]},
                        )
                elif not clause.sub_clauses.exists():
                    # Single-item clause: one sub-clause carrying the text.
                    SubClause.objects.create(
                        clause=clause, text=clause.description, order=0
                    )
        self.stdout.write(
            f"  {framework.code}: {n_req} requirements, {n_cl} clauses"
        )
        return framework

    def _sync_assessments(self, framework: Framework):
        """Backfill SubClauseAssessment rows for sub-clauses added/changed
        above, and re-derive ClauseAssessment.status from them. Idempotent —
        existing rows and unchanged statuses are left untouched."""
        n_recomputed = 0
        for assessment in Assessment.objects.filter(framework=framework):
            assessment.create_clause_assessments()
            for ca in assessment.clause_assessments.all():
                if ca.recompute_status():
                    n_recomputed += 1
        if n_recomputed:
            self.stdout.write(
                f"  {framework.code}: recomputed status for {n_recomputed} "
                "clause assessment(s)"
            )
