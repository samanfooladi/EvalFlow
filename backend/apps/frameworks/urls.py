from rest_framework.routers import DefaultRouter

from .views import (
    ClauseViewSet,
    DefaultTextTemplateViewSet,
    FrameworkViewSet,
    RequirementViewSet,
)

router = DefaultRouter()
router.register("frameworks", FrameworkViewSet, basename="framework")
router.register("requirements", RequirementViewSet, basename="requirement")
router.register("clauses", ClauseViewSet, basename="clause")
router.register("default-texts", DefaultTextTemplateViewSet, basename="defaulttext")

urlpatterns = router.urls
