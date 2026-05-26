/**
 * Carga inicial de instrumentos desde assets empaquetados (Sprint 18).
 *
 * Arquitectura híbrida:
 *  - El APK trae los 8 instrumentos en srni-mobile/assets/instrumentos/
 *  - Al iniciar la app, si SQLite no tiene un instrumento (o tiene una
 *    versión vieja), se carga desde el bundle (instantáneo, sin red).
 *  - La función descargarInstrumento(perfil) del servicio sincronizacion.ts
 *    se mantiene SOLO para sync remoto cuando haya versión más nueva en
 *    el servidor.
 *
 * Beneficios:
 *  - Funciona offline desde el primer login
 *  - Adiós al bug 'database is locked' por descargas concurrentes
 *  - Encuestador en campo no depende de red para empezar
 *  - Cualquier instrumento disponible desde el primer minuto
 */
import * as instrumentoDao from '../db/instrumentoDao';

// Static requires — Metro los empaqueta en el bundle JS automáticamente.
// Si agregas un nuevo instrumento, agrégalo aquí también.
const BUNDLED = {
  ASISTENCIA:        require('../../assets/instrumentos/asistencia_v8.json'),
  BUENAVENTURA:      require('../../assets/instrumentos/buenaventura_v7.json'),
  RURAL_ETNICO:      require('../../assets/instrumentos/rural_etnico_v1.json'),
  SAN_ANDRES:        require('../../assets/instrumentos/san_andres_v7.json'),
  TELEFONICO:        require('../../assets/instrumentos/telefonico_v8.json'),
  TERRITORIAL:       require('../../assets/instrumentos/territorial_v7.json'),
  URBANO_ETNICO:     require('../../assets/instrumentos/urbano_etnico_v1.json'),
  VICTIMAS_EXTERIOR: require('../../assets/instrumentos/victimas_exterior_v1.json'),
} as const;

export type PerfilCodigo = keyof typeof BUNDLED;

/** Devuelve la lista de códigos disponibles en el bundle. */
export function listaPerfilesBundled(): PerfilCodigo[] {
  return Object.keys(BUNDLED) as PerfilCodigo[];
}

/**
 * Carga UN instrumento específico desde el bundle al SQLite.
 * Sobrescribe lo que esté en SQLite (mismo comportamiento que la descarga remota).
 */
export async function cargarInstrumentoBundled(perfil: PerfilCodigo): Promise<void> {
  const { log } = await import('./logger');
  const data = BUNDLED[perfil];
  if (!data) throw new Error(`Perfil bundled no existe: ${perfil}`);
  log.event('BUNDLE', `Cargando ${perfil} v${data.version} desde asset`);
  await instrumentoDao.guardarInstrumentoCompleto(data as any);
  log.event('BUNDLE', `${perfil} OK en SQLite`);
}

/**
 * Asegura que SQLite tenga UN instrumento específico cargado.
 * Si meta ya apunta al mismo (instrumento_id + version) y hay capítulos
 * físicos, no hace nada. Si no, carga desde el bundle.
 *
 * Llamar antes de entrar al formulario de un instrumento.
 */
export async function asegurarInstrumentoLocal(perfil: PerfilCodigo): Promise<void> {
  const { log } = await import('./logger');
  const data = BUNDLED[perfil];
  if (!data) throw new Error(`Perfil bundled no existe: ${perfil}`);

  const meta = await instrumentoDao.getMeta();
  const caps = await instrumentoDao.getCapitulos();
  const yaEstaListo =
    meta?.instrumento_id === data.id &&
    meta?.version === data.version &&
    caps.length > 0;

  if (yaEstaListo) {
    log.event('BUNDLE', `${perfil} ya estaba listo en SQLite`, { caps: caps.length });
    return;
  }

  await cargarInstrumentoBundled(perfil);
}
