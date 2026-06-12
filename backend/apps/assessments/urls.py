from rest_framework.routers import DefaultRouter

from .views import (
    AssessmentViewSet,
    AttachmentViewSet,
    ClauseAssessmentViewSet,
    SubClauseAssessmentViewSet,
)

router = DefaultRouter()
router.register("assessments", AssessmentViewSet, basename="assessment")
router.register(
    "clause-assessments", ClauseAssessmentViewSet, basename="clauseassessment"
)
router.register(
    "sub-clause-assessments",
    SubClauseAssessmentViewSet,
    basename="subclauseassessment",
)
router.register("attachments", AttachmentViewSet, basename="attachment")

urlpatterns = router.urls
