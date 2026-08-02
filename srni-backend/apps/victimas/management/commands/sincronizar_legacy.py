"""
Management command: sincronizar_legacy

Trae del Oracle legacy lo que pasó desde la última vez: personas nuevas incluidas
en el RUV y hogares recién caracterizados. Pensado para correr **cada pocos
minutos**, no una vez al día.

──────────────────────────────────────────────────────────────────────────────
POR QUÉ ESTO TARDA SEGUNDOS Y LA CARGA COMPLETA TARDA HORAS
──────────────────────────────────────────────────────────────────────────────
No es la misma tarea. `cargar_padron_oracle` lee las 5,9 M de víctimas incluidas
(19 h la primera vez); esto lee **lo que entró desde la última corrida**, que en
el legacy real son ~592 personas y ~270 hogares por día.

Medido contra producción el 2-ago-2026:

    traer 1.500 personas nuevas por PER_IDPERSONA          0,08 s
    ...con el cruce RUV por dblink a Vivanto               5,28 s
    traer los hogares del último día por USU_FECHACREACION 0,03 s

O sea: una corrida completa de esto son **segundos**, y el grueso se va en el
dblink a Vivanto, no en nuestra base.

**La PRIMERA corrida tras arrancar el contenedor tarda ~47 s y las siguientes
~4 s** (medido: 47,2 s y luego 4,2 s con los mismos datos). Es el enlace remoto a
Vivanto calentándose, no trabajo nuestro. Otra razón para correr esto seguido en
vez de una vez al día: encima de traer menos, encuentra el camino caliente.

──────────────────────────────────────────────────────────────────────────────
CADA RECURSO POR EL CAMINO QUE YA ESTÁ INDEXADO
──────────────────────────────────────────────────────────────────────────────
| recurso  | tabla        | se pide por          | por qué                        |
|----------|--------------|----------------------|--------------------------------|
| personas | GIC_PERSONA  | `PER_IDPERSONA >`    | índice único KEY20; la fecha no|
|          |              |                      | está indexada (16 s vs 0,08 s) |
| hogares  | GIC_HOGAR    | `USU_FECHACREACION >=`| ahí sí hay índice sobre fecha  |

──────────────────────────────────────────────────────────────────────────────
LO QUE **NO** HACE
──────────────────────────────────────────────────────────────────────────────
Detecta **altas**, no **modificaciones**: si el legacy corrige el nombre de una
persona que ya teníamos, su id no cambia y esto no la vuelve a traer. La red para
eso sigue siendo la recarga completa mensual (`recargar_padron`).

Tampoco decide identidad: las personas nuevas entran como filas nuevas y quien
resuelve los documentos compartidos es `clasificar_colisiones`, que corre después.

Uso:
    python manage.py sincronizar_legacy                    # DRY-RUN
    python manage.py sincronizar_legacy --confirmar
    python manage.py sincronizar_legacy --confirmar --desde-cero
"""
from __future__ import annotations

import datetime
import time

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.victimas import homologacion as H
from apps.victimas.models import MarcaAguaLegacy


#: Cuánto se retrocede la marca de fecha en cada corrida. Un hogar que se está
#: escribiendo justo cuando leemos puede quedar con un `USU_FECHACREACION` anterior
#: al instante en que consultamos y no aparecer nunca más. Con el solape se relee
#: una ventana pequeña; como el upsert es idempotente, releer no hace daño.
SOLAPE_MINUTOS = 10

#: Tope de seguridad por corrida. Si alguien deja la sincronización apagada un mes
#: y vuelve a encenderla, esto evita que una corrida "de rutina" se convierta en
#: una carga de horas sin que nadie lo haya decidido.
TOPE_FILAS = 50_000

