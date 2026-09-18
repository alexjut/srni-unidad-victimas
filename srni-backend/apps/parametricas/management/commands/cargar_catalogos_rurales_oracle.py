"""
Trae de Oracle los catálogos rurales y étnicos: veredas, resguardos y consejos
comunitarios.

Por qué existe (QA · M5). Las tres tablas de SICAV estaban **vacías** —medido contra
producción el 18-sep-2026: 0 veredas, 0 resguardos, 0 consejos—, así que el sistema no
tenía con qué ofrecer una vereda ni un territorio colectivo. Hoy los instrumentos los
piden como TEXTO LIBRE («Ingrese el nombre de la vereda»), y eso produce el mismo
lugar escrito de diez maneras: no se puede agrupar, ni cruzar, ni contar.

La entidad sí los tiene, en el mismo esquema del sistema anterior:

    RNIENTREVISTA.GIC_N_VEREDAS            32.377   CODDANE_VER · NOMBRE_VER
    RNIENTREVISTA.GIC_RESGUARDOSINDIGENAS     127   CODIGO · OCUPACION
    RNIENTREVISTA.GIC_COMUNIDADESNEGRAS       192   CODIGO · OCUPACION

Solo LEE de Oracle. No escribe una sola fila allá.

Dos cosas que se aprendieron mirando el dato, no suponiéndolo:

1. **El código de vereda trae el municipio adentro.** `0566080` es el municipio DANE
   `05660` más el consecutivo de la vereda. Así se resuelve a qué municipio pertenece,
   que es lo único que el nombre no dice de forma confiable.
2. **El nombre viene compuesto**: `ANTIOQUIA-SAN LUIS-SANTA ISABEL`. Se guarda el
   último tramo —el nombre real de la vereda— porque el departamento y el municipio ya
   están en la relación, y repetirlos ensucia cualquier búsqueda.

Los resguardos y los consejos comunitarios son catálogos NACIONALES: no traen
municipio, y por eso ese campo quedó opcional. Exigirlo obligaría a inventarlo.

Uso:
    python manage.py cargar_catalogos_rurales_oracle --dry-run
    python manage.py cargar_catalogos_rurales_oracle
    python manage.py cargar_catalogos_rurales_oracle --destino local

Idempotente: se puede correr de nuevo sin duplicar.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.parametricas.models import (
    ComunidadNegra, Municipio, ResguardoIndigena, Vereda,
)
from apps.sincronizacion.oracle.conexion import abrir_conexion

LOTE = 2000

# Un catálogo de la entidad trae sus propios rellenos. Traerlos sería ofrecerle al
# encuestador «Sin Informacion» como si fuera un resguardo.
RELLENOS = {'sin informacion', 'sin información', 'no aplica', 'ninguno', 'n/a'}


def _nombre_de_vereda(compuesto: str) -> str:
    """`ANTIOQUIA-SAN LUIS-SANTA ISABEL` → `SANTA ISABEL`."""
    partes = [p.strip() for p in (compuesto or '').split('-') if p.strip()]
    return partes[-1] if partes else ''


class Command(BaseCommand):
    help = 'Carga veredas, resguardos y consejos comunitarios desde Oracle (QA · M5).'

    def add_arguments(self, parser):
        parser.add_argument('--destino', default='produccion',
                            help='produccion (por defecto) o local.')
        parser.add_argument('--dry-run', action='store_true',
                            help='No escribe: cuenta qué entraría y muestra ejemplos.')

    def handle(self, *args, **opts):
        destino = opts['destino']
        dry = opts['dry_run']

        with abrir_conexion(destino) as conexion:
            cursor = conexion.cursor()
            veredas = self._veredas(cursor, dry)
            resguardos = self._catalogo_simple(
                cursor, 'GIC_RESGUARDOSINDIGENAS', ResguardoIndigena, 'RES', dry)
            consejos = self._catalogo_simple(
                cursor, 'GIC_COMUNIDADESNEGRAS', ComunidadNegra, 'CCN', dry)

        etiqueta = '[DRY-RUN] ' if dry else ''
        self.stdout.write(self.style.SUCCESS(
            f'{etiqueta}veredas: {veredas} · resguardos: {resguardos} · '
            f'consejos comunitarios: {consejos}'))
        if dry:
            self.stdout.write('Corré el comando sin --dry-run para aplicarlo.')

    # ── Veredas ──────────────────────────────────────────────────────────────

    def _veredas(self, cursor, dry) -> int:
        cursor.execute(
            'SELECT CODDANE_VER, NOMBRE_VER FROM RNIENTREVISTA.GIC_N_VEREDAS')
        filas = cursor.fetchall()

        # Los municipios se resuelven en memoria: 1.102 filas contra 32.377 veredas,
        # así que una consulta por vereda serían 32.377 viajes a la base para nada.
        municipios = {m.codigo_dane: m for m in Municipio.objects.all()}
        existentes = set(Vereda.objects.values_list('codigo_dane', flat=True))

        nuevas, sin_municipio, ejemplos = [], 0, []
        for codigo, compuesto in filas:
            codigo = (codigo or '').strip()
            nombre = _nombre_de_vereda(compuesto)
            if not codigo or not nombre or codigo in existentes:
                continue

            municipio = municipios.get(codigo[:5])
            if not municipio:
                # Municipios que el catálogo de Oracle conoce y SICAV no (o códigos
                # mal formados). Se cuentan y se informan: perderlos en silencio
                # dejaría veredas invisibles sin que nadie se entere.
                sin_municipio += 1
                continue

            existentes.add(codigo)
            nuevas.append(Vereda(codigo_dane=codigo, nombre=nombre, municipio=municipio))
            if len(ejemplos) < 3:
                ejemplos.append(f'{codigo} · {nombre} ({municipio.nombre})')

        for e in ejemplos:
            self.stdout.write(f'  · {e}')
        if sin_municipio:
            self.stdout.write(self.style.WARNING(
                f'  {sin_municipio} veredas sin municipio conocido en SICAV — se omiten.'))

        if not dry and nuevas:
            with transaction.atomic():
                for i in range(0, len(nuevas), LOTE):
                    Vereda.objects.bulk_create(nuevas[i:i + LOTE], ignore_conflicts=True)

        return len(nuevas)

    # ── Resguardos y consejos comunitarios ───────────────────────────────────

    def _catalogo_simple(self, cursor, tabla, modelo, prefijo, dry) -> int:
        cursor.execute(f'SELECT CODIGO, OCUPACION FROM RNIENTREVISTA.{tabla}')
        filas = cursor.fetchall()

        existentes = set(modelo.objects.values_list('codigo', flat=True))
        nuevos = []
        for codigo, nombre in filas:
            nombre = (nombre or '').strip()
            if not nombre or nombre.lower() in RELLENOS:
                continue
            clave = f'{prefijo}-{codigo}'
            if clave in existentes:
                continue
            existentes.add(clave)
            nuevos.append(modelo(codigo=clave, nombre=nombre))

        if not dry and nuevos:
            modelo.objects.bulk_create(nuevos, ignore_conflicts=True)

        return len(nuevos)
