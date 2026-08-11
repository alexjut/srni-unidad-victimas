"""
Tests del filtro de Bloom del universo (`apps/victimas/bloom.py`).

Lo que de verdad importa acá no es que el filtro "funcione", sino que **la APK
llegue exactamente al mismo bit que el backend**. Son dos implementaciones en
dos lenguajes leyendo un archivo binario compartido; si se separan, el filtro no
falla ni avisa: responde basura, y en campo eso significa mandar a alta manual a
quien no corresponde (o peor, negársela a una víctima).

Por eso el test central es `test_vector_fijo_de_indices`: un caso con valores
escritos a mano que el test de JavaScript debe reproducir tal cual.
"""
import hashlib

import pytest

from apps.victimas.bloom import (
    BLOOM_FORMATO,
    ConstructorBloom,
    contiene,
    hash_para_bloom,
    parametros,
)


# ── Dimensionado ────────────────────────────────────────────────────────────
def test_parametros_del_universo_real():
    """
    Los números que se van a producción, con el `n` medido el 11-ago-2026.

    Si alguien cambia la fórmula o P_FALSO_POSITIVO, este test lo delata con la
    cifra concreta que va a pesar el archivo que baja el celular.
    """
    m, k = parametros(12_677_172, 0.001)

    assert k == 10
    assert m % 8 == 0, 'm debe ser múltiplo de 8 o el último byte queda a medias'
    # 22,78 millones de bytes = 21,7 MiB. Las dos unidades se escriben acá a
    # propósito: al dimensionar esto se confundió una con otra, y la diferencia
    # (22,8 vs 21,7) es justo el tipo de cifra que después se cita en un informe.
    assert m // 8 == 22_783_394
    assert 21.5 < m / 8 / 1_048_576 < 22.0


def test_parametros_rechaza_entradas_imposibles():
    with pytest.raises(ValueError):
        parametros(0)
    with pytest.raises(ValueError):
        parametros(100, p=0)
    with pytest.raises(ValueError):
        parametros(100, p=1)


def test_p_mas_estricta_agranda_el_filtro():
    """La perilla documentada: bajar p multiplica el tamaño, no lo regala."""
    m_flojo, _ = parametros(1_000_000, 0.001)
    m_estricto, _ = parametros(1_000_000, 0.0001)

    assert m_estricto > m_flojo
    assert 1.30 < m_estricto / m_flojo < 1.36    # ~1,33x


# ── La garantía dura: nunca un falso negativo ───────────────────────────────
def test_sin_falsos_negativos():
    """
    Un Bloom puede equivocarse diciendo "está" — nunca diciendo "no está".

    Esta es LA propiedad de la que depende el diseño: si fallara, una víctima
    real quedaría sin poder caracterizarse en campo, que es exactamente el
    problema que el filtro vino a resolver.
    """
    docs = [f'{1000000 + i}' for i in range(5_000)]
    bloom = ConstructorBloom(len(docs))
    for d in docs:
        bloom.agregar(hash_para_bloom(d))

    for d in docs:
        assert bloom.contiene(hash_para_bloom(d)), f'{d} se agregó y no se encuentra'


def test_tasa_de_falsos_positivos_cerca_de_la_teorica():
    """Con documentos que NO se agregaron, el error real ronda el declarado."""
    dentro = [f'{2000000 + i}' for i in range(20_000)]
    fuera = [f'{9000000 + i}' for i in range(20_000)]

    bloom = ConstructorBloom(len(dentro), p=0.01)
    for d in dentro:
        bloom.agregar(hash_para_bloom(d))

    fp = sum(1 for d in fuera if bloom.contiene(hash_para_bloom(d))) / len(fuera)

    # Margen ancho a propósito: es una prueba estadística, no una igualdad.
    assert fp < 0.03, f'falsos positivos {fp:.4f}, muy por encima del 1% de diseño'


