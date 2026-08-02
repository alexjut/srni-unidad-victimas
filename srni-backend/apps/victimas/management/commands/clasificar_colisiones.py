"""
Management command: clasificar_colisiones

Recorre los documentos que aparecen más de una vez en el padrón y deja en
`ColisionDocumento` el veredicto de qué es cada repetición: la misma persona
duplicada por la fuente, la misma con el nombre mal escrito, personas distintas,
o un documento de relleno que no identifica a nadie.

Es un derivado: no toca `Victima`, y volver a correrlo reconstruye la tabla desde
cero. Si el criterio cambia, se corrige `apps/victimas/identidad.py` y se re-corre.

Uso:
    python manage.py clasificar_colisiones               # todo el padrón
    python manage.py clasificar_colisiones --dry-run     # mide sin escribir
    python manage.py clasificar_colisiones --limite 5000 # una cata rápida
"""
from __future__ import annotations

import collections
import time

from django.core.management.base import BaseCommand
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
                            help='Procesar solo los primeros N documentos repetidos.')

    def handle(self, *args, **options):
        dry = options['dry_run']
        limite = options['limite']
        t0 = time.time()

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

        if not dry:
            # Se reconstruye entera: es un derivado, y un borrado parcial dejaría
            # veredictos viejos conviviendo con nuevos sin forma de distinguirlos.
            borradas, _ = ColisionDocumento.objects.all().delete()
            self.stdout.write(f'  tabla anterior limpiada ({borradas:,} filas).')

        conteo = collections.Counter()
        personas_extra = 0     # personas que un colapso ciego por documento perdería
        filas_totales = 0
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
                filas_totales += len(filas)
                if v.n_personas > 1:
                    personas_extra += v.n_personas - 1

                nuevas.append(ColisionDocumento(
                    doc_hash=doc_hash_,
                    clase=v.clase,
                    filas=len(filas),
                    personas=v.n_personas,
                    victima_preferida=v.preferida,
                ))

            if not dry and nuevas:
                with transaction.atomic():
                    ColisionDocumento.objects.bulk_create(nuevas, batch_size=1000)

            procesados += len(lote)
            if procesados % (LOTE * 10) == 0 or procesados >= len(hashes):
                seg = time.time() - t0
                ritmo = procesados / seg if seg else 0
                self.stdout.write(
                    f'  {procesados:,}/{len(hashes):,} documentos '
                    f'({ritmo:,.0f}/s, {seg/60:.1f} min)')

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
