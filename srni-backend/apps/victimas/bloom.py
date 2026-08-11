"""
Filtro de Bloom del UNIVERSO de víctimas, para el padrón offline.

──────────────────────────────────────────────────────────────────────────────
QUÉ PROBLEMA RESUELVE
──────────────────────────────────────────────────────────────────────────────
El padrón descargable lleva a las personas **con ficha** (4,55 M documentos
distintos): nombre, banderas y `cons_persona`. Pero el universo del RUV tiene
**12,68 M** personas únicas, y las **8.123.873** que solo están ahí —medido el
11-ago-2026— hoy no viajan al dispositivo. En campo y sin señal, buscar a una de
ellas responde "no encontrada", que es falso: son víctimas reconocidas que
nunca fueron entrevistadas. De 68 cédulas traídas del territorio, 33 estaban en
ese caso.

Llevarlas con nombre y datos costaría ~190 MB más. No hace falta: **en un alta
manual la persona está enfrente del encuestador**, que le pregunta el nombre. Lo
único que el dispositivo tiene que responder es *"¿esta persona está en el
universo, procedo a caracterizarla?"* — una pregunta de sí/no.

Un filtro de Bloom contesta exactamente eso en **22,7 MB para los 12,68 M**, en
vez de los ~190 MB de la tabla equivalente.

──────────────────────────────────────────────────────────────────────────────
EL PRECIO, DICHO CLARO
──────────────────────────────────────────────────────────────────────────────
Un Bloom **nunca dice "no está" si está** (no hay falsos negativos: si la
persona es víctima, el filtro siempre la reconoce). Lo que sí puede es decir
"está" cuando no: con `P_FALSO_POSITIVO = 0,001`, **1 de cada 1.000** consultas
sobre alguien ajeno al universo responde que sí.

Esa consecuencia hay que sostenerla en producto, no esconderla: la APK debe
tratar un acierto del Bloom como **candidato a alta manual**, avisando que se
confirma al sincronizar — igual que ya hace con `clase_colision = 'AMBIGUO'`.
Nunca como una identificación. El backend revalida contra la base al recibir.

──────────────────────────────────────────────────────────────────────────────
⚠️ ESTE FILTRO USA EL HASH **SIN TIPO** — Y LA TABLA `padron` NO
──────────────────────────────────────────────────────────────────────────────
En el mismo archivo conviven dos hashes distintos, y confundirlos hace que nada
coincida:

    tabla `padron`   → doc_hash(tipo, numero)  = sha256("cc|1234")
    Bloom del universo → num_hash(numero)      = sha256("1234")

Es deliberado. `PersonaUniverso.tipo_documento` viene **sin homologar** desde la
fuente, y el cruce entre universo y padrón está definido por documento sin tipo
(ver `PersonaUniverso.numero_documento_hash_sin_tipo`, y la medición de que
`CONS_PERSONA` del universo no es `cons_persona` del legacy). Un Bloom armado
con el tipo incluido fallaría justo en las 1,13 M de personas a las que la
fuente no les registró tipo.

──────────────────────────────────────────────────────────────────────────────
CÓMO SE DERIVAN LOS k ÍNDICES (el cliente DEBE replicar esto bit a bit)
──────────────────────────────────────────────────────────────────────────────
Doble hashing de Kirsch-Mitzenmacher: en vez de calcular k hashes
independientes, se sacan dos del mismo SHA-256 y se combinan. Da la misma tasa
de error y cuesta un solo hash por consulta.

    sha = sha256(numero_normalizado)          # el de `num_hash`, en bytes
    h1  = uint32 big-endian de sha[0:4]
    h2  = uint32 big-endian de sha[4:8]  |  1     # forzado IMPAR
    idx_i = (h1 + i * h2) mod m                   para i en 0..k-1

    bit puesto  →  buf[idx >> 3] |= 1 << (idx & 7)     # bit menos significativo primero

`h2` se fuerza impar por una razón concreta: si `h2` y `m` comparten factores,
la progresión `h1 + i*h2` recorre solo una parte del filtro y la tasa de falsos
positivos real se dispara por encima de la teórica. Con `h2` impar el paso es
coprimo con cualquier `m` par.

Big-endian y no little-endian porque del otro lado es JavaScript, donde
`DataView.getUint32(off)` ya es big-endian por defecto: menos superficie para
que las dos implementaciones se separen sin que nadie lo note.
"""
from __future__ import annotations

import hashlib
import math

#: Tasa de falsos positivos objetivo. 0,001 = 1 de cada 1.000.
#: Bajarla a 0,0001 multiplicaría el archivo por 1,33 (22,7 → 30,3 MB) y es la
#: perilla a mover si en campo el ruido de candidatos falsos molesta.
P_FALSO_POSITIVO = 0.001