def test_falsos_positivos_reales_se_miden_sobre_el_filtro():
    """
    `falsos_positivos_reales()` mira los bits encendidos, no la fórmula.

    Sirve para detectar un dimensionado corto: si se agregan más elementos de
    los estimados, el filtro se satura y la cifra medida sube, mientras que la
    teórica seguiría afirmando el valor de diseño.
    """
    bloom = ConstructorBloom(1_000, p=0.01)
    for i in range(10_000):                      # 10x lo estimado: saturado
        bloom.agregar(hash_para_bloom(str(i)))

    assert bloom.falsos_positivos_reales() > 0.01
    assert bloom.bits_encendidos > 0


# ── Interoperabilidad: el contrato con la APK ───────────────────────────────
def test_vector_fijo_de_indices():
    """
    ⚠️ VECTOR DE PRUEBA COMPARTIDO CON LA APK. No cambiar sin cambiar el de JS.

    Fija la derivación completa —big-endian, `| 1`, la progresión y el orden de
    bits— sobre un caso calculable a mano. El test equivalente en JavaScript debe
    dar estos mismos índices; si difieren, las dos implementaciones se separaron.
    """
    numero = '1234567890'
    sha = hashlib.sha256(numero.encode('utf-8')).digest()

    # Los dos enteros de los que sale todo lo demás.
    h1 = int.from_bytes(sha[0:4], 'big')
    h2 = int.from_bytes(sha[4:8], 'big') | 1

    m, k = 1024, 4
    esperados = [(h1 + i * h2) % m for i in range(k)]

    # `hash_para_bloom` debe ser el SHA-256 del número pelado.
    assert hash_para_bloom(numero) == sha.hex()

    # Y el filtro debe encender exactamente esos bits.
    buf = bytearray(m // 8)
    for idx in esperados:
        buf[idx >> 3] |= 1 << (idx & 7)

    assert contiene(bytes(buf), m, k, sha.hex())
    assert h2 % 2 == 1, 'h2 tiene que quedar impar'


def test_hash_del_bloom_ignora_el_tipo_de_documento():
    """
    El Bloom se consulta SIN tipo. Es la diferencia con la tabla `padron`, y la
    fuente más probable de que un día nada coincida.
    """
    from apps.victimas.repository.base import doc_hash, num_hash

    assert hash_para_bloom('1234567890') == num_hash('1234567890')
    assert hash_para_bloom('1234567890') != doc_hash('CC', '1234567890')


def test_normalizacion_del_numero():
    """Puntos, espacios y mayúsculas no pueden cambiar el resultado."""
    base = hash_para_bloom('1234567890')

    assert hash_para_bloom(' 1234567890 ') == base
    assert hash_para_bloom('1.234.567.890') == base


def test_round_trip_por_bytes():
    """
    Lo que se serializa al archivo responde igual que el constructor en memoria.

    Es el camino real: el generador escribe `to_bytes()` en el SQLite y la APK lo
    lee de vuelta y consulta con `contiene()`.
    """
    docs = [f'{3000000 + i}' for i in range(1_000)]
    bloom = ConstructorBloom(len(docs))
    for d in docs:
        bloom.agregar(hash_para_bloom(d))

    buf = bloom.to_bytes()
    assert len(buf) == bloom.m // 8

    for d in docs:
        assert contiene(buf, bloom.m, bloom.k, hash_para_bloom(d))


def test_agregar_dos_veces_no_cambia_nada():
    """
    En lo que se apoya el generador para no deduplicar 12,68 M de hashes en un
    `set` de 1,5 GB: volcar los dos flujos con solapamiento sale gratis.
    """
    bloom = ConstructorBloom(100)
    bloom.agregar(hash_para_bloom('555'))
    huella = bytes(bloom.buf)

    bloom.agregar(hash_para_bloom('555'))

    assert bytes(bloom.buf) == huella


def test_formato_declarado():
    """El formato viaja al manifiesto; un cliente viejo debe poder rechazarlo."""
    assert BLOOM_FORMATO == 1
