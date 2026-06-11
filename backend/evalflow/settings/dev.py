"""Development settings.

Defaults to SQLite so the project runs on machines without MySQL client
libraries (set DB_ENGINE=mysql to use a local/dockerized MySQL instead).
Production always uses MySQL — see prod.py / docker-compose.yml.
"""
from .base import *  # noqa: F401,F403
from .base import REST_FRAMEWORK, env

DEBUG = True

SECRET_KEY = env("DJANGO_SECRET_KEY", default="dev-only-insecure-key-do-not-use-in-prod")

ALLOWED_HOSTS = ["*"]

if env("DB_ENGINE", default="sqlite") != "mysql":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",  # noqa: F405
            "ATOMIC_REQUESTS": True,
        }
    }

INSTALLED_APPS += ["corsheaders"]  # noqa: F405
MIDDLEWARE.insert(0, "corsheaders.middleware.CorsMiddleware")  # noqa: F405

# Vite dev server origin only; production is same-origin and needs no CORS.
CORS_ALLOWED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
CORS_ALLOW_CREDENTIALS = True

# Cookies over plain http in dev.
REFRESH_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
