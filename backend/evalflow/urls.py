from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.audit.urls")),
    path("api/v1/", include("apps.catalog.urls")),
    path("api/v1/", include("apps.frameworks.urls")),
    path("api/v1/", include("apps.assessments.urls")),
    path("api/v1/", include("apps.reports.urls")),
]
