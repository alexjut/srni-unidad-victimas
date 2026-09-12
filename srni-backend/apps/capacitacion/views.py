"""
API de las pruebas de capacitación.

Dos superficies distintas y con permisos opuestos:

* **Pública** (`AllowAny`) — la usa el participante desde el navegador. No hay
  inicio de sesión porque ninguno de los convocados tiene credenciales todavía.
  Se identifica con su correo institucional.
* **Interna** (`PuedeVerReportes`) — el tablero de resultados del panel.

La calificación ocurre siempre en el servidor. El cuestionario que se entrega al
navegador no lleva la respuesta correcta.
"""
from django.db import IntegrityError, transaction
from django.db.models import (Avg, Count, ExpressionWrapper, F,
                              FloatField, Func, Q)
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated

from apps.autenticacion.throttles import PruebaPublicaThrottle
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.autenticacion.permissions import PuedeVerReportes

from .models import IntentoPrueba, Prueba, normalizar_correo
from .serializers import (IntentoResumenSerializer, PruebaPublicaSerializer,
                          ResponderSerializer)


def _ip(request):
    """
    IP de origen. El WAF antepone la del cliente y a veces con puerto
    (`186.29.187.18:62432`), que `GenericIPAddressField` rechaza.
    """
    reenviada = request.META.get('HTTP_X_FORWARDED_FOR', '')
    cruda = (reenviada.split(',')[0] if reenviada else
             request.META.get('REMOTE_ADDR', '')).strip()
    if cruda.count(':') == 1:          # IPv4 con puerto
        cruda = cruda.split(':')[0]
    return cruda or None


# ─── Superficie pública ───────────────────────────────────────────────────────

class PruebaPublicaView(APIView):
    """Entrega el cuestionario, sin las respuestas correctas."""
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [PruebaPublicaThrottle]

    def get(self, request, codigo):
        prueba = get_object_or_404(
            Prueba.objects.prefetch_related('preguntas'), codigo=codigo)
        return Response(PruebaPublicaSerializer(prueba).data)


class EstadoParticipanteView(APIView):
    """
    ¿Esta persona ya presentó esta prueba?

    Se consulta antes de mostrar el formulario, para que quien ya respondió vea
    su resultado en vez del cuestionario en blanco.
    """
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [PruebaPublicaThrottle]

    def get(self, request, codigo):
        correo = normalizar_correo(request.query_params.get('correo', ''))
        if not correo:
            return Response({'detail': 'Indique el correo.'},
                            status=status.HTTP_400_BAD_REQUEST)
        prueba = get_object_or_404(Prueba, codigo=codigo)
        intento = IntentoPrueba.objects.filter(
            prueba=prueba, correo_normalizado=correo).first()
        if not intento:
            return Response({'presentada': False, 'abierta': prueba.abierta})
        return Response({
            'presentada': True,
            'abierta': prueba.abierta,
            'puntaje': intento.puntaje,
            'total': intento.total,
            'porcentaje': intento.porcentaje,
            'nivel': intento.nivel,
            'creado_en': intento.creado_en,
        })


class ResponderPruebaView(APIView):
    """Recibe las respuestas, califica y devuelve el resultado con la retroalimentación."""
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [PruebaPublicaThrottle]

    def post(self, request, codigo):
        prueba = get_object_or_404(
            Prueba.objects.prefetch_related('preguntas'), codigo=codigo)
        if not prueba.abierta:
            return Response({'detail': 'Esta prueba ya está cerrada.'},
                            status=status.HTTP_409_CONFLICT)

        entrada = ResponderSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data
        correo_norm = normalizar_correo(datos['correo'])

        if IntentoPrueba.objects.filter(
                prueba=prueba, correo_normalizado=correo_norm).exists():
            return Response(
                {'detail': 'Este correo ya presentó la prueba.', 'ya_presentada': True},
                status=status.HTTP_409_CONFLICT)

        preguntas = list(prueba.preguntas.all())
        enviadas = datos['respuestas']

        puntaje = 0
        detalle = []
        for p in preguntas:
            marcada = (enviadas.get(str(p.id)) or '').strip().upper()
            acerto = marcada == p.correcta.strip().upper()
            if acerto:
                puntaje += 1
            detalle.append({
                'pregunta_id': str(p.id),
                'orden': p.orden,
                'enunciado': p.enunciado,
                'marcada': marcada,
                'correcta': p.correcta,
                'acerto': acerto,
                # La explicación va en TODAS, no solo en las falladas: el
                # cuestionario es una herramienta de aprendizaje, no una
                # calificación, y quien acertó también se lleva el porqué.
                # No hay riesgo de filtración: solo se envía después de responder.
                'explicacion': p.explicacion,
            })

        try:
            with transaction.atomic():
                intento = IntentoPrueba.objects.create(
                    prueba=prueba,
                    correo=datos['correo'],
                    nombre=datos.get('nombre', ''),
                    territorial=datos.get('territorial', ''),
                    respuestas=enviadas,
                    puntaje=puntaje,
                    total=len(preguntas),
                    segundos=datos.get('segundos', 0),
                    ip=_ip(request),
                )
        except IntegrityError:
            # Dos envíos simultáneos del mismo correo: gana el primero.
            return Response(
                {'detail': 'Este correo ya presentó la prueba.', 'ya_presentada': True},
                status=status.HTTP_409_CONFLICT)

        return Response({
            'puntaje': intento.puntaje,
            'total': intento.total,
            'porcentaje': intento.porcentaje,
            'nivel': intento.nivel,
            'detalle': detalle,
        }, status=status.HTTP_201_CREATED)


# ─── Superficie interna (panel) ───────────────────────────────────────────────

