"""
Management command: generar_padron

Construye el PADRÓN OFFLINE descargable (Fase B del modo offline) como un
archivo COMPACTO, versionado e indexado, listo para que la APK lo descargue una
sola vez y lo consulte localmente sin conexión.

──────────────────────────────────────────────────────────────────────────────
FORMATO ELEGIDO: SQLite prearmado, organizado por `doc_hash`.
──────────────────────────────────────────────────────────────────────────────
¿Por qué SQLite y no NDJSON+gzip?

  * La APK ya trabaja con SQLite local. Un padrón en SQLite se abre/ATTACH y se
    consulta por `doc_hash` en O(log n), SIN cargar millones de filas en memoria.
    Con NDJSON la app tendría que parsear e indexar todo en RAM (o re-importarlo
    a su propio SQLite), justo lo que queremos evitar.
  * Se genera en STREAMING: insertamos por lotes desde `repo.iterar_padron()`,
    así el proceso Django nunca materializa el padrón completo en RAM.
  * Tamaño compacto: ver `ESQUEMA_VERSION` — el hash va en binario truncado y la
    tabla es `WITHOUT ROWID`, que fue lo que llevó el archivo de 896 MB a la
    fracción que ocupa hoy. El VACUUM final compacta lo que quede suelto.

⚠️ El archivo lo LEEN otros: la APK abre este SQLite y consulta `doc_hash`. Si
cambia el esquema hay que subir `ESQUEMA_VERSION` — viaja en el manifiesto para
que un cliente viejo sepa que no entiende lo que descargó, en vez de fallar al
consultarlo.

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

from apps.victimas.bloom import BLOOM_FORMATO, ConstructorBloom
from apps.victimas.repository import get_repository
from apps.victimas.repository.base import doc_hash


FORMATO = 'sqlite'
EXT = 'sqlite3'
PADRON_DIRNAME = 'padron'
MANIFIESTO_NOMBRE = 'padron-latest.json'

#: Versión del ESQUEMA del archivo. Va en el manifiesto para que un cliente sepa
#: si entiende lo que descargó, en vez de fallar al consultarlo.
#:   1 → doc_hash en hexadecimal, tres columnas booleanas, índice aparte
#:   2 → doc_hash BLOB de 16 bytes, WITHOUT ROWID, booleanos en `flags`
#:   3 → + tabla `universo_bloom`: filtro de Bloom de los 12,68 M del universo
ESQUEMA_VERSION = 3

#: Cuántos bytes del SHA-256 se guardan. 16 bytes = 128 bits: con 5 millones de
#: claves la probabilidad de colisión ronda 10⁻²⁶, y el campo solo se usa para
#: comparar por igualdad. En hexadecimal costaba 64 bytes por fila.
HASH_BYTES = 16

# Los tres booleanos, en bits de la columna `flags`.
FLAG_EN_RUV = 1 << 0
FLAG_HABILITADA = 1 << 1
FLAG_YA_CARACTERIZADA = 1 << 2


def _clave(doc_hash_hex: str) -> bytes:
    """El hash del documento como lo guarda el archivo: BLOB de 16 bytes."""
    return bytes.fromhex(doc_hash_hex)[:HASH_BYTES]


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


def _contar_clase(path: str, clase: str) -> int:
    """Cuántas filas del padrón quedaron marcadas con esa clase de colisión."""
    conn = sqlite3.connect(path)
    try:
        return conn.execute(
            'SELECT count(*) FROM padron WHERE clase_colision = ?', (clase,)
        ).fetchone()[0]
    finally:
        conn.close()


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

    #: Lo llena `_escribir_bloom`. Queda en None si no hay universo cargado, y en
    #: ese caso el manifiesto declara `bloom: null` — que es información, no un
    #: hueco: le dice a la APK que ese archivo no reconoce al universo.
    _bloom_info = None

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
            leidos, total = self._construir_sqlite(repo, tmp_path, batch_size)

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
        #
        # `total_registros` sale del `count(*)` del archivo, NO del contador del
        # bucle: son cosas distintas y el 2-ago el manifiesto declaraba 5.926.004
        # registros sobre un archivo de 4.928.725 filas — casi un millón que nadie
        # iba a encontrar. Se declara lo que el archivo tiene.
        #
        # La diferencia con `registros_leidos` ya NO son personas perdidas: los
        # duplicados de la fuente se resuelven antes (una fila por persona) y lo
        # único que se omite acá son las marcas repetidas de los documentos de
        # relleno.
        omitidos = leidos - total
        ambiguos = _contar_clase(destino_final, 'AMBIGUO')
        no_identificantes = _contar_clase(destino_final, 'NO_IDENTIFICANTE')
        manifiesto = {
            'version': version,
            'esquema': ESQUEMA_VERSION,
            'hash_bytes': HASH_BYTES,
            'checksum': checksum,
            'total_registros': total,
            'registros_leidos': leidos,
            'marcas_relleno_omitidas': omitidos,
            # Cuánta ambigüedad lleva este padrón: la APK puede avisar, y sirve
            # para vigilar si la calidad de la fuente mejora o empeora entre cortes.
            'filas_ambiguas': ambiguos,
            'documentos_no_identificantes': no_identificantes,
            'generado_en': generado_en.isoformat(),
            'formato': FORMATO,
            'archivo': archivo_nombre,
            'fuente': fuente,
            # Parámetros del filtro del universo (esquema 3). `null` significa que
            # este archivo NO lleva filtro: la APK debe entonces responder "no
            # encontrada" como antes, en vez de asumir que el universo está vacío.
            'bloom': self._bloom_info,
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
            f'  Registros:  {total} (filas reales en el archivo)\n'
            f'  Leidos:     {leidos} desde la fuente\n'
            f'  Checksum:   {checksum}\n'
            f'  Fuente:     {fuente}\n'
            f'  Limpiados:  {eliminados} archivo(s) viejo(s)\n'
        ))
        if ambiguos or no_identificantes:
            self.stdout.write(self.style.WARNING(
                f'[AVISO] Identidad que la app DEBE confirmar en campo:\n'
                f'  {ambiguos} filas de documentos compartidos por personas distintas\n'
                f'  {no_identificantes} documentos de relleno (no identifican a nadie)\n'
                f'  {omitidos} marcas de relleno repetidas, omitidas\n'
            ))

    # ──────────────────────────────────────────────────────────────────────
    def _construir_sqlite(self, repo, path: str, batch_size: int) -> tuple[int, int]:
        """
        Construye el SQLite del padrón en streaming.

        Inserta por lotes consumiendo `repo.iterar_padron(batch_size)`. NO
        materializa el padrón completo en memoria: como mucho mantiene un lote
        de `batch_size` filas en el buffer de la transacción antes de hacer commit.

        Devuelve `(leidos, filas)`: cuántos registros entregó la fuente y cuántas
        filas quedaron en el archivo. No coinciden cuando hay documentos repetidos
        —ver el comentario del manifiesto en `handle`—.
        """
        conn = sqlite3.connect(path)
        try:
            # PRAGMAs orientados a escritura masiva rápida y archivo compacto.
            conn.execute('PRAGMA journal_mode=OFF;')
            conn.execute('PRAGMA synchronous=OFF;')
            # `doc_hash` YA NO es PRIMARY KEY, y es el arreglo central de este
            # archivo. Con la PK, dos personas distintas que comparten documento
            # colapsaban en una: `INSERT OR REPLACE` pisaba a la primera **sin
            # avisar** y esa víctima desaparecía del padrón que se lleva a campo.
            #
            # Ahora un documento puede tener varias filas, y `clase_colision` dice
            # qué son. Los duplicados de la fuente —el 92 %— ya vienen resueltos
            # desde el repositorio, así que en la práctica solo se repiten los
            # documentos genuinamente ambiguos.
            # ── Formato compacto (esquema 2) ─────────────────────────────────
            #
            # Medido sobre el archivo real de 896 MB: el hash se llevaba el 74 %.
            # 305 MB en la columna (SHA-256 escrito en hexadecimal: 64 bytes por
            # fila para 32 bytes de información) y otros 356 MB en el índice, que
            # guarda una segunda copia del mismo hash.
            #
            # Dos cambios atacan las dos causas:
            #
            # 1. `doc_hash BLOB` con los primeros 16 bytes del SHA-256. El hex se
            #    va (64 → 16 bytes/fila) y siguen sobrando: con 128 bits y 5
            #    millones de claves, la probabilidad de que dos documentos
            #    distintos choquen es del orden de 10⁻²⁶. La comparación por
            #    igualdad es lo único que se hace con este campo, así que truncar
            #    no cambia nada más.
            #
            # 2. `WITHOUT ROWID` con PK compuesta: la tabla ES el índice. Antes
            #    había una copia del hash en la tabla y otra en `idx_padron_doc`.
            #    `seq` está solo para que la llave sea única cuando un documento
            #    tiene varias personas —que es justo lo que este archivo tiene que
            #    poder representar—, y ordena las filas del mismo documento juntas,
            #    así que leerlas cuesta una sola página.
            #
            # 3. Los tres booleanos van en un mapa de bits: SQLite gasta un byte
            #    por columna aunque el valor sea 0/1.
            conn.execute(
                """
                CREATE TABLE padron (
                    doc_hash         BLOB NOT NULL,      -- 16 bytes: SHA-256 truncado
                    seq              INTEGER NOT NULL,   -- desempata dentro del documento
                    nombre           TEXT NOT NULL,
                    ubicacion        TEXT,
                    cantidad_hechos  INTEGER NOT NULL DEFAULT 0,
                    -- bit 0 = en_ruv · bit 1 = habilitada · bit 2 = ya_caracterizada
                    flags            INTEGER NOT NULL DEFAULT 0,
                    cons_persona     INTEGER,                      -- consecutivo Oracle (nullable)
                    -- NULL = documento limpio. 'AMBIGUO' = varias personas lo
                    -- comparten y la app DEBE pedir confirmación.
                    -- 'NO_IDENTIFICANTE' = valor de relleno ('99', '0'): no
                    -- identifica a nadie y no debe devolver datos de nadie.
                    clase_colision   TEXT,
                    PRIMARY KEY (doc_hash, seq)
                ) WITHOUT ROWID;
                """
            )

            insert_sql = (
                'INSERT INTO padron '
                '(doc_hash, seq, nombre, ubicacion, cantidad_hechos, flags, '
                ' cons_persona, clase_colision) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?)'
            )

            leidos = 0
            escritas = 0
            lote: list[tuple] = []
            # Un documento de relleno como `99` tiene 4.297 filas detrás. La marca
            # de "esto no identifica a nadie" se escribe UNA vez: repetirla 4.297
            # veces solo abulta el archivo con filas idénticas y vacías. Son unos
            # pocos cientos de documentos, así que el set no pesa.
            no_identificantes_vistos: set[str] = set()
            for v in repo.iterar_padron(batch_size=batch_size):
                leidos += 1
                clase = getattr(v, 'clase_colision', None)
                h = doc_hash(v.tipo_documento, v.numero_documento)

                # Un documento de relleno no identifica a nadie: viaja la marca,
                # NUNCA los datos. Si viajaran, buscar "99" en campo devolvería a
                # una de 3.780 personas distintas como si fuera la correcta.
                no_identificante = clase == 'NO_IDENTIFICANTE'
                if no_identificante:
                    if h in no_identificantes_vistos:
                        continue
                    no_identificantes_vistos.add(h)

                flags = 0
                if not no_identificante:
                    # 🔴 Sale del universo del RUV, NO de `estado_ruv`.
                    #
                    # Hasta el 12-ago acá decía `v.estado_ruv == 'INCLUIDO'`, y ese
                    # campo llegaba del join por `CONS_PERONA` —un contador de
                    # filas, no un identificador de persona—. Resultado: el padrón
                    # que se descargaban los celulares marcaba ~5 M de fichas como
                    # "Incluida en RUV" copiando el registro de otra persona, y el
                    # encuestador lo leía en pantalla (`busqueda.tsx`).
                    #
                    # `en_universo_ruv` lo pone `iterar_padron` cruzando el
                    # documento contra `PersonaUniverso`, que es el snapshot real
                    # del RUV. Ver `docs/oracle-legacy/join_caracterizacion_roto.md`.
                    if v.en_universo_ruv:
                        flags |= FLAG_EN_RUV
                    if v.habilitado_para_caracterizacion:
                        flags |= FLAG_HABILITADA
                    if v.fecha_ult_caracterizacion:
                        flags |= FLAG_YA_CARACTERIZADA

                lote.append((
                    _clave(h),
                    leidos,          # `seq`: único dentro del documento y creciente
                    '' if no_identificante else _nombre_completo(v),
                    None if no_identificante else v.municipio_residencia_nombre,
                    0 if no_identificante else len(v.hechos_victimizantes or []),
                    flags,
                    None if no_identificante else v.cons_persona,
                    clase,
                ))
                if len(lote) >= batch_size:
                    conn.executemany(insert_sql, lote)
                    conn.commit()
                    escritas += len(lote)
                    lote.clear()

            if lote:
                conn.executemany(insert_sql, lote)
                conn.commit()
                escritas += len(lote)

            # Filas REALES del archivo, antes del VACUUM (que no cambia el conteo
            # pero sí tarda): es lo que la APK va a poder encontrar.
            filas = conn.execute('SELECT count(*) FROM padron;').fetchone()[0]

            # El filtro del universo va DESPUÉS del padrón, para que si la fuente
            # no tiene universo (el mock) el archivo siga siendo válido: la tabla
            # queda vacía y el manifiesto lo declara.
            self._escribir_bloom(conn)

            # Ya no se crea ningún índice: con `WITHOUT ROWID` la tabla está
            # organizada por (doc_hash, seq), o sea que la búsqueda por documento
            # ya usa la propia estructura. El `idx_padron_doc` de la versión
            # anterior pesaba 356 MB — una segunda copia de todos los hashes.

            # VACUUM compacta el archivo final.
            conn.execute('VACUUM;')
            conn.commit()
            return leidos, filas
        finally:
            conn.close()

    # ──────────────────────────────────────────────────────────────────────
    def _escribir_bloom(self, conn) -> None:
        """
        Construye el filtro de Bloom del universo y lo guarda en el archivo.

        ── Por qué se lee así y no con el ORM normal ──────────────────────────
        Son 12,68 M de documentos. `values_list(flat=True).iterator()` trae UNA
        columna con un cursor del lado del servidor: no instancia modelos y, sobre
        todo, **no toca `EncryptedField`**. Instanciar `PersonaUniverso` descifra
        cinco campos por fila — el mismo error que costó tres corridas canceladas
        cargando el universo. Acá solo viajan strings de 64 caracteres.

        ── Por qué NO se deduplica en Python ─────────────────────────────────
        Un `set` de 12,68 M de hashes hex pesa ~1,5 GB. No hace falta: meter dos
        veces el mismo elemento en un Bloom no cambia un solo bit. Los dos flujos
        se vuelcan tal cual y la duplicación sale gratis. Lo único que sí necesita
        el conteo real de únicos es el **dimensionado**, y ese va aparte.
        """
        from apps.victimas.models import PersonaUniverso, Victima

        # Dimensionar con el número de únicos. Se paga un COUNT sobre la unión
        # —minutos— porque errarle es caro en las dos direcciones: quedarse corto
        # llena el filtro y dispara los falsos positivos por encima de lo
        # declarado; pasarse infla el archivo que baja el celular.
        n_unicos = self._contar_universo_unico()
        if not n_unicos:
            self.stdout.write(self.style.WARNING(
                '[AVISO] No hay universo cargado: el archivo va SIN filtro de Bloom.\n'
                '        La APK solo podrá reconocer a quien tenga ficha.'
            ))
            conn.execute(
                'CREATE TABLE universo_bloom ('
                ' formato INTEGER NOT NULL, m INTEGER NOT NULL, k INTEGER NOT NULL,'
                ' n INTEGER NOT NULL, p REAL NOT NULL, bits BLOB NOT NULL)'
            )
            conn.commit()
            return

        bloom = ConstructorBloom(n_unicos)
        self.stdout.write(
            f'  Bloom del universo: {n_unicos} documentos únicos → '
            f'{bloom.m // 8 / 1048576:.1f} MB, k={bloom.k}'
        )

        for modelo in (PersonaUniverso, Victima):
            qs = (modelo.objects
                  .exclude(numero_documento_hash_sin_tipo='')
                  .values_list('numero_documento_hash_sin_tipo', flat=True))
            for h in qs.iterator(chunk_size=50_000):
                bloom.agregar(h)

        real = bloom.falsos_positivos_reales()
        conn.execute(
            'CREATE TABLE universo_bloom ('
            ' formato INTEGER NOT NULL, m INTEGER NOT NULL, k INTEGER NOT NULL,'
            ' n INTEGER NOT NULL, p REAL NOT NULL, bits BLOB NOT NULL)'
        )
        conn.execute(
            'INSERT INTO universo_bloom (formato, m, k, n, p, bits)'
            ' VALUES (?, ?, ?, ?, ?, ?)',
            (BLOOM_FORMATO, bloom.m, bloom.k, n_unicos, real, bloom.to_bytes()),
        )
        conn.commit()

        # Se declara la tasa MEDIDA sobre el filtro construido, no la teórica: si
        # el dimensionado se quedó corto, esta cifra lo dice y la de diseño no.
        self._bloom_info = {
            'formato': BLOOM_FORMATO,
            'm': bloom.m,
            'k': bloom.k,
            'n': n_unicos,
            'documentos_agregados': bloom.n,
            'falsos_positivos': round(real, 6),
            'bytes': bloom.m // 8,
        }
        self.stdout.write(
            f'  Bloom listo: {bloom.n} agregados, '
            f'falsos positivos reales {real:.4%}'
        )

    def _contar_universo_unico(self) -> int:
        """
        Documentos distintos en `PersonaUniverso ∪ Victima`.

        En SQL y no en Python: son 18 M de filas y la unión con `DISTINCT` la
        resuelve Postgres sin traer nada. Devuelve 0 si las tablas no existen
        —el mock no las tiene— para que el generador siga funcionando en pruebas.
        """
        from django.db import connection as django_conn
        from django.db.utils import OperationalError, ProgrammingError

        try:
            with django_conn.cursor() as cur:
                # El techo de tiempo es de PostgreSQL; en los tests la base es
                # SQLite y `SET LOCAL` es un error de sintaxis, no un no-op.
                if django_conn.vendor == 'postgresql':
                    cur.execute("SET LOCAL statement_timeout = '30min'")
                cur.execute("""
                    SELECT COUNT(*) FROM (
                        SELECT numero_documento_hash_sin_tipo AS h
                          FROM victimas_personauniverso
                         WHERE numero_documento_hash_sin_tipo <> ''
                        UNION
                        SELECT numero_documento_hash_sin_tipo
                          FROM victimas_victima
                         WHERE numero_documento_hash_sin_tipo <> ''
                    ) u
                """)
                return cur.fetchone()[0]
        except (ProgrammingError, OperationalError):
            return 0

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