#: Versión del formato del filtro. Viaja en el manifiesto: si cambia la manera de
#: derivar los índices, un cliente viejo debe rechazarlo en vez de consultarlo mal
#: —un Bloom mal leído no falla, simplemente responde basura—.
BLOOM_FORMATO = 1


def parametros(n: int, p: float = P_FALSO_POSITIVO) -> tuple[int, int]:
    """
    `(m, k)` óptimos para `n` elementos y tasa de error `p`.

        m = -n·ln(p) / (ln 2)²        bits del filtro
        k = (m/n)·ln 2                funciones hash

    Con n = 12.677.172 y p = 0,001 da m ≈ 182,25 Mbits (22,78 MB) y k = 10.

    `m` se redondea hacia arriba al byte para que el buffer no tenga bits
    colgando fuera del último byte, que es justo el tipo de detalle en el que
    dos implementaciones —Python y JavaScript— se desalinean sin avisar.
    """
    if n <= 0:
        raise ValueError('El filtro necesita al menos un elemento.')
    if not 0 < p < 1:
        raise ValueError('La tasa de falsos positivos debe estar entre 0 y 1.')

    m = math.ceil(-n * math.log(p) / (math.log(2) ** 2))
    m = ((m + 7) // 8) * 8                      # múltiplo de 8 bits
    k = max(1, round((m / n) * math.log(2)))
    return m, k


def _indices(sha: bytes, m: int, k: int):
    """Los k índices de bit para un SHA-256 ya calculado. Ver el docstring."""
    h1 = int.from_bytes(sha[0:4], 'big')
    h2 = int.from_bytes(sha[4:8], 'big') | 1    # impar: ver arriba
    for i in range(k):
        yield (h1 + i * h2) % m


class ConstructorBloom:
    """
    Construye el filtro en memoria y lo entrega como `bytes`.

    Los 22,7 MB del buffer se reservan de una vez y no crecen: `bytearray` de
    tamaño fijo, un bit por posición. Es la única estructura que este proceso
    mantiene completa en RAM, y por eso el resto del generador sigue siendo
    streaming — nunca hay 12,68 M de objetos Python vivos, solo el buffer.
    """

    def __init__(self, n_estimado: int, p: float = P_FALSO_POSITIVO):
        self.m, self.k = parametros(n_estimado, p)
        self.p = p
        self.buf = bytearray(self.m // 8)
        self.n = 0

    def agregar(self, hash_hex: str) -> None:
        """Marca un documento. `hash_hex` es la salida de `num_hash` (SHA-256 hex)."""
        sha = bytes.fromhex(hash_hex)
        for idx in _indices(sha, self.m, self.k):
            self.buf[idx >> 3] |= 1 << (idx & 7)
        self.n += 1

    def contiene(self, hash_hex: str) -> bool:
        """`False` es definitivo; `True` es 'probablemente' (ver P_FALSO_POSITIVO)."""
        sha = bytes.fromhex(hash_hex)
        return all(
            self.buf[idx >> 3] & (1 << (idx & 7))
            for idx in _indices(sha, self.m, self.k)
        )

    @property
    def bits_encendidos(self) -> int:
        """Cuántos bits quedaron en 1. Sirve para verificar el llenado real."""
        return sum(bin(b).count('1') for b in self.buf)

    def falsos_positivos_reales(self) -> float:
        """
        Tasa de error **medida sobre el filtro construido**, no la teórica.

        Se calcula desde la fracción de bits encendidos: `(bits_en_1 / m) ** k`.
        Vale la pena reportarla: si la estimación de `n` se quedó corta, el
        filtro se llena de más y esta cifra lo delata, mientras que la `p`
        teórica seguiría diciendo 0,001 tan tranquila.
        """
        return (self.bits_encendidos / self.m) ** self.k

    def to_bytes(self) -> bytes:
        return bytes(self.buf)


def contiene(buf: bytes, m: int, k: int, hash_hex: str) -> bool:
    """
    Consulta suelta contra un filtro ya serializado — la misma que hará la APK.

    Existe para poder verificar en un test que un buffer leído desde el archivo
    responde igual que el constructor que lo creó.
    """
    sha = bytes.fromhex(hash_hex)
    return all(buf[idx >> 3] & (1 << (idx & 7)) for idx in _indices(sha, m, k))


def hash_para_bloom(numero_documento: str) -> str:
    """
    El hash con el que se consulta este filtro: **solo el número, sin tipo**.

    Envoltura fina sobre `num_hash` que existe para dejar el contrato en un solo
    lugar. Si alguien pasa por aquí buscando "cómo consulto el Bloom", la
    respuesta no admite improvisación: es esta función, no `doc_hash`.
    """
    from apps.victimas.repository.base import num_hash
    return num_hash(numero_documento)
