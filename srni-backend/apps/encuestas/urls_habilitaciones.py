"""
`/api/habilitaciones/` — recurso propio y no una sub-ruta de `/api/encuestas/`.

Una habilitación existe **antes** que la sesión de encuesta y muchas veces sin
que llegue a haber una: colgarla de `/api/encuestas/{id}/` obligaría a inventar
una sesión para autorizarla. Además el consumidor es el front web, no la app de
campo, y tenerla en su propia raíz deja esa frontera visible.
"""
from rest_framework.routers import DefaultRouter

from .habilitaciones import HabilitacionViewSet

router = DefaultRouter()
router.register(r'', HabilitacionViewSet, basename='habilitacion')

urlpatterns = router.urls