CONSULTA_PERSONAS_NUEVAS = """
    SELECT p.per_idpersona, p.per_tipodoc, p.per_numerodoc,
           p.per_primernombre, p.per_segundonombre,
           p.per_primerapellido, p.per_segundoapellido,
           p.per_fechanacimiento,
           c.pert_etnica, c.genero_hom, c.discap, c.estado_ruv
      FROM gic_persona p
      JOIN RNIPAQUETES.M_CARACT_TABLA_RA_PER@DBL_VIVANTO c
        ON c.cons_perona = p.per_idpersona
     WHERE c.estado_ruv = :estado
       AND p.per_numerodoc IS NOT NULL
       AND TRIM(p.per_numerodoc) IS NOT NULL
       AND p.per_idpersona > :desde
       AND ROWNUM <= :tope
"""

#: Hogares caracterizados desde la marca. Se toma la fecha del hogar y la persona
#: a la que pertenece: es exactamente lo que alimenta `fecha_ult_caracterizacion`.
CONSULTA_HOGARES_NUEVOS = """
    SELECT m.per_idpersona, MAX(h.usu_fechacreacion)
      FROM gic_hogar h
      JOIN gic_miembros_hogar m ON m.hog_codigo = h.hog_codigo
     WHERE h.usu_fechacreacion >= :desde
       AND m.per_idpersona IS NOT NULL
       AND (h.usu_idusuario IS NULL OR h.usu_idusuario <> :usuario_sicav)
     GROUP BY m.per_idpersona
"""

#: El usuario con el que SICAV escribe en el legacy. Sus hogares se EXCLUYEN de la
#: lectura: si no, lo que acabamos de escribir vuelve mañana como "novedad", se
#: reimporta como caracterización del legacy y la persona se bloquea sola. Es el
#: bucle de eco, y no se corta solo — se corta con este AND.
#:
#: Va desde el primer día, semanas antes de encender la escritura automática: el
#: día que se encienda, el freno ya tiene que estar puesto y probado.
USUARIO_SICAV_EN_LEGACY = 999999


