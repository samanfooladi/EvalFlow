"""Parametrized endpoint × role permission matrix.

Extended in later milestones as endpoints land; doubles as living
documentation of the RBAC rules.
"""
import pytest

from .factories import (
    AdminFactory,
    AssessorFactory,
    QALeadFactory,
    ReviewerFactory,
    UserFactory,
)

pytestmark = pytest.mark.django_db

ROLE_FACTORIES = {
    "admin": AdminFactory,
    "assessor": AssessorFactory,
    "reviewer": ReviewerFactory,
    "qa_lead": QALeadFactory,
}


@pytest.mark.parametrize(
    "role,method,url,expected",
    [
        # /users/ — Admin CRUD, QA Lead read-only
        ("admin", "get", "/api/v1/auth/users/", 200),
        ("qa_lead", "get", "/api/v1/auth/users/", 200),
        ("assessor", "get", "/api/v1/auth/users/", 403),
        ("reviewer", "get", "/api/v1/auth/users/", 403),
        ("admin", "post", "/api/v1/auth/users/", 400),  # passes RBAC, fails validation
        ("qa_lead", "post", "/api/v1/auth/users/", 403),
        ("assessor", "post", "/api/v1/auth/users/", 403),
        ("reviewer", "post", "/api/v1/auth/users/", 403),
        # /audit-logs/ — Admin + QA Lead read-only
        ("admin", "get", "/api/v1/audit-logs/", 200),
        ("qa_lead", "get", "/api/v1/audit-logs/", 200),
        ("assessor", "get", "/api/v1/audit-logs/", 403),
        ("reviewer", "get", "/api/v1/audit-logs/", 403),
    ],
)
def test_endpoint_role_matrix(api, as_user, role, method, url, expected):
    user = ROLE_FACTORIES[role]()
    as_user(user)
    response = getattr(api, method)(url, {}, format="json")
    assert response.status_code == expected, (
        f"{role} {method.upper()} {url}: got {response.status_code}, "
        f"expected {expected}"
    )


def test_anonymous_denied_everywhere(api):
    for url in ["/api/v1/auth/users/", "/api/v1/audit-logs/", "/api/v1/auth/me/"]:
        assert api.get(url).status_code == 401


def test_admin_create_user_full_flow(api, as_user):
    admin = AdminFactory()
    as_user(admin)
    response = api.post(
        "/api/v1/auth/users/",
        {
            "username": "new.assessor",
            "password": "Initial-Str0ng-Pass!",
            "role": "assessor",
            "first_name": "علی",
            "last_name": "ارزیاب",
        },
        format="json",
    )
    assert response.status_code == 201, response.content
    assert response.data["must_change_password"] is True
    assert "password" not in response.data


def test_user_delete_is_soft(api, as_user):
    admin = AdminFactory()
    target = UserFactory()
    as_user(admin)
    response = api.delete(f"/api/v1/auth/users/{target.pk}/")
    assert response.status_code == 204
    target.refresh_from_db()
    assert target.is_active is False  # deactivated, not deleted


def test_weak_password_rejected_on_user_create(api, as_user):
    admin = AdminFactory()
    as_user(admin)
    response = api.post(
        "/api/v1/auth/users/",
        {"username": "weak.user", "password": "12345678", "role": "assessor"},
        format="json",
    )
    assert response.status_code == 400
