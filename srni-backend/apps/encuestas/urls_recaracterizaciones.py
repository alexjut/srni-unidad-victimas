"""
`/api/recaracterizaciones/` — recurso propio, igual que `/api/habilitaciones/`.

Va en su propia raíz y no bajo `/api/encuestas/` por lo que **es**: la consulta de
supervisión del retiro del control de vigencia. Su consumidor es el Panel de
Control, no la aplicación de campo, y el permiso que exige es otro —supervisión, no
caracterización—. Colgarla de las encuestas escondería esa frontera.
"""
from rest_framework.routers import DefaultRouter

from .recaracterizaciones import RecaracterizacionViewSet

router = DefaultRouter()
router.register(r'', RecaracterizacionViewSet, basename='recaracterizacion')

urlpatterns = router.urls
