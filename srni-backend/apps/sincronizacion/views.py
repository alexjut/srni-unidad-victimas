"""
API de consulta del ledger de escritura a Oracle legacy.

Por qué existe: hasta el 2026-07-28 el ledger solo se podía mirar entrando a la
base o al admin. Con la escritura automatizada eso deja de servir — un supervisor
necesita poder responder "¿este hogar llegó a Oracle?" sin pedirle nada a un
desarrollador, y sobre todo necesita ver **qué falló**, porque los procedures del
legacy no avisan de sus propios errores.

Solo lectura. La escritura se dispara al cerrar la encuesta o con el comando
`escribir_a_oracle`; no se expone por HTTP a propósito: es irreversible.
"""
from django.db.models import Count, Max, Q
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.autenticacion.permissions import PuedeConsultarOperacion
from srni.pagination import CursorTimePagination

from .models import EstadoPaso, RegistroEscrituraOracle
from .serializers import EstadoHogarSerializer, RegistroEscrituraSerializer


@extend_schema_view(
    list=extend_schema(
        summary="Pasos de escritura hacia Oracle",
        description=(
            "Ledger de la sincronización SICAV → Oracle legacy. Cada fila es un paso "
            "(HOGAR, PERSONA, MIEMBRO, TERRITORIO, RESPUESTA) con su estado.\n\n"
            "El estado que importa es **VERIFICADO**: significa que la escritura fue "
            "confirmada por una consulta posterior a Oracle. **EJECUTADO_SIN_VERIFICAR** "
            "quiere decir que se llamó al procedure pero no se pudo confirmar el "
            "resultado — y como los procedures se tragan sus excepciones, eso NO es "
            "sinónimo de que quedó escrito."
        ),
        tags=["Sincronización Oracle"],
    ),
    retrieve=extend_schema(summary="Detalle de un paso", tags=["Sincronización Oracle"]),
)
class RegistroEscrituraViewSet(mixins.ListModelMixin,
                               mixins.RetrieveModelMixin,
                               viewsets.GenericViewSet):
    serializer_class = RegistroEscrituraSerializer
    permission_classes = [IsAuthenticated, PuedeConsultarOperacion]
    pagination_class = CursorTimePagination
    filterset_fields = ["paso", "estado", "destino_entorno"]

    def get_queryset(self):
        qs = (RegistroEscrituraOracle.objects
              .select_related("hogar")
              .order_by("-actualizado_en"))
        codigo = self.request.query_params.get("hogar")
        return qs.filter(hogar__codigo_hogar=codigo) if codigo else qs

    @extend_schema(
        summary="Estado de sincronización por hogar",
        description=(
            "Resumen agregado: un renglón por hogar y destino, con cuántos pasos van "
            "verificados y cuántos fallaron.\n\n"
            "`estado` resume el conjunto:\n"
            "- **COMPLETO** — todos los pasos verificados en Oracle.\n"
            "- **CON_FALLOS** — al menos un paso falló su verificación. Requiere revisión.\n"
            "- **EN_PROCESO** — hay pasos a medio camino.\n"
            "- **SIMULADO** — solo se corrió en DRY-RUN; no hay nada escrito."
        ),
        tags=["Sincronización Oracle"],
        responses={200: EstadoHogarSerializer(many=True)},
    )
    @action(detail=False, methods=["get"], url_path="estado")
    def estado(self, request):
        filas = (self.get_queryset()
                 .values("hogar__codigo_hogar", "destino_entorno")
                 .annotate(
                     pasos_totales=Count("id"),
                     pasos_verificados=Count("id", filter=Q(estado=EstadoPaso.VERIFICADO)),
                     pasos_fallidos=Count("id", filter=Q(estado=EstadoPaso.FALLIDO)),
                     pasos_dry_run=Count("id", filter=Q(estado=EstadoPaso.DRY_RUN)),
                     hog_codigo_oracle=Max("destino_hog_codigo"),
                     ultima_actualizacion=Max("actualizado_en"),
                 )
                 .order_by("-ultima_actualizacion"))

        datos = [{
            "hogar_codigo": f["hogar__codigo_hogar"],
            "destino": f["destino_entorno"] or "(dry-run)",
            "hog_codigo_oracle": f["hog_codigo_oracle"] or "",
            "estado": _resumir(f),
            "pasos_totales": f["pasos_totales"],
            "pasos_verificados": f["pasos_verificados"],
            "pasos_fallidos": f["pasos_fallidos"],
            "ultima_actualizacion": f["ultima_actualizacion"],
        } for f in filas]
        return Response(EstadoHogarSerializer(datos, many=True).data)


def _resumir(fila) -> str:
    """
    Un fallo pesa más que el resto: si algo falló, el hogar necesita revisión aunque
    los demás pasos estén verificados. Por eso se evalúa primero.
    """
    if fila["pasos_fallidos"]:
        return "CON_FALLOS"
    if fila["pasos_dry_run"] == fila["pasos_totales"]:
        return "SIMULADO"
    if fila["pasos_verificados"] == fila["pasos_totales"]:
        return "COMPLETO"
    return "EN_PROCESO"
