/**
 * El padrón completo en el dispositivo (Fase B2).
 *
 * ── Qué resuelve ────────────────────────────────────────────────────────────
 * Sin señal, la APK conocía **5.000 personas**: las que caben en el trozo que
 * viaja dentro de la precarga (`PRECARGA_LIMITE_PERSONAS`). El padrón real son
 * 5,9 millones. En campo eso significa que buscar una cédula respondía «no está
 * en los datos offline» para casi todo el mundo, con la persona enfrente.
 *
 * El servidor ya genera el archivo desde hace meses —un SQLite organizado por
 * `doc_hash`, ~319 MiB— y lo sirve por `/api/victimas/padron/download/`. Lo que
 * faltaba era del lado del teléfono: nadie lo descargaba ni lo consultaba.
 *
 * ── Qué NO resuelve ─────────────────────────────────────────────────────────
 * El archivo trae a quien tiene ficha en el padrón. A quien está en el universo
 * del RUV y nunca fue entrevistado lo reconoce el filtro (`filtroUniverso`), que
 * es otra cosa y se consulta aparte.
 *
 * ── Decisiones ──────────────────────────────────────────────────────────────
 * 1. **Archivo suelto, no una tabla de la base local.** Igual que el filtro: no
 *    toca el esquema, se borra sin vaciar la base y evita meter 5,9 M de filas
 *    por una migración que no corre en transacción.
 * 2. **Se abre en solo lectura y se consulta por índice.** La tabla es
 *    `WITHOUT ROWID` con clave `(doc_hash, seq)`: buscar es descender un árbol,
 *    no recorrer millones de filas.
 * 3. **La descarga es explícita, no automática.** Son cientos de MB; bajarlos
 *    solos en el plan de datos de la encuestadora sería abusivo. La pantalla de
 *    sincronización ofrece el botón y avisa el peso.
 * 4. **Se guarda la versión junto al archivo.** Si el servidor regenera el
 *    padrón, `hayArchivo()` deja de reconocer el local y se vuelve a ofrecer.
 */
import { File, Paths } from 'expo-file-system';
import * as SQLite from 'expo-sqlite';

import { claveDocumento } from '../crypto/docHash';

/** Nombre del archivo en el directorio de documentos de la app. */
const ARCHIVO = 'padron.sqlite3';

/** Clave en `meta_offline` con la versión del archivo que hay en el teléfono. */
export const CLAVE_VERSION = 'padron_archivo_version';

/** Lo que la precarga publica en `padron_archivo`. */
export interface InfoPadronArchivo {
  url: string;
  version: string;
  checksum?: string;
  esquema?: number;
  hash_bytes?: number;
  total_registros?: number;
}

/** Una persona del padrón, tal como la trae el archivo. */
export interface FilaPadron {
  nombre: string;
  ubicacion: string | null;
  cantidad_hechos: number;
  en_ruv: boolean;
  habilitada: boolean;
  ya_caracterizada: boolean;
  cons_persona: number | null;
  clase_colision: string | null;
}

/** Esquemas del archivo que este cliente sabe leer. */
const ESQUEMAS_SOPORTADOS = [2, 3];

function archivo(): File {
  return new File(Paths.document, ARCHIVO);
}

export function rutaArchivo(): string {
  return archivo().uri;
}

/** ¿Hay archivo descargado? No dice de qué versión: eso lo sabe `precargaDao`. */
export function hayArchivo(): boolean {
  const f = archivo();
  return f.exists && f.size > 0;
}

export function tamanoArchivo(): number {
  const f = archivo();
  return f.exists ? (f.size ?? 0) : 0;
}

/** ¿Sabemos leer el archivo que ofrece el servidor? */
export function esquemaSoportado(info: InfoPadronArchivo | null | undefined): boolean {
  if (!info?.url || !info.version) return false;
  // Sin `esquema` no se puede saber qué trae; el servidor siempre lo manda.
  return typeof info.esquema === 'number' && ESQUEMAS_SOPORTADOS.includes(info.esquema);
}

/**
 * Descarga el padrón completo y lo deja listo para consultar.
 *
 * Devuelve `true` si al terminar hay un archivo consultable. NO lanza: quedarse
 * sin padrón completo degrada la búsqueda sin conexión a lo que había antes, que
 * es peor pero funciona; reventar la precarga por esto sería peor todavía.
 *
 * @param token Bearer del usuario — el endpoint exige sesión y permiso de campo.
 */
