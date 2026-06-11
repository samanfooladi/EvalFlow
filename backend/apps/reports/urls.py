from django.urls import path

from .views import AssessmentExportView

urlpatterns = [
    path(
        "assessments/<int:pk>/export/",
        AssessmentExportView.as_view(),
        name="assessment-export",
    ),
]
