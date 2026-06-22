"""
Dashboard de presentación para el panel de administración (django-unfold).

Solo PRESENTACIÓN: este módulo enriquece el `context` del index del admin con
KPIs, datos para gráficos (Chart.js, formato que espera unfold) y una tabla con
las últimas sesiones de encuesta. No modifica modelos, lógica ni permisos.

Conectado vía UNFOLD['DASHBOARD_CALLBACK'] = 'srni.dashboard.dashboard_callback'.

Notas de robustez:
- Todas las queries toleran 0 registros (los gráficos no truenan con BD vacía).
- Se usa timezone.localdate()/localtime() (USE_TZ=True, America/Bogota).
- Los datos de los gráficos se serializan a JSON y se pasan tal cual al componente
  unfold/components/chart/{line,bar}.html mediante el atributo `data` del <canvas>.
"""
import json
from datetime import timedelta

from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.victimas.models import Victima
from apps.hogares.models import Hogar
from apps.encuestas.models import SesionEncuesta


# Colores institucionales (Chart.js entiende rgb/rgba directamente).
COLOR_PRIMARIO = "rgb(59, 130, 246)"          # azul
COLOR_PRIMARIO_FILL = "rgba(59, 130, 246, 0.15)"
PALETA_BARRAS = [
    "rgba(59, 130, 246, 0.7)",   # azul
    "rgba(16, 185, 129, 0.7)",   # verde
    "rgba(249, 115, 22, 0.7)",   # naranja
    "rgba(139, 92, 246, 0.7)",   # violeta
    "rgba(236, 72, 153, 0.7)",   # rosa
    "rgba(234, 179, 8, 0.7)",    # amarillo
    "rgba(20, 184, 166, 0.7)",   # teal
]

DIAS_VENTANA = 30
ULTIMAS_SESIONES = 8


def _kpis():
    """KPIs principales (cards). Cada query tolera 0 registros."""
    hoy = timezone.localdate()

    total_victimas = Victima.objects.count()
    total_sesiones = SesionEncuesta.objects.count()

    # Capturas/entrevistas de HOY: se filtra por la fecha local del created_at.
    capturas_hoy = SesionEncuesta.objects.filter(created_at__date=hoy).count()

    total_hogares = Hogar.objects.count()
    # "Completados" según el estado real del modelo Hogar: ACTIVO = caracterización completa.
    hogares_activos = Hogar.objects.filter(estado="ACTIVO").count()
    sesiones_completadas = SesionEncuesta.objects.filter(estado="COMPLETADA").count()

    return {
        "total_victimas": total_victimas,
        "capturas_hoy": capturas_hoy,
        "total_hogares": total_hogares,
        "hogares_activos": hogares_activos,
        "total_sesiones": total_sesiones,
        "sesiones_completadas": sesiones_completadas,
    }


def _chart_lineas():
    """
    Capturas (SesionEncuesta) por día en los últimos 30 días.
    Rellena con 0 los días sin registros. Devuelve JSON Chart.js (line).
    """
    hoy = timezone.localdate()
    desde = hoy - timedelta(days=DIAS_VENTANA - 1)

    qs = (
        SesionEncuesta.objects.filter(created_at__date__gte=desde)
        .annotate(dia=TruncDate("created_at"))
        .values("dia")
        .annotate(total=Count("id"))
    )
    conteo_por_dia = {row["dia"]: row["total"] for row in qs if row["dia"]}

    labels = []
    data = []
    for i in range(DIAS_VENTANA):
        dia = desde + timedelta(days=i)
        labels.append(dia.strftime("%d/%m"))
        data.append(conteo_por_dia.get(dia, 0))

    return json.dumps({
        "labels": labels,
        "datasets": [{
            "label": "Capturas",
            "data": data,
            "borderColor": COLOR_PRIMARIO,
            "backgroundColor": COLOR_PRIMARIO_FILL,
            "borderWidth": 2,
            "tension": 0.4,
            "fill": True,
            "pointRadius": 2,
        }],
    })


def _chart_barras():
    """
    Entrevistas (SesionEncuesta) agrupadas por instrumento.
    Maneja el caso de 0 registros sin romper. Devuelve JSON Chart.js (bar).
    """
    qs = (
        SesionEncuesta.objects.values(
            "instrumento__codigo", "instrumento__nombre"
        )
        .annotate(total=Count("id"))
        .order_by("-total")
    )

    labels = []
    data = []
    for row in qs:
        codigo = row.get("instrumento__codigo") or "—"
        labels.append(codigo)
        data.append(row["total"])

    # Con BD vacía, labels/data quedan vacíos: Chart.js dibuja un eje sin barras (no truena).
    colores = [PALETA_BARRAS[i % len(PALETA_BARRAS)] for i in range(len(labels))]

    return json.dumps({
        "labels": labels,
        "datasets": [{
            "label": "Entrevistas por instrumento",
            "data": data,
            "backgroundColor": colores or PALETA_BARRAS[:1],
            "borderWidth": 0,
        }],
    })


def _ultimas_sesiones():
    """
    Últimas ~8 SesionEncuesta para la tabla.
    Devuelve estructura {headers, rows} que espera unfold/components/table.html.
    """
    estado_display = dict(SesionEncuesta.ESTADO)

    sesiones = (
        SesionEncuesta.objects.select_related("instrumento")
        .order_by("-created_at")[:ULTIMAS_SESIONES]
    )

    rows = []
    for s in sesiones:
        instrumento = (
            f"{s.instrumento.codigo}-{s.instrumento.version}"
            if s.instrumento_id else "—"
        )
        fecha = timezone.localtime(s.created_at).strftime("%d/%m/%Y %H:%M")
        rows.append([
            instrumento,
            estado_display.get(s.estado, s.estado),
            f"{s.porcentaje_completado}%",
            fecha,
        ])

    return {
        "headers": ["Instrumento", "Estado", "% Completado", "Fecha"],
        "rows": rows,
    }


def dashboard_callback(request, context):
    """
    Callback de unfold. Enriquece el context del index del admin.
    Debe devolver el context.
    """
    context.update({
        "kpis": _kpis(),
        "chart_capturas_30d": _chart_lineas(),
        "chart_por_instrumento": _chart_barras(),
        "tabla_ultimas_sesiones": _ultimas_sesiones(),
    })
    return context
