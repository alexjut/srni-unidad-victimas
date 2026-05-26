"""
Vistas de reportes de producción — Sprint 10.

Endpoints:
  GET /api/reportes/produccion/         → resumen del encuestador autenticado
  GET /api/reportes/produccion/detalle/ → lista paginada de sesiones del período
  GET /api/reportes/produccion/export/  → descarga CSV

Permisos:
  - Encuestador: ve solo sus propias sesiones
  - Administrador (puede_administrar=True): puede filtrar por encuestador
"""
import csv
from datetime import date, timedelta, datetime

from django.db.models import Count, Avg, Q, Sum, Max
from django.db.models.functions import TruncDate
from django.http import StreamingHttpResponse
from django.utils import timezone
from django.utils.timezone import make_aware
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.autenticacion.permissions import (
    PuedeCaracterizar, PuedeVerReportes, PuedeAdministrar,
)
from apps.encuestas.models import SesionEncuesta, RespuestaEncuesta
from apps.autenticacion.models import Usuario

from .serializers import (
    ProduccionEncuestadorSerializer,
    SesionResumenReporteSerializer,
    SupervisorReporteSerializer,
    DashboardSeriesSerializer,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _parse_date(value: str | None, default: date) -> date:
    if not value:
        return default
    try:
        return date.fromisoformat(value)
    except ValueError:
        return default


def _sesiones_periodo(encuestador, desde: date, hasta: date):
    """Queryset base de sesiones del período para un encuestador."""
    desde_dt = make_aware(datetime(desde.year, desde.month, desde.day, 0, 0, 0))
    hasta_dt = make_aware(datetime(hasta.year, hasta.month, hasta.day, 23, 59, 59))
    return SesionEncuesta.objects.filter(
        encuestador=encuestador,
        created_at__range=(desde_dt, hasta_dt),
    ).select_related('instrumento', 'hogar')


def _build_sesion_data(sesion) -> dict:
    duracion = None
    if sesion.fecha_fin and sesion.fecha_inicio:
        delta = sesion.fecha_fin - sesion.fecha_inicio
        duracion = round(delta.total_seconds() / 60, 1)

    return {
        'id': sesion.id,
        'hogar_id': sesion.hogar_id,
        'instrumento_nombre': sesion.instrumento.nombre if hasattr(sesion.instrumento, 'nombre') else str(sesion.instrumento),
        'perfil_codigo': sesion.instrumento.codigo if sesion.instrumento else '',
        'estado': sesion.estado,
        'estado_display': sesion.get_estado_display(),
        'porcentaje_completado': sesion.porcentaje_completado,
        'respuestas_total': sesion.respuestas.count(),
        'fecha_inicio': sesion.fecha_inicio,
        'fecha_fin': sesion.fecha_fin,
        'duracion_minutos': duracion,
    }


# ─── Endpoint: resumen ─────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated, PuedeCaracterizar])
def produccion_resumen(request):
    """
    Resumen de producción del encuestador autenticado.

    Query params:
      desde       ISO date — inicio del período (default: 1° del mes actual)
      hasta       ISO date — fin del período (default: hoy)
      encuestador UUID     — solo para administradores
    """
    hoy = date.today()
    desde = _parse_date(request.query_params.get('desde'), hoy.replace(day=1))
    hasta = _parse_date(request.query_params.get('hasta'), hoy)

    # Admins pueden ver otro encuestador
    encuestador = request.user
    encuestador_param = request.query_params.get('encuestador')
    if encuestador_param and request.user.puede('administrar'):
        try:
            encuestador = Usuario.objects.get(pk=encuestador_param)
        except Usuario.DoesNotExist:
            return Response({'detail': 'Encuestador no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

    qs = _sesiones_periodo(encuestador, desde, hasta)

    # Conteos por estado
    conteos = qs.values('estado').annotate(n=Count('id'))
    por_estado = {item['estado']: item['n'] for item in conteos}

    sesiones_completadas  = por_estado.get('COMPLETADA', 0)
    sesiones_en_progreso  = por_estado.get('EN_PROGRESO', 0) + por_estado.get('INICIADA', 0)
    sesiones_suspendidas  = por_estado.get('SUSPENDIDA', 0)
    sesiones_total        = qs.count()

    # Hogares caracterizados = hogares con al menos 1 sesión completada
    hogares_caracterizados = qs.filter(estado='COMPLETADA').values('hogar').distinct().count()

    # Total de respuestas del período
    respuestas_total = RespuestaEncuesta.objects.filter(
        sesion__in=qs,
    ).exclude(valor='').count()

    # Promedio de completado
    avg_data = qs.aggregate(avg=Avg('porcentaje_completado'))
    promedio_completado = round(avg_data['avg'] or 0.0, 1)

    # Por instrumento
    instr_qs = qs.values(
        'instrumento__id',
        'instrumento__nombre',
        'instrumento__codigo',
    ).annotate(
        total=Count('id'),
        completadas=Count('id', filter=Q(estado='COMPLETADA')),
        promedio=Avg('porcentaje_completado'),
    )
    por_instrumento = [
        {
            'instrumento_id': item['instrumento__id'],
            'instrumento_nombre': item['instrumento__nombre'] or '',
            'perfil_codigo': item['instrumento__codigo'] or '',
            'total': item['total'],
            'completadas': item['completadas'],
            'promedio_completado': round(item['promedio'] or 0.0, 1),
        }
        for item in instr_qs
    ]

    # Últimas 5 sesiones
    recientes = [_build_sesion_data(s) for s in qs.order_by('-created_at')[:5]]

    data = {
        'encuestador_id': encuestador.id,
        # Sprint 20: el modelo custom Usuario no tiene get_full_name()/username.
        # Usar nombre_completo (campo del modelo) con fallback al codigo_usuario.
        'encuestador_nombre': getattr(encuestador, 'nombre_completo', '')
                              or getattr(encuestador, 'codigo_usuario', ''),
        'periodo_desde': desde,
        'periodo_hasta': hasta,
        'sesiones_total': sesiones_total,
        'sesiones_completadas': sesiones_completadas,
        'sesiones_en_progreso': sesiones_en_progreso,
        'sesiones_suspendidas': sesiones_suspendidas,
        'hogares_caracterizados': hogares_caracterizados,
        'respuestas_total': respuestas_total,
        'promedio_completado': promedio_completado,
        'por_instrumento': por_instrumento,
        'sesiones_recientes': recientes,
    }

    serializer = ProduccionEncuestadorSerializer(data)
    return Response(serializer.data)


# ─── Endpoint: detalle paginado ───────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated, PuedeCaracterizar])
def produccion_detalle(request):
    """
    Lista paginada de sesiones del período.

    Query params:
      desde, hasta, encuestador (igual que resumen)
      estado   — filtrar por estado
      page     — página (default 1, 20 por página)
    """
    hoy = date.today()
    desde = _parse_date(request.query_params.get('desde'), hoy.replace(day=1))
    hasta = _parse_date(request.query_params.get('hasta'), hoy)

    encuestador = request.user
    encuestador_param = request.query_params.get('encuestador')
    if encuestador_param and request.user.puede('administrar'):
        try:
            encuestador = Usuario.objects.get(pk=encuestador_param)
        except Usuario.DoesNotExist:
            return Response({'detail': 'Encuestador no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

    qs = _sesiones_periodo(encuestador, desde, hasta)

    estado_filtro = request.query_params.get('estado')
    if estado_filtro:
        qs = qs.filter(estado=estado_filtro.upper())

    qs = qs.order_by('-created_at')

    # Paginación manual liviana
    PAGE_SIZE = 20
    try:
        page = max(1, int(request.query_params.get('page', 1)))
    except ValueError:
        page = 1
    total = qs.count()
    inicio = (page - 1) * PAGE_SIZE
    sesiones = qs[inicio: inicio + PAGE_SIZE]

    items = [_build_sesion_data(s) for s in sesiones]

    return Response({
        'count': total,
        'page': page,
        'pages': max(1, -(-total // PAGE_SIZE)),  # ceil division
        'results': SesionResumenReporteSerializer(items, many=True).data,
    })


# ─── Endpoint: export CSV ─────────────────────────────────────────────────────

class _Echo:
    """Adaptador para StreamingHttpResponse."""
    def write(self, value):
        return value


@api_view(['GET'])
@permission_classes([IsAuthenticated, PuedeCaracterizar])
def produccion_export_csv(request):
    """
    Descarga CSV de las sesiones del período.
    Devuelve el archivo como streaming para no bloquear el servidor.
    """
    hoy = date.today()
    desde = _parse_date(request.query_params.get('desde'), hoy.replace(day=1))
    hasta = _parse_date(request.query_params.get('hasta'), hoy)

    encuestador = request.user
    encuestador_param = request.query_params.get('encuestador')
    if encuestador_param and request.user.puede('administrar'):
        try:
            encuestador = Usuario.objects.get(pk=encuestador_param)
        except Usuario.DoesNotExist:
            return Response({'detail': 'Encuestador no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

    qs = _sesiones_periodo(encuestador, desde, hasta).order_by('fecha_inicio')

    encuestador_nombre = getattr(encuestador, 'nombre_completo', '') \
                         or getattr(encuestador, 'codigo_usuario', '')

    def _rows():
        writer = csv.writer(_Echo())
        yield writer.writerow([
            'sesion_id', 'hogar_id', 'instrumento', 'perfil',
            'encuestador', 'estado', 'porcentaje_completado',
            'respuestas_total', 'fecha_inicio', 'fecha_fin', 'duracion_minutos',
        ])
        for s in qs.iterator():
            duracion = None
            if s.fecha_fin and s.fecha_inicio:
                duracion = round((s.fecha_fin - s.fecha_inicio).total_seconds() / 60, 1)
            nombre_instr = s.instrumento.nombre if hasattr(s.instrumento, 'nombre') else str(s.instrumento)
            perfil = s.instrumento.codigo if s.instrumento else ''
            yield writer.writerow([
                s.id, s.hogar_id, nombre_instr, perfil,
                encuestador_nombre, s.estado, s.porcentaje_completado,
                s.respuestas.count(),
                s.fecha_inicio.strftime('%Y-%m-%d %H:%M'),
                s.fecha_fin.strftime('%Y-%m-%d %H:%M') if s.fecha_fin else '',
                duracion or '',
            ])

    nombre_archivo = f'produccion_{encuestador.codigo_usuario}_{desde}_{hasta}.csv'
    response = StreamingHttpResponse(
        _rows(),
        content_type='text/csv; charset=utf-8',
    )
    response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
    return response


# ─── Endpoint: vista supervisor (S13) ─────────────────────────────────────────

def _rango_periodo(request):
    """Resuelve el rango ?desde=&hasta= con defaults (mes actual)."""
    hoy = date.today()
    desde = _parse_date(request.query_params.get('desde'), hoy.replace(day=1))
    hasta = _parse_date(request.query_params.get('hasta'), hoy)
    desde_dt = make_aware(datetime(desde.year, desde.month, desde.day, 0, 0, 0))
    hasta_dt = make_aware(datetime(hasta.year, hasta.month, hasta.day, 23, 59, 59))
    return desde, hasta, desde_dt, hasta_dt


@api_view(['GET'])
@permission_classes([IsAuthenticated, PuedeVerReportes])
def supervisor_reporte(request):
    """
    Vista supervisor — métricas comparativas por encuestador.

    Query params:
      desde   ISO date — inicio del período (default: 1° del mes actual)
      hasta   ISO date — fin del período (default: hoy)

    Requiere perfil con puede_ver_reportes=True.

    Respuesta:
      {
        "periodo_desde": "2026-05-01",
        "periodo_hasta": "2026-05-25",
        "encuestadores_activos": 5,
        "totales": { "sesiones_total": ..., "promedio_completado": ... },
        "encuestadores": [
          {
            "id": "...", "codigo_usuario": "ENC001",
            "nombre_completo": "...", "perfil_codigo": "ASISTENCIA",
            "sesiones_total": 30, "sesiones_completadas": 25,
            "hogares_caracterizados": 22, "promedio_completado": 82.1,
            "ultima_actividad": "2026-05-25T14:32:00Z"
          }, ...
        ]
      }
    """
    desde, hasta, desde_dt, hasta_dt = _rango_periodo(request)

    sesiones_qs = SesionEncuesta.objects.filter(
        created_at__range=(desde_dt, hasta_dt),
        encuestador__isnull=False,
    )

    # Agregaciones por encuestador
    por_enc = sesiones_qs.values(
        'encuestador__id',
        'encuestador__codigo_usuario',
        'encuestador__nombre_completo',
        'encuestador__perfil__codigo',
    ).annotate(
        sesiones_total=Count('id'),
        sesiones_completadas=Count('id', filter=Q(estado='COMPLETADA')),
        sesiones_en_progreso=Count(
            'id',
            filter=Q(estado__in=['INICIADA', 'EN_PROGRESO']),
        ),
        sesiones_suspendidas=Count('id', filter=Q(estado='SUSPENDIDA')),
        hogares_caracterizados=Count(
            'hogar', filter=Q(estado='COMPLETADA'), distinct=True,
        ),
        promedio_completado=Avg('porcentaje_completado'),
        ultima_actividad=Max('updated_at'),
    ).order_by('-sesiones_total')

    encuestadores = [
        {
            'id': item['encuestador__id'],
            'codigo_usuario': item['encuestador__codigo_usuario'],
            'nombre_completo': item['encuestador__nombre_completo'],
            'perfil_codigo': item['encuestador__perfil__codigo'] or '',
            'sesiones_total': item['sesiones_total'],
            'sesiones_completadas': item['sesiones_completadas'],
            'sesiones_en_progreso': item['sesiones_en_progreso'],
            'sesiones_suspendidas': item['sesiones_suspendidas'],
            'hogares_caracterizados': item['hogares_caracterizados'],
            'promedio_completado': round(item['promedio_completado'] or 0.0, 1),
            'ultima_actividad': item['ultima_actividad'],
        }
        for item in por_enc
    ]

    # Totales globales
    global_agg = sesiones_qs.aggregate(
        sesiones_total=Count('id'),
        sesiones_completadas=Count('id', filter=Q(estado='COMPLETADA')),
        sesiones_en_progreso=Count(
            'id', filter=Q(estado__in=['INICIADA', 'EN_PROGRESO']),
        ),
        sesiones_suspendidas=Count('id', filter=Q(estado='SUSPENDIDA')),
        hogares_caracterizados=Count(
            'hogar', filter=Q(estado='COMPLETADA'), distinct=True,
        ),
        promedio_completado=Avg('porcentaje_completado'),
    )

    data = {
        'periodo_desde': desde,
        'periodo_hasta': hasta,
        'encuestadores_activos': len(encuestadores),
        'totales': {
            'sesiones_total': global_agg['sesiones_total'] or 0,
            'sesiones_completadas': global_agg['sesiones_completadas'] or 0,
            'sesiones_en_progreso': global_agg['sesiones_en_progreso'] or 0,
            'sesiones_suspendidas': global_agg['sesiones_suspendidas'] or 0,
            'hogares_caracterizados': global_agg['hogares_caracterizados'] or 0,
            'promedio_completado': round(global_agg['promedio_completado'] or 0.0, 1),
        },
        'encuestadores': encuestadores,
    }

    return Response(SupervisorReporteSerializer(data).data)


# ─── Endpoint: dashboard series temporales (S13) ──────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated, PuedeVerReportes])
def dashboard_series(request):
    """
    Series temporales para gráficos del dashboard.

    Query params:
      desde   ISO date — default: hoy − 30 días
      hasta   ISO date — default: hoy

    Devuelve:
      - serie_diaria: lista de (fecha, sesiones_iniciadas, sesiones_completadas)
      - distribucion_por_instrumento: lista (instrumento_codigo, nombre, total)

    Si el usuario tiene puede_administrar=True ve todos los encuestadores.
    Si solo tiene puede_ver_reportes ve únicamente sus propias sesiones.
    """
    hoy = date.today()
    desde = _parse_date(request.query_params.get('desde'), hoy - timedelta(days=30))
    hasta = _parse_date(request.query_params.get('hasta'), hoy)
    desde_dt = make_aware(datetime(desde.year, desde.month, desde.day, 0, 0, 0))
    hasta_dt = make_aware(datetime(hasta.year, hasta.month, hasta.day, 23, 59, 59))

    qs = SesionEncuesta.objects.filter(created_at__range=(desde_dt, hasta_dt))
    if not request.user.puede('administrar'):
        qs = qs.filter(encuestador=request.user)

    # Serie diaria de iniciadas (created_at) y completadas (fecha_fin)
    iniciadas_qs = qs.annotate(
        fecha=TruncDate('created_at'),
    ).values('fecha').annotate(total=Count('id'))
    iniciadas_map = {item['fecha']: item['total'] for item in iniciadas_qs}

    completadas_qs = qs.filter(estado='COMPLETADA', fecha_fin__isnull=False).annotate(
        fecha=TruncDate('fecha_fin'),
    ).values('fecha').annotate(total=Count('id'))
    completadas_map = {item['fecha']: item['total'] for item in completadas_qs}

    # Generar serie completa día a día (incluyendo días sin actividad)
    serie_diaria = []
    cursor = desde
    while cursor <= hasta:
        serie_diaria.append({
            'fecha': cursor,
            'sesiones_iniciadas': iniciadas_map.get(cursor, 0),
            'sesiones_completadas': completadas_map.get(cursor, 0),
        })
        cursor += timedelta(days=1)

    # Distribución por instrumento (no usamos perfil — el modelo no lo tiene)
    distrib_qs = qs.values(
        'instrumento__codigo',
        'instrumento__nombre',
    ).annotate(total=Count('id')).order_by('-total')
    distribucion = [
        {
            'instrumento_codigo': item['instrumento__codigo'] or '',
            'instrumento_nombre': item['instrumento__nombre'] or '',
            'total': item['total'],
        }
        for item in distrib_qs
    ]

    data = {
        'periodo_desde': desde,
        'periodo_hasta': hasta,
        'serie_diaria': serie_diaria,
        'distribucion_por_instrumento': distribucion,
    }

    return Response(DashboardSeriesSerializer(data).data)
