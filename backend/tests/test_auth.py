import pytest
from django.conf import settings

from apps.audit.models import AuditLog

from .conftest import login

pytestmark = pytest.mark.django_db

LOGIN_URL = "/api/v1/auth/login/"
REFRESH_URL = "/api/v1/auth/refresh/"
LOGOUT_URL = "/api/v1/auth/logout/"
ME_URL = "/api/v1/auth/me/"


def test_login_returns_access_and_sets_httponly_refresh_cookie(api, assessor, password):
    response = api.post(
        LOGIN_URL, {"username": assessor.username, "password": password}, format="json"
    )
    assert response.status_code == 200
    assert "access" in response.data
    assert "refresh" not in response.data  # never in the body
    cookie = response.cookies[settings.REFRESH_COOKIE_NAME]
    assert cookie["httponly"]
    assert cookie["samesite"] == "Strict"
    assert cookie["path"] == settings.REFRESH_COOKIE_PATH
    assert response.data["user"]["role"] == "assessor"


def test_login_wrong_password_fails_and_is_audited(api, assessor):
    response = api.post(
        LOGIN_URL, {"username": assessor.username, "password": "wrong-pass-123"},
        format="json",
    )
    assert response.status_code == 401
    assert AuditLog.objects.filter(action="login_fail").exists()


def test_login_success_is_audited(api, assessor, password):
    login(api, assessor)
    entry = AuditLog.objects.filter(action="login_ok").first()
    assert entry is not None
    assert entry.actor == assessor


def test_inactive_user_cannot_login(api, assessor, password):
    assessor.is_active = False
    assessor.save()
    response = api.post(
        LOGIN_URL, {"username": assessor.username, "password": password}, format="json"
    )
    assert response.status_code == 401


def test_refresh_rotates_token(api, assessor, password):
    login_resp = api.post(
        LOGIN_URL, {"username": assessor.username, "password": password}, format="json"
    )
    old_refresh = login_resp.cookies[settings.REFRESH_COOKIE_NAME].value

    api.cookies[settings.REFRESH_COOKIE_NAME] = old_refresh
    refresh_resp = api.post(REFRESH_URL)
    assert refresh_resp.status_code == 200
    assert "access" in refresh_resp.data
    new_refresh = refresh_resp.cookies[settings.REFRESH_COOKIE_NAME].value
    assert new_refresh and new_refresh != old_refresh

    # Old (rotated-out) refresh token is blacklisted.
    api.cookies[settings.REFRESH_COOKIE_NAME] = old_refresh
    replay = api.post(REFRESH_URL)
    assert replay.status_code == 401


def test_refresh_without_cookie_fails(api):
    assert api.post(REFRESH_URL).status_code == 401


def test_logout_blacklists_refresh(api, assessor, password):
    login_resp = api.post(
        LOGIN_URL, {"username": assessor.username, "password": password}, format="json"
    )
    refresh = login_resp.cookies[settings.REFRESH_COOKIE_NAME].value
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {login_resp.data['access']}")
    api.cookies[settings.REFRESH_COOKIE_NAME] = refresh
    assert api.post(LOGOUT_URL).status_code == 204

    api.cookies[settings.REFRESH_COOKIE_NAME] = refresh
    assert api.post(REFRESH_URL).status_code == 401


def test_me_requires_auth(api):
    assert api.get(ME_URL).status_code == 401


def test_me_returns_profile(api, assessor, as_user):
    as_user(assessor)
    response = api.get(ME_URL)
    assert response.status_code == 200
    assert response.data["username"] == assessor.username


def test_login_throttled_after_5_attempts(api, assessor):
    for _ in range(5):
        api.post(
            LOGIN_URL,
            {"username": assessor.username, "password": "bad-password-x"},
            format="json",
        )
    response = api.post(
        LOGIN_URL,
        {"username": assessor.username, "password": "bad-password-x"},
        format="json",
    )
    assert response.status_code == 429


def test_change_password_validates_current(api, assessor, as_user):
    as_user(assessor)
    response = api.post(
        "/api/v1/auth/change-password/",
        {"current_password": "nope", "new_password": "An0ther-Strong-Pass!"},
        format="json",
    )
    assert response.status_code == 400


def test_change_password_enforces_strength(api, assessor, as_user, password):
    as_user(assessor)
    response = api.post(
        "/api/v1/auth/change-password/",
        {"current_password": password, "new_password": "short"},
        format="json",
    )
    assert response.status_code == 400


def test_change_password_success(api, assessor, as_user, password):
    as_user(assessor)
    response = api.post(
        "/api/v1/auth/change-password/",
        {"current_password": password, "new_password": "An0ther-Strong-Pass!"},
        format="json",
    )
    assert response.status_code == 200
    assessor.refresh_from_db()
    assert assessor.check_password("An0ther-Strong-Pass!")
