/**
 * Traduce un error de la API a algo que el encuestador pueda leer y actuar.
 *
 * ─── Por qué existe (APK-002) ────────────────────────────────────────────────
 * QA reportó «error intermitente al conformar hogar, sin información de
 * diagnóstico suficiente». La causa no era el error sino cómo se mostraba:
 *
 *     const detalle = err?.response?.data;
 *     if (typeof detalle === 'object') setErrorHogar(JSON.stringify(detalle));
 *
 * Eso le ponía enfrente el JSON crudo del servidor —llaves, comillas y nombres
 * de campos internos—. Y como en JavaScript `typeof null === 'object'`, una
 * respuesta con cuerpo vacío le mostraba literalmente la palabra **«null»**,
 * que es lo más parecido a no decir nada.
 *
 * Lo intermitente se explica solo: el mismo intento falla distinto según haya
 * red, la víctima tenga un hogar de otro encuestador (409) o el cuerpo venga
 * vacío — y las tres cosas se veían igual de opacas.
 *
 * ─── Qué hace ────────────────────────────────────────────────────────────────
 * Distingue los tres casos que en campo exigen acciones distintas:
 *
 *   · Sin red        → esperar o moverse; el trabajo no se pierde.
 *   · Servidor dijo  → el texto del servidor, tal cual, que ya viene redactado
 *                      para el encuestador (ej. el 409 de hogar ajeno).
 *   · Otra cosa      → mensaje propio + el código HTTP, para que soporte tenga
 *                      por dónde empezar.
 */

export interface ErrorLegible {
  /** Lo que se le muestra a la persona. */
  mensaje: string;
  /** `true` si no hubo respuesta del servidor (sin señal, timeout, DNS). */
  sinRed: boolean;
  /** Código HTTP, cuando lo hubo. */
  estado?: number;
  /** Resumen técnico para el reporte de errores — NO para la pantalla. */
  diagnostico: string;
}

const MSG_SIN_RED =
  'Sin conexión con el servidor. Su trabajo no se pierde: vuelva a intentarlo '
  + 'cuando tenga señal.';

/** Campos del backend que no significan nada para quien está en campo. */
function nombreLegible(campo: string): string {
  const nombres: Record<string, string> = {
    autorizado: 'Persona autorizada',
    municipio: 'Municipio',
    tipo_documento: 'Tipo de documento',
    numero_documento: 'Número de documento',
    parentesco: 'Parentesco',
    fecha_nacimiento: 'Fecha de nacimiento',
    non_field_errors: '',
  };
  if (campo in nombres) return nombres[campo];
  return campo.replace(/_/g, ' ');
}

export function interpretarError(err: any, porDefecto: string): ErrorLegible {
  const respuesta = err?.response;

  // Sin respuesta = no llegamos al servidor. Es el caso más común en campo y el
  // único donde la acción es esperar, no reportar.
  if (!respuesta) {
    return {
      mensaje: MSG_SIN_RED,
      sinRed: true,
      diagnostico: `sin respuesta: ${err?.message ?? 'desconocido'}`,
    };
  }

  const estado: number = respuesta.status;
  const datos = respuesta.data;
  const base = { sinRed: false, estado };

  // `detail` es lo que usa DRF para los mensajes redactados a mano — y los del
  // backend ya están escritos para el encuestador ("Solicita su reasignación al
  // supervisor"). Se muestra tal cual.
  if (datos && typeof datos.detail === 'string' && datos.detail.trim()) {
    return { ...base, mensaje: datos.detail, diagnostico: `HTTP ${estado}: ${datos.detail}` };
  }

  // Errores por campo: se arman legibles en vez de volcar el JSON.
  if (datos && typeof datos === 'object' && !Array.isArray(datos)) {
    const partes = Object.entries(datos)
      .map(([campo, valor]) => {
        const texto = [valor].flat().filter((v) => typeof v === 'string').join(' ');
        if (!texto) return '';
        const etiqueta = nombreLegible(campo);
        return etiqueta ? `${etiqueta}: ${texto}` : texto;
      })
      .filter(Boolean);

    if (partes.length) {
      return {
        ...base,
        mensaje: partes.join('\n'),
        diagnostico: `HTTP ${estado}: ${JSON.stringify(datos).slice(0, 300)}`,
      };
    }
  }

  // Cuerpo vacío, `null`, o algo que no sabemos leer. Acá caía el «null».
  // Se muestra el mensaje propio CON el código, que es lo que le permite a
  // soporte distinguir un 500 de un 403 sin pedirle capturas al encuestador.
  return {
    ...base,
    mensaje: `${porDefecto} (código ${estado})`,
    diagnostico: `HTTP ${estado}: cuerpo ${JSON.stringify(datos ?? null).slice(0, 200)}`,
  };
}

/** Atajo cuando solo se necesita el texto. */
export function mensajeDeError(err: any, porDefecto: string): string {
  return interpretarError(err, porDefecto).mensaje;
}
