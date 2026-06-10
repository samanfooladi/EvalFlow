import factory
from django.contrib.auth.hashers import make_password

from apps.accounts.models import Role, User

DEFAULT_PASSWORD = "Str0ng-Passw0rd-For-Tests!"
# Hash once at import time; per-user set_password with Argon2 makes the
# suite needlessly slow.
_DEFAULT_HASH = make_password(DEFAULT_PASSWORD)


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    first_name = "کاربر"
    last_name = factory.Sequence(lambda n: f"آزمایشی {n}")
    role = Role.ASSESSOR
    is_active = True
    password = _DEFAULT_HASH


class AdminFactory(UserFactory):
    role = Role.ADMIN


class AssessorFactory(UserFactory):
    role = Role.ASSESSOR


class ReviewerFactory(UserFactory):
    role = Role.REVIEWER


class QALeadFactory(UserFactory):
    role = Role.QA_LEAD
