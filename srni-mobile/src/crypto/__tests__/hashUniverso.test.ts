/**
 * El contrato con el backend, fijado en números.
 *
 * Estos valores NO se inventaron: salieron de ejecutar el propio backend
 * (`apps/victimas/repository/base.py` y `apps/victimas/bloom.py`) el 11-ago-2026.
 * Si un cambio en la normalización los mueve, el padrón descargable deja de
 * encontrar a nadie y **no hay excepción que lo avise** — por eso están escritos
 * literalmente aquí y no calculados.
 */
import { contiene, contieneCon, esUsable, indicesDe } from '../bloom';
import { claveDocumento, docHash, normalizarDoc, numHash } from '../docHash';
import { bytesAHex, hexABytes, sha256Hex, utf8Bytes } from '../sha256';

// ── SHA-256: vectores oficiales de NIST ─────────────────────────────────────

describe('sha256', () => {
  test('vectores conocidos de FIPS 180-4', () => {
    expect(sha256Hex('abc')).toBe(
      'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad',
    );
    expect(sha256Hex('')).toBe(
      'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    );
  });

  test('entrada larga: cruza varios bloques de 64 bytes', () => {
    expect(sha256Hex('a'.repeat(1000))).toBe(
      '41edece42d63e8d9bf515a9ba6932e1c20cbc9f5a5d134645adb5db1b9737ea3',
    );
  });

  test('hashea BYTES UTF-8, no unidades UTF-16', () => {
    // El valor es el de Python: sha256('niño'.encode('utf-8')). Si esta
    // implementación recorriera charCodeAt como el hash viejo del móvil, daría
    // otro resultado — y solo se notaría con documentos no numéricos.
    expect(sha256Hex('niño')).toBe(
      'd6108ffef03cf18f9cee2f691c4eb52ac74432f0d12e04497312032c10d9f273',
    );
    expect(Array.from(utf8Bytes('ñ'))).toEqual([0xc3, 0xb1]);
    expect(Array.from(utf8Bytes('a'))).toEqual([0x61]);
  });

  test('hex y bytes son inversos', () => {
    const hex = sha256Hex('1234567890');
    expect(bytesAHex(hexABytes(hex))).toBe(hex);
    expect(hexABytes(hex)).toHaveLength(32);
  });
});

// ── Normalización canónica ──────────────────────────────────────────────────

describe('normalizarDoc', () => {
  test('produce la cadena canónica del backend', () => {
    expect(normalizarDoc('CC', '99.901.000-01')).toBe('cc|9990100001');
    expect(normalizarDoc(' cc ', '9990100001')).toBe('cc|9990100001');
    expect(normalizarDoc('TI', '1061598492')).toBe('ti|1061598492');
  });

  test('MINÚSCULAS, no mayúsculas', () => {
    // El hash viejo del móvil normaliza a MAYÚSCULAS. Con cédulas numéricas da
    // igual; con un pasaporte alfanumérico el resultado sería otro y el padrón
    // no encontraría nunca a esa persona, sin error visible.
    expect(normalizarDoc('PA', 'AB12345')).toBe('pa|ab12345');
  });

  test('quita diacríticos', () => {
    expect(normalizarDoc('cc', 'áé')).toBe('cc|ae');
  });
});

// ── doc_hash: la llave de la tabla `padron` ─────────────────────────────────

describe('docHash', () => {
  test('coincide con doc_hash del backend', () => {
    expect(docHash('CC', '99.901.000-01')).toBe(
      'd4d543f3ecc2e19418c1171a829a3eb25ee5d2fa14cc487a72bddb0885150282',
    );
    expect(docHash('TI', '1061598492')).toBe(
      '8bedc8ba77db584dec6b1a40d3f968444a4476b48e40611fdbdad08490257c9a',
    );
    expect(docHash('PA', 'ab12345')).toBe(
      'd0809719309f62023c7abbe16b26207e72a4186c0b8bd2c9f3af629978d12ef5',
    );
    expect(docHash('CC', '28683981')).toBe(
      '847ffa3669fe173309547717942e7a37e0ce50283ae8142b7b565f322af22fc9',
    );
  });

  test('el formato del número no cambia el hash', () => {
    const base = docHash('CC', '9990100001');
    expect(docHash('CC', '99.901.000-01')).toBe(base);
    expect(docHash(' cc ', '9990100001')).toBe(base);
  });

  test('claveDocumento son los primeros 16 bytes, como en el archivo', () => {
    const clave = claveDocumento('CC', '99.901.000-01');
    expect(clave).toHaveLength(16);
    expect(bytesAHex(clave)).toBe('d4d543f3ecc2e19418c1171a829a3eb2');
  });
});

// ── num_hash: con lo que se consulta el Bloom ───────────────────────────────

describe('numHash', () => {
  test('coincide con num_hash del backend', () => {
    expect(numHash('1234567890')).toBe(
      'c775e7b757ede630cd0aa1113bd102661ab38829ca52a6422ab782862f268646',
    );
    expect(numHash('28683981')).toBe(
      '77f9732cb43f496a96e2f8cd1a0a62d6b0990d17b81809f8f8d4d59a59fda215',
    );
    expect(numHash('93021801')).toBe(
      'dc36b9800423befe790873526d432aa209ad986136b7c92b73676f946d776131',
    );
  });

  test('normaliza igual que el backend', () => {
    const base = numHash('1234567890');
    expect(numHash(' 1234567890 ')).toBe(base);
    expect(numHash('1.234.567.890')).toBe(base);
  });

  test('IGNORA el tipo — es la diferencia con docHash', () => {
    // La trampa central: consultar el Bloom con docHash no devuelve "algunos
    // fallos", no encuentra absolutamente nada y sin avisar.
    expect(numHash('28683981')).not.toBe(docHash('CC', '28683981'));
  });
});

// ── Bloom: la derivación tiene que ser la de Python ─────────────────────────

describe('bloom', () => {
  /**
   * ⚠️ VECTOR COMPARTIDO con test_bloom.py::test_vector_fijo_de_indices.
   * Los índices salieron de ejecutar el Python. Si estos dos lados se separan,
   * el filtro no falla: responde basura.
   */
  test('vector fijo de índices', () => {
    const m = 1024;
    const k = 4;
    const esperados = [951, 488, 25, 586];

    // Se enciende exactamente lo que Python calculó...
    const bits = new Uint8Array(m / 8);
    esperados.forEach((idx) => {
      bits[idx >> 3] |= 1 << (idx & 7);
    });

    // ...y esta implementación debe reconocerlo.
    expect(contiene(bits, m, k, numHash('1234567890'))).toBe(true);
  });

  test('vector fijo con los parámetros REALES de producción', () => {
    // m y k del padrón que se genera con los 12.677.172 del universo. Los
    // índices son grandes (>2^25) y la progresión h1+i*h2 supera 2^32: si el
    // cálculo usara operadores de bits truncaría a 32 bits y daría otros.
    const m = 182267152;
    const k = 10;
    const esperados = [
      65584279, 82655816, 99727353, 116798890, 133870427,
      150941964, 168013501, 2817886, 19889423, 36960960,
    ];

    const bits = new Uint8Array(m / 8);
    esperados.forEach((idx) => {
      bits[idx >> 3] |= 1 << (idx & 7);
    });

    expect(contiene(bits, m, k, numHash('1234567890'))).toBe(true);
  });

  test('sin falsos negativos: lo que se agregó siempre se encuentra', () => {
    const m = 8192;
    const k = 5;
    const bits = new Uint8Array(m / 8);
    const docs = ['28683981', '93021801', '1075263069', '1032256897'];

    // Se construye con `indicesDe`, la MISMA derivación que usa la consulta.
    docs.forEach((d) => {
      indicesDe(numHash(d), m, k).forEach((idx) => {
        bits[idx >> 3] |= 1 << (idx & 7);
      });
    });

    docs.forEach((d) => {
      expect(contiene(bits, m, k, numHash(d))).toBe(true);
    });
  });

  test('ningún índice sale negativo, ni con el bit alto de h2 encendido', () => {
    // Regresión del bug del signo: `(x >>> 0) | 1` devuelve el valor a int32 y
    // produce índices negativos para la mitad de los documentos. El 28683981 es
    // uno de ellos —daba [4908, 7319, -6654, -4243, -1832]— y es además una de
    // las cédulas reales que motivaron todo esto.
    const casos = ['28683981', '1075263069', '1032256897', '1234567890'];

    casos.forEach((d) => {
      indicesDe(numHash(d), 182267152, 10).forEach((idx) => {
        expect(idx).toBeGreaterThanOrEqual(0);
        expect(idx).toBeLessThan(182267152);
      });
    });
  });

  test('la derivación coincide con Python para un h2 de bit alto encendido', () => {
    // Valores calculados con el backend para 28683981, cuyo h2 sin corregir
    // salía negativo en JS. Fija el arreglo contra la implementación real.
    expect(indicesDe(numHash('28683981'), 8192, 5)).toEqual([
      4908, 7319, 1538, 3949, 6360,
    ]);
  });

  test('un filtro vacío responde que no a todo', () => {
    const bits = new Uint8Array(1024);
    expect(contiene(bits, 8192, 5, numHash('28683981'))).toBe(false);
  });

  describe('contieneCon — lectura byte a byte desde archivo', () => {
    const m = 8192;
    const k = 5;

    function filtroCon(docs: string[]): Uint8Array {
      const bits = new Uint8Array(m / 8);
      docs.forEach((d) => {
        indicesDe(numHash(d), m, k).forEach((idx) => {
          bits[idx >> 3] |= 1 << (idx & 7);
        });
      });
      return bits;
    }

    test('da el mismo resultado que leer el buffer entero', () => {
      const bits = filtroCon(['28683981', '93021801']);

      expect(contieneCon((i) => bits[i] ?? 0, m, k, numHash('28683981'))).toBe(true);
      expect(contieneCon((i) => bits[i] ?? 0, m, k, numHash('93021801'))).toBe(true);
      expect(contieneCon((i) => bits[i] ?? 0, m, k, numHash('99999999'))).toBe(false);
    });

    test('lee solo k bytes, no el filtro entero', () => {
      // Es la razón de existir de esta variante: en el dispositivo el filtro son
      // 22,7 MB y traerlo a memoria en cada búsqueda no tiene sentido.
      const bits = filtroCon(['28683981']);
      const leidos: number[] = [];

      contieneCon(
        (i) => {
          leidos.push(i);
          return bits[i] ?? 0;
        },
        m,
        k,
        numHash('28683981'),
      );

      expect(leidos.length).toBeLessThanOrEqual(k);
    });

    test('corta en el primer bit apagado sin leer de más', () => {
      const vacio = new Uint8Array(m / 8);
      const leidos: number[] = [];

      const r = contieneCon(
        (i) => {
          leidos.push(i);
          return vacio[i] ?? 0;
        },
        m,
        k,
        numHash('28683981'),
      );

      expect(r).toBe(false);
      expect(leidos).toHaveLength(1);
    });

    test('un lector que devuelve 0 fuera de rango responde "no está", no rompe', () => {
      // El contrato: `undefined & 1` es 0 y daría el mismo false, pero en
      // silencio y sin que nadie sepa que se leyó fuera del archivo.
      expect(contieneCon(() => 0, m, k, numHash('28683981'))).toBe(false);
    });
  });

  describe('esUsable', () => {
    const params = { formato: 1, m: 8192, k: 5, n: 100, falsos_positivos: 0.001 };

    test('acepta un filtro coherente', () => {
      expect(esUsable(new Uint8Array(1024), params)).toBe(true);
    });

    test('rechaza un blob más corto de lo que declara m', () => {
      // La comprobación que más importa: con un blob corto, bits[i] es
      // undefined, y `undefined & 1` es 0 — el filtro respondería "no está"
      // para todo el mundo, en silencio.
      expect(esUsable(new Uint8Array(512), params)).toBe(false);
    });

    test('rechaza un formato que no entiende', () => {
      expect(esUsable(new Uint8Array(1024), { ...params, formato: 2 })).toBe(false);
    });

    test('rechaza filtro ausente', () => {
      expect(esUsable(null, params)).toBe(false);
      expect(esUsable(new Uint8Array(1024), null)).toBe(false);
    });
  });
});
