"""
Management command: generar_padron

Construye el PADRÓN OFFLINE descargable (Fase B del modo offline) como un
archivo COMPACTO, versionado e indexado, listo para que la APK lo descargue una
sola vez y lo consulte localmente sin conexión.

──────────────────────────────────────────────────────────────────────────────
FORMATO ELEGIDO: SQLite prearmado, indexado por `doc_hash`.
──────────────────────────────────────────────────────────────────────────────
¿Por qué SQLite y no NDJSON+gzip?

  * La APK ya trabaja con SQLite local. Un padrón en SQLite se abre/ATTACH y se
    consulta por `doc_hash` en O(log n) usando el índice, SIN cargar 10M filas
    en memoria. Con NDJSON la app tendría que parsear e indexar todo en RAM (o
    re-importarlo a su propio SQLite), justo lo que queremos evitar.
  * Se genera en STREAMING: insertamos por lotes desde `repo.iterar_padron()`,
    así el proceso Django nunca materializa el padrón completo en RAM.
  * Tamaño compacto: VACUUM al final + solo los campos del resumen (sin hechos).

Si en el futuro se prefiere NDJSON gzip (p.ej. para padrones diminutos servidos
por CDN), el mecanismo de manifiesto/versión/endpoints es idéntico — solo cambia
el escritor del archivo.

──────────────────────────────────────────────────────────────────────────────
ORACLE-READY
──────────────────────────────────────────────────────────────────────────────
El command NO sabe de dónde salen los datos: itera `get_repository().iterar_padron
(batch_size)`. La fuente queda 100 % detrás de la interfaz del repo. En el mock
se itera un dict; en `OracleVictimaRepository` ese método DEBE usar un
server-side cursor con fetchmany por lotes (ver doc en repository/base.py y
repository/mock.py). No hay que reescribir este command para producción.

──────────────────────────────────────────────────────────────────────────────
SALIDA
──────────────────────────────────────────────────────────────────────────────
  MEDIA_ROOT/padron/padron-<version>.sqlite3   ← archivo del padrón
  MEDIA_ROOT/padron/padron-latest.json         ← manifiesto (version, checksum…)

`version` = '<YYYYMMDDHHMMSS>-<checksum8>' (fecha de generación + 8 hex del sha256).

Idempotente y re-ejecutable. Limpia versiones viejas dejando las últimas N
(--keep, default 3) más el manifiesto.

Uso:
    python manage.py generar_padron
    python manage.py generar_padron --batch-size 5000 --keep 5
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.victimas.repository import get_repository
from apps.victimas.repository.base import doc_hash


FORMATO = 'sqlite'
EXT = 'sqlite3'
PADRON_DIRNAME = 'padron'
MANIFIESTO_NOMBRE = 'padron-latest.json'


def _nombre_completo(v) -> str:
    """Nombre completo del VictimaResumen omitiendo partes vacías."""
    partes = [v.primer_nombre, v.segundo_nombre, v.primer_apellido, v.segundo_apellido]
    return ' '.join(p for p in partes if p)


def _padron_dir() -> str:
    base = getattr(settings, 'MEDIA_ROOT', None)
    if not base:
        raise RuntimeError('MEDIA_ROOT no está configurado; no se puede generar el padrón.')
    ruta = os.path.join(str(base), PADRON_DIRNAME)
    os.makedirs(ruta, exist_ok=True)
    return ruta


def _sha256_archivo(path: str, _bufsize: int = 1024 * 1024) -> str:
    """SHA-256 del archivo leyendo por bloques (no carga el archivo entero)."""
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(_bufsize), b''):
            h.update(chunk)
    return h.hexdigest()


class Command(BaseCommand):
    help = 'Genera el padrón offline descargable (SQLite indexado) + manifiesto versionado.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size', type=int, default=1000,
            help='Tamaño de lote para insertar/commit en streaming (default: 1000).',
        )
        parser.add_argument(
            '--keep', type=int, default=3,
            help='Cuántas versiones del padrón conservar (default: 3).',
        )

    def handle(self, *args, **options):
        batch_size = max(1, options['batch_size'])
        keep = max(1, options['keep'])

        repo = get_repository()
        fuente = getattr(repo, 'FUENTE', 'DESCONOCIDA')
        destino_dir = _padron_dir()

        # 1. Escribir a un archivo TEMPORAL en el mismo directorio (commit atómico
        #    al renombrar). Así un fallo a mitad no deja un padrón corrupto servido.
        fd, tmp_path = tempfile.mkstemp(suffix=f'.{EXT}', dir=destino_dir)
        os.close(fd)

        total = 0
        try:
            total = self._construir_sqlite(repo, tmp_path, batch_size)

            # 2. Checksum y versión a partir del archivo ya cerrado.
            checksum = _sha256_archivo(tmp_path)
            generado_en = timezone.now()
            version = f"{generado_en.strftime('%Y%m%d%H%M%S')}-{checksum[:8]}"
            archivo_nombre = f'padron-{version}.{EXT}'
            destino_final = os.path.join(destino_dir, archivo_nombre)

            # 3. Mover el temporal a su nombre versionado definitivo.
            os.replace(tmp_path, destino_final)
            tmp_path = None  # ya no hay que limpiarlo
        except Exception:
            # Limpieza del temporal si algo falló.
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise

        # 4. Manifiesto (padron-latest.json).
        manifiesto = {
            'version': version,
            'checksum': checksum,
            'total_registros': total,
            'generado_en': generado_en.isoformat(),
            'formato': FORMATO,
            'archivo': archivo_nombre,
            'fuente': fuente,
        }
        manifiesto_path = os.path.join(destino_dir, MANIFIESTO_NOMBRE)
        with open(manifiesto_path, 'w', encoding='utf-8') as fh:
            json.dump(manifiesto, fh, ensure_ascii=False, indent=2)

        # 5. Limpiar versiones viejas (deja las últimas N + el archivo actual).
        eliminados = self._limpiar_viejos(destino_dir, conservar=archivo_nombre, keep=keep)

        self.stdout.write(self.style.SUCCESS(
            f'\n[OK] Padron generado:\n'
            f'  Archivo:    {destino_final}\n'
            f'  Manifiesto: {manifiesto_path}\n'
            f'  Version:    {version}\n'
            f'  Registros:  {total}\n'
            f'  Checksum:   {checksum}\n'
            f'  Fuente:     {fuente}\n'
            f'  Limpiados:  {eliminados} archivo(s) viejo(s)\n'
        ))

    # ──────────────────────────────────────────────────────────────────────
    def _construir_sqlite(self, repo, path: str, batch_size: int) -> int:
        """
        Construye el SQLite del padrón en streaming.

        Inserta por lotes consumiendo `repo.iterar_padron(batch_size)`. NO
        materializa el padrón completo en memoria: como mucho mantiene un lote
        de `batch_size` filas en el buffer de la transacción antes de hacer commit.
        """
        conn = sqlite3.connect(path)
        try:
            # PRAGMAs orientados a escritura masiva rápida y archivo compacto.
            conn.execute('PRAGMA journal_mode=OFF;')
            conn.execute('PRAGMA synchronous=OFF;')
            conn.execute(
                """
                CREATE TABLE padron (
                    doc_hash         TEXT PRIMARY KEY,   -- SHA-256 canónico del documento
                    nombre           TEXT NOT NULL,
                    ubicacion        TEXT,
                    cantidad_hechos  INTEGER NOT NULL DEFAULT 0,
                    en_ruv           INTEGER NOT NULL DEFAULT 0,   -- bool 0/1
                    habilitada       INTEGER NOT NULL DEFAULT 0,   -- bool 0/1
                    ya_caracterizada INTEGER NOT NULL DEFAULT 0,   -- bool 0/1
                    cons_persona     INTEGER                       -- consecutivo Oracle (nullable)
                );
                """
            )

            insert_sql = (
                'INSERT OR REPLACE INTO padron '
                '(doc_hash, nombre, ubicacion, cantidad_hechos, en_ruv, '
                ' habilitada, ya_caracterizada, cons_persona) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?)'
            )

            total = 0
            lote: list[tuple] = []
            for v in repo.iterar_padron(batch_size=batch_size):
                lote.append((
                    doc_hash(v.tipo_documento, v.numero_documento),
                    _nombre_completo(v),
                    v.municipio_residencia_nombre,
                    len(v.hechos_victimizantes or []),
                    1 if v.estado_ruv == 'INCLUIDO' else 0,
                    1 if v.habilitado_para_caracterizacion else 0,
                    1 if v.fecha_ult_caracterizacion else 0,
                    v.cons_persona,
                ))
                if len(lote) >= batch_size:
                    conn.executemany(insert_sql, lote)
                    conn.commit()
                    total += len(lote)
                    lote.clear()

            if lote:
                conn.executemany(insert_sql, lote)
                conn.commit()
                total += len(lote)

            # PRIMARY KEY ya indexa doc_hash; VACUUM compacta el archivo final.
            conn.execute('VACUUM;')
            conn.commit()
            return total
        finally:
            conn.close()

    # ──────────────────────────────────────────────────────────────────────
    def _limpiar_viejos(self, destino_dir: str, conservar: str, keep: int) -> int:
        """
        Borra los archivos de padrón más viejos dejando las últimas `keep`
        versiones (incluyendo siempre el `conservar` recién generado).
        """
        archivos = [
            f for f in os.listdir(destino_dir)
            if f.startswith('padron-') and f.endswith(f'.{EXT}')
        ]
        # Orden por mtime descendente (más nuevo primero).
        archivos.sort(
            key=lambda f: os.path.getmtime(os.path.join(destino_dir, f)),
            reverse=True,
        )
        a_conservar = set(archivos[:keep]) | {conservar}
        eliminados = 0
        for f in archivos:
            if f not in a_conservar:
                try:
                    os.remove(os.path.join(destino_dir, f))
                    eliminados += 1
                except OSError:
                    pass
        return eliminados
