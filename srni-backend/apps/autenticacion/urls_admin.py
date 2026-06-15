from rest_framework.routers import DefaultRouter

from .views_admin import UsuarioAdminViewSet

router = DefaultRouter()
router.register(r"", UsuarioAdminViewSet, basename="usuario")

urlpatterns = router.urls
