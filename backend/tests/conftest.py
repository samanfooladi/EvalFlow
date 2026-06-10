import pytest
from django.core.cache import cache
from rest_framework.test import APIClient


@pytest.fixture(autouse=True)
def _clear_throttle_cache():
    """DRF throttle counters live in the cache and would leak across tests."""
    cache.clear()
    yield
    cache.clear()

from .factories import (
    DEFAULT_PASSWORD,
    AdminFactory,
    AssessorFactory,
    QALeadFactory,
    ReviewerFactory,
)


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def admin_user(db):
    return AdminFactory()


@pytest.fixture
def assessor(db):
    return AssessorFactory()


@pytest.fixture
def reviewer(db):
    return ReviewerFactory()


@pytest.fixture
def qa_lead(db):
    return QALeadFactory()


@pytest.fixture
def password():
    return DEFAULT_PASSWORD


def login(api: APIClient, user, password: str = DEFAULT_PASSWORD):
    """Login via the real endpoint; returns the access token."""
    response = api.post(
        "/api/v1/auth/login/",
        {"username": user.username, "password": password},
        format="json",
    )
    assert response.status_code == 200, response.content
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
    return response


@pytest.fixture
def as_user(api):
    def _as(user):
        login(api, user)
        return api

    return _as
