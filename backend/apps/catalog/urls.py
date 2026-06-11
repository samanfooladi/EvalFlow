from rest_framework.routers import DefaultRouter

from .views import CompanyViewSet, ProductSystemViewSet

router = DefaultRouter()
router.register("companies", CompanyViewSet, basename="company")
router.register("systems", ProductSystemViewSet, basename="system")

urlpatterns = router.urls