export async function descargarPadron(
  info: InfoPadronArchivo,
  token: string,
): Promise<boolean> {
  if (!esquemaSoportado(info)) return false;

  const destino = archivo();
  try {
    // `idempotent`: si quedó el archivo de una versión anterior, se reemplaza.
    await File.downloadFileAsync(info.url, destino, {
      headers: { Authorization: `Bearer ${token}` },
      idempotent: true,
    });
  } catch {
    return false;
  }

  // Un archivo a medias —descarga cortada, que con la red de campo pasa— es un
  // SQLite inválido o, peor, uno válido al que le faltan personas. Se comprueba
  // que abra y que tenga la tabla antes de darlo por bueno.
  if (!(await archivoUtilizable())) {
    try { destino.delete(); } catch { /* `hayArchivo` lo descartará igual */ }
    return false;
  }

  return true;
}

/** Abre el archivo en SOLO LECTURA. Devuelve null si no hay o no se puede. */
async function abrir(): Promise<SQLite.SQLiteDatabase | null> {
  if (!hayArchivo()) return null;
  try {
    // El archivo vive en `document`, no en el directorio de bases de datos de
    // expo-sqlite, así que se abre indicando su carpeta.
    return await SQLite.openDatabaseAsync(ARCHIVO, { useNewConnection: true }, Paths.document.uri);
  } catch {
    return null;
  }
}

/** ¿El archivo descargado abre y tiene la tabla del padrón? */
export async function archivoUtilizable(): Promise<boolean> {
  const db = await abrir();
  if (!db) return false;
  try {
    const fila = await db.getFirstAsync<{ n: number }>(
      "SELECT count(*) AS n FROM sqlite_master WHERE type='table' AND name='padron'",
    );
    return (fila?.n ?? 0) > 0;
  } catch {
    return false;
  } finally {
    try { await db.closeAsync(); } catch { /* ya cerrada */ }
  }
}

/**
 * Busca a una persona por su documento en el archivo local.
 *
 * Devuelve TODAS las filas de ese documento: un documento compartido por varias
 * personas trae varias, y la pantalla debe pedir confirmación en vez de elegir
 * por su cuenta (`clase_colision = 'AMBIGUO'`).
 *
 * Un documento de relleno (`clase_colision = 'NO_IDENTIFICANTE'`) viaja con la
 * marca y SIN datos: no identifica a nadie y no debe devolver el nombre de nadie.
 */
export async function buscarEnArchivo(
  tipoDocumento: string,
  numeroDocumento: string,
): Promise<FilaPadron[]> {
  const db = await abrir();
  if (!db) return [];

  try {
    const clave = claveDocumento(tipoDocumento, numeroDocumento);
    const filas = await db.getAllAsync<{
      nombre: string;
      ubicacion: string | null;
      cantidad_hechos: number;
      flags: number;
      cons_persona: number | null;
      clase_colision: string | null;
    }>(
      'SELECT nombre, ubicacion, cantidad_hechos, flags, cons_persona, clase_colision '
      + 'FROM padron WHERE doc_hash = ? ORDER BY seq',
      [clave],
    );

    return filas.map((f) => ({
      nombre: f.nombre,
      ubicacion: f.ubicacion,
      cantidad_hechos: f.cantidad_hechos ?? 0,
      // bit 0 = en_ruv · bit 1 = habilitada · bit 2 = ya_caracterizada
      en_ruv: (f.flags & 1) !== 0,
      habilitada: (f.flags & 2) !== 0,
      ya_caracterizada: (f.flags & 4) !== 0,
      cons_persona: f.cons_persona,
      clase_colision: f.clase_colision,
    }));
  } catch {
    return [];
  } finally {
    try { await db.closeAsync(); } catch { /* ya cerrada */ }
  }
}

/** Borra el archivo. Lo llama el cierre de sesión, igual que con el filtro. */
export function borrarArchivo(): void {
  const f = archivo();
  if (f.exists) {
    try { f.delete(); } catch { /* si no se puede, queda para la próxima descarga */ }
  }
}
