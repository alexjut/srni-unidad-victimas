from rest_framework.routers import DefaultRouter
from .views import SesionEncuestaViewSet

router = DefaultRouter()
router.register(r'', SesionEncuestaViewSet, basename='sesion')

urlpatterns = router.urls
