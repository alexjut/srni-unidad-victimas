from rest_framework.routers import DefaultRouter
from .views import (
    DepartamentoViewSet, MunicipioViewSet, VeredaViewSet,
    TipoDocumentoViewSet, ComunidadNegraViewSet, ResguardoIndigenaViewSet,
    DireccionTerritorialViewSet, PuntoAtencionViewSet,
)

router = DefaultRouter()
router.register(r'departamentos', DepartamentoViewSet, basename='departamento')
router.register(r'municipios', MunicipioViewSet, basename='municipio')
router.register(r'veredas', VeredaViewSet, basename='vereda')
router.register(r'tipos-documento', TipoDocumentoViewSet, basename='tipodocumento')
router.register(r'comunidades-negras', ComunidadNegraViewSet, basename='comunidadnegra')
router.register(r'resguardos-indigenas', ResguardoIndigenaViewSet, basename='resguardoindigena')
router.register(r'direcciones-territoriales', DireccionTerritorialViewSet, basename='direccionterritorial')
router.register(r'puntos-atencion', PuntoAtencionViewSet, basename='puntoatencion')

urlpatterns = router.urls
