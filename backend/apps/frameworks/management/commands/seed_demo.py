"""Create a demo dataset for development: users for every role, one company,
one system, and one TRP assessment. Never run in production."""
import secrets

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import Role, User
from apps.assessments.models import Assessment
from apps.catalog.models import Company, ProductSystem
from apps.frameworks.models import Framework


class Command(BaseCommand):
    help = "Seed demo users, a company/system, and a TRP assessment (dev only)."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("seed_demo is a development-only command.")

        password = secrets.token_urlsafe(12) + "-Aa1"
        users = {}
        for username, role in [
            ("admin", Role.ADMIN),
            ("assessor", Role.ASSESSOR),
            ("reviewer", Role.REVIEWER),
            ("qalead", Role.QA_LEAD),
        ]:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"role": role, "assessor_code": f"{role[:2].upper()}-01"},
            )
            if created:
                user.set_password(password)
                if role == Role.ADMIN:
                    user.is_staff = True
                    user.is_superuser = True
                user.save()
            users[role] = user

        company, _ = Company.objects.get_or_create(
            name="شرکت نمونه پردازش امن",
            defaults={"name_en": "Sample Secure Processing Co.", "created_by": users[Role.ADMIN]},
        )
        system, _ = ProductSystem.objects.get_or_create(
            company=company,
            name="سامانه مدیریت اسناد",
            version="2.1",
            defaults={"name_en": "Document Management System"},
        )

        framework = Framework.objects.filter(kind="TRP").first()
        if framework is None:
            raise CommandError("Run load_frameworks first.")
        assessment, created = Assessment.objects.get_or_create(
            system=system,
            framework=framework,
            defaults={
                "assessor": users[Role.ASSESSOR],
                "reviewer": users[Role.REVIEWER],
                "tester_code": "AS-01",
                "created_by": users[Role.ADMIN],
            },
        )
        if created:
            assessment.create_clause_assessments()

        self.stdout.write(self.style.SUCCESS("Demo data created."))
        self.stdout.write(
            f"Users admin/assessor/reviewer/qalead — password (new accounts only): {password}"
        )
