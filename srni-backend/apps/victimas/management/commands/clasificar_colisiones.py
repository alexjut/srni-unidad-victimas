"""
Management command: clasificar_colisiones

Recorre los documentos que aparecen más de una vez en el padrón y deja en
`ColisionDocumento` el veredicto de qué es cada repetición: la misma persona
duplicada por la fuente, la misma con el nombre mal escrito, personas distintas,
o un documento de relleno que no identifica a nadie.

Es un derivado: no toca `Victima`, y volver a correrlo reconstruye la tabla desde
cero. Si el criterio cambia, se corrige `apps/victimas/identidad.py` y se re-corre.

Uso:
    python manage.py clasificar_colisiones                          # todo el padrón
    python manage.py clasificar_colisiones --dry-run                # mide sin escribir
    python manage.py clasificar_colisiones --limite 5000 --dry-run  # cata rápida
"""
from __future__ import annotations

import collections
import contextlib
import time

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from apps.victimas.identidad import clasificar_grupo
from apps.victimas.models import ColisionDocumento, Victima


# Cuántos documentos se procesan por vuelta. El costo real no es el SQL sino
# descifrar nombre y fecha de cada fila (Fernet, en Python), así que el lote se
# mide en documentos y no en filas.
LOTE = 2000


class Command(BaseCommand):
    help = ('Clasifica los documentos repetidos del padrón: duplicado de la fuente, '
            'variante del nombre, personas distintas, o documento de relleno.')

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Mide y reporta sin escribir ColisionDocumento.')
        parser.add_argument('--limite', type=int, default=None,
                            help='Procesar solo los primeros N documentos repetidos. '
                                 'Solo con --dry-run: es una cata, no una corrida.')

    def handle(self, *args, **options):
        dry = options['dry_run']
        limite = options['limite']
        t0 = time.time()

        # `--limite` sin `--dry-run` sería destructivo y nada lo avisaría: la
        # corrida borra la tabla entera y la reescribe, así que limitar a N
        # dejaría al padrón sin los veredictos de los otros 763 mil documentos —y
        # sin veredicto, el padrón offline vuelve a colapsar por documento—.
        if limite and not dry:
            raise CommandError(
                '--limite es una cata y solo tiene sentido con --dry-run. Sin él, '
                'la corrida borraría los veredictos de TODOS los documentos '
                'repetidos y dejaría solo los primeros N.'
            )

        self.stdout.write('Buscando documentos repetidos…')
        sql = """
            SELECT numero_documento_hash
            FROM victimas_victima
            GROUP BY numero_documento_hash
            HAVING count(*) > 1
        """
        if limite:
            sql += f' LIMIT {int(limite)}'
        with connection.cursor() as cur:
            cur.execute(sql)
            hashes = [r[0] for r in cur.fetchall()]

        self.stdout.write(f'  {len(hashes):,} documentos repetidos.')

        conteo = collections.Counter()
        # Contadores compartidos con `_clasificar` (que corre dentro de la
        # transacción): `personas_extra` son las personas que un colapso ciego por
        # documento perdería.
        acumulador = {'filas': 0, 'personas_extra': 0}

        # TODO el trabajo va en UNA transacción, borrado incluido. El motivo es
        # operativo: la corrida tarda ~25 min sobre 768 mil documentos y esta red
        # se cae seguido. Con el borrado fuera de la transacción, un proceso muerto
        # a la mitad dejaba la tabla con la mitad de los veredictos, y esa mitad es
        # indistinguible de una corrida completa —el padrón siguiente saldría sin
        # los AMBIGUO que faltaron, borrando personas—. Ahora, o queda la
        # clasificación nueva entera, o queda intacta la anterior.
        #
        # Gracias al MVCC de PostgreSQL, mientras tanto la búsqueda sigue leyendo
        # los veredictos viejos sin bloquearse.
        contexto = contextlib.nullcontext() if dry else transaction.atomic()
        with contexto:
            if not dry:
                # Se reconstruye entera: es un derivado, y un borrado parcial
                # dejaría veredictos viejos conviviendo con nuevos.
                borradas, _ = ColisionDocumento.objects.all().delete()
                self.stdout.write(f'  tabla anterior limpiada ({borradas:,} filas).')
            self._clasificar(hashes, dry=dry, conteo=conteo, t0=t0,
                             acumulador=acumulador)

        filas_totales = acumulador['filas']
        personas_extra = acumulador['personas_extra']

        # ── Informe ───────────────────────────────────────────────────────────
        total = sum(conteo.values()) or 1
        self.stdout.write(self.style.SUCCESS('\n[OK] Clasificacion terminada.'))
        self.stdout.write(f'  Documentos repetidos: {total:,}')
        self.stdout.write(f'  Filas involucradas:   {filas_totales:,}')
        for clase, n in conteo.most_common():
            self.stdout.write(f'    {n:>9,}  ({100.0*n/total:5.1f} %)  {clase}')

        self.stdout.write(
            f'\n  Personas distintas que un colapso por documento borraria: '
            f'{personas_extra:,}')
        ambiguos = conteo.get('AMBIGUO', 0) + conteo.get('NO_IDENTIFICANTE', 0)
        self.stdout.write(
            f'  Documentos que exigen confirmar identidad: {ambiguos:,} '
            f'({100.0*ambiguos/total:.1f} % de los repetidos)')

        if dry:
            self.stdout.write(self.style.WARNING('\n  --dry-run: no se escribio nada.'))


    def _clasificar(self, hashes, *, dry, conteo, t0, acumulador):
        procesados = 0
        for i in range(0, len(hashes), LOTE):
            lote = hashes[i:i + LOTE]
            filas_por_doc: dict[str, list] = collections.defaultdict(list)
            qs = (Victima.objects
                  .filter(numero_documento_hash__in=lote)
                  .only('id', 'numero_documento', 'numero_documento_hash',
                        'primer_nombre', 'segundo_nombre', 'primer_apellido',
                        'segundo_apellido', 'fecha_nacimiento', 'genero',
                        'pertenencia_etnica', 'tipo_discapacidad',
                        'municipio_residencia_id', 'cons_persona', 'estado_ruv',
                        'fecha_ult_caracterizacion'))
            for v in qs.iterator(chunk_size=5000):
                filas_por_doc[v.numero_documento_hash].append(v)

            nuevas = []
            for doc_hash_, filas in filas_por_doc.items():
                # El número en claro solo se usa para reconocer los valores de
                # relleno; no se guarda en ningún lado.
                numero = str(filas[0].numero_documento) if filas[0].numero_documento else ''
                v = clasificar_grupo(filas, numero_documento=numero)

                conteo[v.clase] += 1
                acumulador['filas'] += len(filas)
                if v.n_personas > 1:
                    acumulador['personas_extra'] += v.n_personas - 1

                nuevas.append(ColisionDocumento(
                    doc_hash=doc_hash_,
                    clase=v.clase,
                    filas=len(filas),
                    personas=v.n_personas,
                    victima_preferida=v.preferida,
                ))

            if not dry and nuevas:
                # Sin `atomic` propio: ya corre dentro de la transacción única.
                ColisionDocumento.objects.bulk_create(nuevas, batch_size=1000)

            procesados += len(lote)
            if procesados % (LOTE * 10) == 0 or procesados >= len(hashes):
                seg = time.time() - t0
                ritmo = procesados / seg if seg else 0
                self.stdout.write(
                    f'  {procesados:,}/{len(hashes):,} documentos '
                    f'({ritmo:,.0f}/s, {seg/60:.1f} min)')
