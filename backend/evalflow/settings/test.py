"""Settings for the pytest suite: SQLite, fast hashing where safe."""
from .base import *  # noqa: F401,F403
from .base import BASE_DIR

DEBUG = False
SECRET_KEY = "test-only-secret-key-padded-to-at-least-32-bytes!"
ALLOWED_HOSTS = ["testserver"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
        "ATOMIC_REQUESTS": True,
    }
}

REFRESH_COOKIE_SECURE = False

MEDIA_ROOT = BASE_DIR / "test_media"