class Command(BaseCommand):
    help = ('Trae del Oracle legacy las novedades desde la última corrida '
            '(personas nuevas y hogares caracterizados). DRY-RUN por defecto.')

    def add_arguments(self, parser):
        parser.add_argument('--confirmar', action='store_true',
                            help='Escribe de verdad. Sin él, solo informa.')
        parser.add_argument('--desde-cero', action='store_true',
                            help='Ignora la marca de agua y arranca del principio. '
                                 'Con --confirmar puede traer millones de filas.')
        parser.add_argument('--solo', choices=['personas', 'hogares'],
                            help='Sincronizar un solo recurso.')

    def handle(self, *args, **opts):
        confirmar = opts['confirmar']
        t0 = time.time()

        self.stdout.write(self.style.WARNING(
            'DRY-RUN: no se escribe nada. Usá --confirmar.\n') if not confirmar else '')

        con = self._abrir()
        try:
            if opts['solo'] in (None, 'personas'):
                self._personas(con, confirmar, opts['desde_cero'])
            if opts['solo'] in (None, 'hogares'):
                self._hogares(con, confirmar, opts['desde_cero'])
        finally:
            con.close()

        self.stdout.write(self.style.SUCCESS(
            f'\n[OK] Sincronizacion en {time.time()-t0:.1f}s'))
        if confirmar:
            self.stdout.write(
                '  Recorda correr `clasificar_colisiones` si entraron personas: las '
                'nuevas pueden compartir documento con alguien que ya estaba.')

    # ── personas ─────────────────────────────────────────────────────────────
    def _personas(self, con, confirmar, desde_cero):
        from apps.victimas.models import Victima
        from apps.victimas.repository.base import doc_hash, num_hash

        marca, creada = MarcaAguaLegacy.objects.get_or_create(recurso='personas')
        if creada and marca.ultimo_id is None:
            # Primera vez: la marca NO arranca en cero. El padrón ya está cargado
            # hasta cierto punto, así que arrancar de cero convertiría una corrida
            # "de rutina" en una relectura de 5,9 millones de filas. Se toma el
            # mayor `cons_persona` que ya tenemos: es exactamente "hasta acá ya sé".
            mayor = (Victima.objects.filter(cons_persona__isnull=False)
                     .order_by('-cons_persona')
                     .values_list('cons_persona', flat=True).first())
            marca.ultimo_id = mayor or 0
            marca.save(update_fields=['ultimo_id'])
            self.stdout.write(
                f'  marca inicializada con lo ya cargado: {marca.ultimo_id:,}')

        desde = 0 if desde_cero else (marca.ultimo_id or 0)
        t0 = time.time()

        self.stdout.write(f'\n── PERSONAS ── desde PER_IDPERSONA > {desde:,}')

        cur = con.cursor()
        cur.execute(CONSULTA_PERSONAS_NUEVAS,
                    {'estado': int(H.ESTADO_INCLUIDO), 'desde': desde, 'tope': TOPE_FILAS})
        filas = cur.fetchall()
        cur.close()

        if not filas:
            self.stdout.write('  sin novedades.')
            return

        catalogo = H.cargar_catalogo_tipodoc_oracle()
        tipos = self._tipos_sicav()
        creadas = actualizadas = sin_tipo = 0
        max_id = desde

        for (cons, tipodoc_raw, numero, n1, n2, a1, a2, f_nac,
             etnia, genero, discap, estado) in filas:
            cons = int(cons)
            max_id = max(max_id, cons)
            numero = (numero or '').strip()
            if not numero:
                continue

            codigo_tipo = H.homologar_tipo_documento(tipodoc_raw, catalogo)
            tipo = tipos.get(codigo_tipo) if codigo_tipo else None
            if tipo is None:
                sin_tipo += 1

            if not confirmar:
                continue

            # Mismo criterio que `cargar_padron_oracle`: idempotente por
            # `cons_persona`, así que releer no duplica. Y los hashes se calculan
            # con las MISMAS funciones, nunca con una fórmula reescrita.
            _, creada = Victima.objects.update_or_create(
                cons_persona=cons,
                defaults={
                    'tipo_documento': tipo,
                    'numero_documento': numero,
                    'numero_documento_hash': doc_hash(codigo_tipo or '', numero),
                    'numero_documento_hash_sin_tipo': num_hash(numero),
                    'primer_nombre': (n1 or '').strip(),
                    'segundo_nombre': (n2 or '').strip(),
                    'primer_apellido': (a1 or '').strip(),
                    'segundo_apellido': (a2 or '').strip(),
                    'fecha_nacimiento': f_nac.date().isoformat() if f_nac else '',
                    'genero': H.homologar_genero(genero),
                    'pertenencia_etnica': H.homologar_etnia(etnia),
                    'discapacidad': H.homologar_discapacidad(discap),
                    'estado_ruv': H.homologar_estado_ruv(estado) or 'EN_PROCESO',
                    'fuente_origen': 'RUV',
                },
            )
            creadas += creada
            actualizadas += (not creada)

        seg = time.time() - t0
        self.stdout.write(
            f'  {len(filas):,} leidas · {creadas:,} nuevas · {actualizadas:,} actualizadas'
            f' · {sin_tipo:,} sin tipo de documento   ({seg:.1f}s)')
        if len(filas) >= TOPE_FILAS:
            self.stdout.write(self.style.WARNING(
                f'  [AVISO] se alcanzo el tope de {TOPE_FILAS:,} filas: quedan mas. '
                f'Volve a correrlo (la marca ya avanzo).'))

        if confirmar:
            # La marca avanza SOLO con lo que de verdad se escribió. Si el proceso
            # muere antes de esta línea, la próxima corrida vuelve a traer el lote
            # entero — que es lo correcto: repetir es barato e idempotente, perderse
            # personas no.
            marca.ultimo_id = max_id
            marca.corridas += 1
            marca.filas_ultima_corrida = len(filas)
            marca.segundos_ultima_corrida = seg
            marca.save()
            self.stdout.write(f'  marca de agua → {max_id:,}')

    # ── hogares ──────────────────────────────────────────────────────────────
    def _hogares(self, con, confirmar, desde_cero):
        from apps.victimas.models import Victima

        marca, _ = MarcaAguaLegacy.objects.get_or_create(recurso='hogares')
        cur0 = con.cursor()
        cur0.execute('SELECT SYSDATE FROM DUAL')
        reloj_oracle = cur0.fetchone()[0]
        cur0.close()

        if desde_cero or marca.ultima_fecha is None:
            # Sin marca previa se pide una ventana corta, no la historia entera:
            # para eso está `cargar_fechas_caracterizacion`, que ya sabe hacerlo bien
            # sobre 3,3 M de filas.
            desde = reloj_oracle - datetime.timedelta(days=2)
        else:
            previa = marca.ultima_fecha
            if timezone.is_aware(previa):
                previa = timezone.make_naive(previa, datetime.timezone.utc)
            desde = previa - datetime.timedelta(minutes=SOLAPE_MINUTOS)

        t0 = time.time()
        self.stdout.write(f'\n── HOGARES ── desde {desde:%Y-%m-%d %H:%M} '
                          f'(incluye {SOLAPE_MINUTOS} min de solape)')

        # El instante de corte se toma del reloj de ORACLE, no del nuestro: entre
        # el servidor de aplicaciones y la base hay horas de diferencia, y una marca
        # tomada con `timezone.now()` puede quedar por delante de lo que Oracle
        # todavía no escribió — esas filas no se leerían nunca más.
        cur = con.cursor()
        cur.execute('SELECT SYSDATE FROM DUAL')
        ahora_oracle = cur.fetchone()[0]

        cur.execute(CONSULTA_HOGARES_NUEVOS,
                    {'desde': desde, 'usuario_sicav': USUARIO_SICAV_EN_LEGACY})
        filas = cur.fetchall()
        cur.close()

        if not filas:
            self.stdout.write('  sin novedades.')
            if confirmar:
                marca.ultima_fecha = ahora_oracle
                marca.corridas += 1
                marca.save()
            return

        aplicadas = 0
        if confirmar:
            with transaction.atomic():
                for cons, fecha in filas:
                    if cons is None or fecha is None:
                        continue
                    aplicadas += (
                        Victima.objects
                        .filter(cons_persona=int(cons))
                        .exclude(fecha_ult_caracterizacion=fecha)
                        .update(
                            fecha_ult_caracterizacion=fecha,
                            # La regla de 2 años, aplicada acá mismo: una persona
                            # recién caracterizada deja de estar disponible.
                            habilitado_para_caracterizacion=False,
                        )
                    )

        seg = time.time() - t0
        self.stdout.write(
            f'  {len(filas):,} personas con hogar nuevo · {aplicadas:,} actualizadas '
            f'en SICAV   ({seg:.1f}s)')

        if confirmar:
            marca.ultima_fecha = ahora_oracle
            marca.corridas += 1
            marca.filas_ultima_corrida = len(filas)
            marca.segundos_ultima_corrida = seg
            marca.save()

    # ── conexión ─────────────────────────────────────────────────────────────
    @staticmethod
    def _abrir():
        import os

        import oracledb

        faltan = [v for v in ('ORACLE_PROD_HOST', 'ORACLE_PROD_SERVICE',
                              'ORACLE_PROD_USER', 'ORACLE_PROD_PASSWORD')
                  if not os.environ.get(v)]
        if faltan:
            raise CommandError(f'Faltan variables de entorno: {", ".join(faltan)}')
        return oracledb.connect(
            user=os.environ['ORACLE_PROD_USER'],
            password=os.environ['ORACLE_PROD_PASSWORD'],
            dsn=(f"{os.environ['ORACLE_PROD_HOST']}:"
                 f"{os.environ.get('ORACLE_PROD_PORT', '1521')}/"
                 f"{os.environ['ORACLE_PROD_SERVICE']}"),
        )

    @staticmethod
    def _tipos_sicav():
        from apps.parametricas.models import TipoDocumento
        return {t.codigo: t for t in TipoDocumento.objects.all()}