class ResultadosView(APIView):
    """
    Tablero de resultados: agregados, por persona y por pregunta.

    El corte por pregunta es el que más sirve para la siguiente jornada: una
    pregunta que falla la mayoría del grupo señala un tema mal explicado.
    """
    permission_classes = [IsAuthenticated, PuedeVerReportes]

    def get(self, request):
        codigo = request.query_params.get('prueba')
        intentos = IntentoPrueba.objects.select_related('prueba')
        if codigo:
            intentos = intentos.filter(prueba__codigo=codigo)

        # ── La nota va SOBRE 10, aunque el cuestionario tenga otro número ─────
        #
        # La escala que aprobó la Dirección técnica es sobre 10 —9-10 apropiado,
        # 7-8 suficiente, 5-6 básico, 0-4 insuficiente— y el criterio de rediseño
        # del bloque es «ganancia promedio inferior a 2 puntos». Las dos cosas
        # viven en esa escala.
        #
        # El 11-sep-2026 el cuestionario pasó de 10 preguntas a 13, y esto contaba
        # el puntaje ABSOLUTO contra un umbral fijo de 7. El efecto era doble y
        # silencioso: 7 de 13 (54 %) pasaba por «habilitado» cuando la escala pide
        # 70 %, y el promedio mezclaba intentos de 10 con intentos de 13 como si
        # fueran la misma medida.
        #
        # Se normaliza contra `total`, que cada intento guarda. Así la escala
        # aprobada sigue valiendo si mañana el cuestionario cambia otra vez, y
        # nadie tiene que acordarse de mover un número en dos sitios.
        NOTA10 = ExpressionWrapper(
            F('puntaje') * 10.0 / Func(F('total'), function='NULLIF',
                                       template='NULLIF(%(expressions)s, 0)'),
            output_field=FloatField(),
        )
        resumen = intentos.aggregate(
            presentaron=Count('id'),
            promedio=Avg(NOTA10),
            # «No alcanzó Suficiente», que es la barra de «Habilitado para
            # operar» de la escala. El nombre se conserva por compatibilidad.
            insuficientes=Count('id', filter=Q(total__gt=0) & Q(
                puntaje__lt=F('total') * 0.7)),
        )
        # Se dice en la respuesta sobre qué escala está el promedio: un número sin
        # unidad es exactamente cómo se llegó a comparar 7 sobre 13 con 7 sobre 10.
        resumen['escala'] = 10
        resumen['umbral_habilitado'] = 7

        # Ganancia pre → post, emparejando por correo dentro de la misma pareja.
        ganancia = []
        parejas = (Prueba.objects.exclude(pareja='')
                   .values_list('pareja', flat=True).distinct())
        for par in parejas:
            pre = {i.correo_normalizado: i for i in IntentoPrueba.objects.filter(
                prueba__pareja=par, prueba__momento=Prueba.Momento.PRE)}
            post = {i.correo_normalizado: i for i in IntentoPrueba.objects.filter(
                prueba__pareja=par, prueba__momento=Prueba.Momento.POST)}
            for correo in sorted(set(pre) & set(post)):
                a, b = pre[correo], post[correo]
                ganancia.append({
                    'pareja': par,
                    'correo': correo,
                    'nombre': b.nombre or a.nombre,
                    'territorial': b.territorial or a.territorial,
                    'pre': a.puntaje, 'post': b.puntaje,
                    'ganancia': b.puntaje - a.puntaje,
                })

        # Aciertos por pregunta.
        por_pregunta = {}
        for intento in intentos:
            for p in intento.prueba.preguntas.all():
                clave = (intento.prueba.codigo, p.orden)
                fila = por_pregunta.setdefault(clave, {
                    'prueba': intento.prueba.codigo, 'orden': p.orden,
                    'enunciado': p.enunciado, 'aciertos': 0, 'respondieron': 0,
                })
                # ⚠️ Solo cuenta si este intento respondió ESTA pregunta.
                #
                # Antes sumaba `respondieron` para toda pregunta de la prueba, sin
                # mirar si el intento tenía respuesta para ella. El efecto aparece
                # cuando se reemplazan las preguntas —`cargar_prueba_capacitacion
                # --reemplazar`— con intentos ya registrados: sus respuestas quedan
                # apuntando a identificadores borrados, y **las 13 preguntas salen
                # con cero aciertos**, como si el grupo entero las hubiera fallado.
                #
                # Medido en producción el 12-sep-2026: un solo intento viejo hacía
                # que las 13 aparecieran falladas. Y este corte es justamente el que
                # se usa para decidir qué tema se explicó mal.
                clave_resp = str(p.id)
                if clave_resp not in intento.respuestas:
                    continue
                marcada = (intento.respuestas.get(clave_resp) or '').strip().upper()
                fila['respondieron'] += 1
                if marcada == p.correcta.strip().upper():
                    fila['aciertos'] += 1
        preguntas = sorted(por_pregunta.values(), key=lambda f: (f['prueba'], f['orden']))
        for f in preguntas:
            f['porcentaje_acierto'] = (
                round(f['aciertos'] * 100 / f['respondieron']) if f['respondieron'] else 0)

        return Response({
            'resumen': {
                'presentaron': resumen['presentaron'] or 0,
                'promedio': round(resumen['promedio'] or 0, 2),
                'insuficientes': resumen['insuficientes'] or 0,
                # La unidad viaja con el número. Un promedio de «7,7» sin decir
                # sobre qué está es cómo se llegó a comparar 7 sobre 13 con 7
                # sobre 10, y el cuestionario ya cambió de tamaño dos veces.
                'escala': resumen['escala'],
                'umbral_habilitado': resumen['umbral_habilitado'],
            },
            'intentos': IntentoResumenSerializer(intentos, many=True).data,
            'ganancia': ganancia,
            'por_pregunta': preguntas,
        })
