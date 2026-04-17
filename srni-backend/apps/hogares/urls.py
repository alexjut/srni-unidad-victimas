from rest_framework.routers import DefaultRouter
from .views import HogarViewSet

router = DefaultRouter()
router.register(r'', HogarViewSet, basename='hogar')

urlpatterns = router.urls
