"""
Reconocer cuándo dos filas del padrón son la misma persona.

Este módulo tiene una sola responsabilidad: dado un puñado de registros que
comparten número de documento, decir **cuántas personas distintas** hay ahí y
cuál es la fila que mejor la representa. No escribe nada; decide.

─── Por qué determinístico y no un modelo ───────────────────────────────────
El oficio (record linkage) ofrece dos caminos: reglas determinísticas y
puntajes probabilísticos tipo Fellegi-Sunter. Acá se eligen reglas, por tres
razones concretas de este proyecto:

1. **Hay que poder explicar cada decisión.** Si a una víctima se le niega o se le
   asigna una caracterización, la respuesta no puede ser "el modelo dio 0,87".
   Con reglas se responde "mismo documento, mismos apellidos y misma fecha de
   nacimiento".
2. **El emparejamiento acá es fácil.** Los registros ya comparten el
   identificador fuerte (documento); lo único que se decide es si el nombre y la
   fecha describen a la misma persona. Medido sobre producción, el 92 % de los
   grupos son coincidencia EXACTA de nombre y fecha: no hay franja gris que
   justifique un modelo.
3. **Corre sobre millones de filas** en un servidor compartido y sin GPU.

Si algún día aparece la franja gris —fuentes con nombres libres, sin fecha—, el
paso siguiente es puntaje + umbral + revisión humana de lo dudoso. La forma del
resultado (cuántas personas, cuál es la preferida) no cambia.

─── Qué NO decide este módulo ───────────────────────────────────────────────
No fusiona ni borra: devuelve grupos. Quien lo llama decide qué hacer, y la
`Victima` original nunca se toca (*link, don't merge*).
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field


# Documentos que NO identifican a nadie: valores de relleno que la fuente usa
# cuando no hay documento. Medidos en producción el 2-ago: `99` aparece 4.297
# veces con 3.780 nombres distintos; `0`, 1.194 veces con 971 nombres.
#
# La práctica establecida en los índices maestros de personas (EMPI) es tener una
# "null value list": identificadores conocidos que se excluyen del emparejamiento
# en vez de tratarlos como llave. Sin esto, `99` empareja a 4.297 personas entre
# sí y la búsqueda devuelve cualquiera de ellas.
#
# La lista es de valores EXACTOS ya normalizados (sin puntos ni guiones). Se
# amplía con lo que mida `clasificar_colisiones`, no a ojo.
DOCUMENTOS_NO_IDENTIFICANTES = frozenset({
    '0', '00', '000', '0000', '00000', '000000', '0000000', '00000000',
    '1', '11', '111', '1111', '11111', '111111', '1111111', '11111111',
    '99', '999', '9999', '99999', '999999', '9999999', '99999999',
    '999999999', '9999999999',
    '12345', '123456', '1234567', '12345678', '123456789', '1234567890',
})

# Cuántos nombres distintos bastan para declarar que un documento es de relleno
# aunque no esté en la lista de arriba. Una persona real puede aparecer con dos o
# tres grafías de su nombre; veinte nombres distintos bajo el mismo número no es
# una persona mal escrita, es un campo que se usó como comodín.
UMBRAL_NOMBRES_COMODIN = 20


def normalizar_nombre(*partes: str | None) -> str:
    """
    Forma canónica de un nombre para compararlo: mayúsculas, sin tildes, sin
    puntuación, sin espacios de más.

    **La Ñ se pliega a N a propósito.** MUÑOZ y MUNOZ tienen que comparar igual:
    los sistemas de los que viene este padrón pierden la ñ de forma inconsistente
    —la misma persona aparece de las dos formas— y separarlas produciría un
    "ambiguo" falso que le hace perder tiempo al encuestador. El riesgo inverso
    es despreciable: para que esto uniera a dos personas distintas harían falta
    dos personas con el mismo documento, la misma fecha de nacimiento y apellidos
    que solo difieren en la ñ.

    No intenta ser inteligente —no reordena apellidos ni resuelve apodos—: eso
    daría uniones que después nadie puede explicar.
    """
    crudo = ' '.join(p for p in partes if p)
    sin_tildes = ''.join(
        c for c in unicodedata.normalize('NFKD', crudo.upper())
        if not unicodedata.combining(c)
    )
    return ' '.join(re.sub(r'[^A-Z ]', ' ', sin_tildes).split())


def documento_no_identificante(numero: str | None) -> bool:
    """
    Si el número es un valor de relleno y no debe usarse como identidad.

    Además de la lista, un número de menos de 4 dígitos no es un documento
    colombiano válido —ni cédula, ni tarjeta de identidad, ni registro civil—, así
    que tampoco identifica.
    """
    if not numero:
        return True
    limpio = re.sub(r'[^0-9A-Za-z]', '', str(numero)).lstrip('0') or '0'
    normalizado = re.sub(r'[^0-9A-Za-z]', '', str(numero))
    if normalizado in DOCUMENTOS_NO_IDENTIFICANTES:
        return True
    # Solo dígitos y demasiado corto para ser un documento real.
    if normalizado.isdigit() and len(limpio) < 4:
        return True
    return False


@dataclass
class Persona:
    """Una persona reconocida dentro de un grupo, y las filas que la sustentan."""
    nombre: str
    fecha_nacimiento: object
    apellidos: str
    filas: list = field(default_factory=list)


@dataclass
class Veredicto:
    """
    Qué hay detrás de un documento repetido.

    `clase` usa los mismos valores que `ColisionDocumento.CLASE`.
    """
    clase: str
    personas: list[Persona]
    preferida: object | None

    @property
    def n_personas(self) -> int:
        return len(self.personas)


def _completitud(v) -> int:
    """
    Cuántos campos útiles trae la fila. Decide cuál se muestra cuando varias
    describen a la misma persona — la regla de *survivorship* más simple que
    existe y la que no puede sorprender a nadie: gana la que más información
    tiene, y a igualdad, la caracterizada más recientemente.

    NO decide identidad: solo el orden.
    """
    campos = (
        v.primer_nombre, v.segundo_nombre, v.primer_apellido, v.segundo_apellido,
        v.fecha_nacimiento, v.genero, v.pertenencia_etnica, v.tipo_discapacidad,
        v.municipio_residencia_id, v.cons_persona, v.estado_ruv,
        v.fecha_ult_caracterizacion,
    )
    return sum(1 for c in campos if c not in (None, '', 0))


def _id_estable(v) -> str:
    """
    Identificador de la fila como texto, para ordenar de forma reproducible.

    Los dobles de los tests no tienen `id`; devolver '' los deja en su orden de
    entrada, que en `sorted` (estable) es exactamente lo que se quiere.
    """
    return str(getattr(v, 'id', '') or '')


def _orden_survivorship(v) -> tuple:
    """
    Orden TOTAL para elegir la fila que representa a la persona: completitud,
    luego recencia de la caracterización, luego id.

    Los tres componentes hacen falta. Con solo la completitud, `max()` rompe los
    empates por posición en la lista —y esa posición la decide el plan de
    ejecución de PostgreSQL, que puede cambiar entre corridas—: dos generaciones
    del padrón publicarían filas distintas para la misma persona sin que nadie
    haya cambiado nada. El `id` al final garantiza que el desempate sea siempre
    el mismo.
    """
    f = v.fecha_ult_caracterizacion
    if hasattr(f, 'timestamp'):
        recencia = f.timestamp()
    elif hasattr(f, 'toordinal'):
        recencia = float(f.toordinal())
    else:
        recencia = 0.0
    return (_completitud(v), recencia, _id_estable(v))


def _clave_apellidos(v) -> str:
    return normalizar_nombre(v.primer_apellido, v.segundo_apellido)


def _clave_completa(v) -> tuple:
    return (
        normalizar_nombre(v.primer_nombre, v.segundo_nombre,
                          v.primer_apellido, v.segundo_apellido),
        v.fecha_nacimiento,
    )


def clasificar_grupo(filas: list, numero_documento: str | None = None) -> Veredicto:
    """
    El corazón del asunto: cuántas personas hay entre estas filas.

    Tres pasos, en orden de certeza decreciente:

    1. **¿El documento identifica?** Si es un valor de relleno, no hay nada que
       agrupar: las filas no tienen por qué ser la misma persona y el documento no
       sirve para encontrarlas. → `NO_IDENTIFICANTE`.
    2. **Coincidencia exacta** de nombre normalizado + fecha de nacimiento. Es el
       92 % de los casos y no admite discusión: misma persona.
    3. **Variantes**: si dos bloques del paso 2 comparten apellidos y fecha de
       nacimiento, es la misma persona con el nombre mal escrito. Se unen y el
       grupo queda marcado `VARIANTE_NOMBRE` para que quede rastro de que hubo
       una decisión, no una coincidencia.

    Lo que sobrevive a los tres pasos son personas distintas: `AMBIGUO`, y ahí
    **no se elige** —`preferida` queda en None y decide quien tiene a la persona
    enfrente—.
    """
    if not filas:
        return Veredicto(clase='NO_IDENTIFICANTE', personas=[], preferida=None)

    # Paso 1 — el documento no identifica.
    if documento_no_identificante(numero_documento):
        return Veredicto(clase='NO_IDENTIFICANTE', personas=[], preferida=None)

    # Paso 2 — coincidencia exacta.
    #
    # Se recorre en orden de `id` y no en el que devuelva PostgreSQL: sin eso, el
    # plan de ejecución decide qué fila se guarda primero y dos corridas del mismo
    # comando pueden dar veredictos distintos sobre los mismos datos.
    bloques: dict[tuple, Persona] = {}
    for i, v in enumerate(sorted(filas, key=_id_estable)):
        clave = _clave_completa(v)
        # Sin nombre no se puede afirmar que dos filas son la misma persona: se
        # dejan separadas y el grupo termina en AMBIGUO. Hay 153 víctimas sin
        # primer_nombre en el padrón; unirlas por "las dos están vacías" sería
        # fabricar una identidad a partir de la ausencia de datos.
        if not clave[0]:
            clave = ('#sin-nombre', i)
        p = bloques.get(clave)
        if p is None:
            p = Persona(nombre=clave[0] if isinstance(clave[0], str) else '',
                        fecha_nacimiento=_clave_completa(v)[1],
                        apellidos=_clave_apellidos(v))
            bloques[clave] = p
        p.filas.append(v)

    # Un documento con demasiados nombres distintos es un comodín no declarado.
    if len(bloques) >= UMBRAL_NOMBRES_COMODIN:
        return Veredicto(clase='NO_IDENTIFICANTE', personas=[], preferida=None)

    hubo_variante = False
    if len(bloques) > 1:
        # Paso 3 — unir variantes por (apellidos, fecha de nacimiento).
        #
        # Se exige que la fecha coincida además de los apellidos: dos hermanos
        # comparten apellidos y podrían compartir un documento mal digitado, y
        # unirlos sería fabricar una persona que no existe. Con la fecha igual, la
        # explicación más simple es el typo en el nombre.
        #
        # ⚠️ Un bloque SIN apellidos o SIN fecha no puede unirse ni servir de
        # llave, y va con una clave propia. La versión anterior lo metía igual en
        # el diccionario bajo la llave ('', ''): el segundo bloque sin apellidos
        # **sobrescribía** al primero y esa persona desaparecía del veredicto —el
        # grupo quedaba marcado como "una sola persona" y el padrón offline
        # borraba sus filas—. Es el borrado silencioso que este módulo existe para
        # impedir, entrando por la puerta de atrás. La fuente escribe '' cuando
        # Oracle trae NULL, así que el caso es corriente, no teórico.
        unidos: dict[tuple, Persona] = {}
        for clave, p in bloques.items():
            if not p.apellidos or not p.fecha_nacimiento:
                unidos[('#solo', clave)] = p
                continue
            k = ('#apellidos', p.apellidos, p.fecha_nacimiento)
            existente = unidos.get(k)
            if existente is not None:
                existente.filas.extend(p.filas)
                hubo_variante = True
            else:
                unidos[k] = p
        bloques = unidos

    personas = list(bloques.values())

    if len(personas) == 1:
        preferida = max(personas[0].filas, key=_orden_survivorship)
        clase = 'VARIANTE_NOMBRE' if hubo_variante else 'DUPLICADO_FUENTE'
        return Veredicto(clase=clase, personas=personas, preferida=preferida)

    # Personas distintas: acá no elegimos.
    return Veredicto(clase='AMBIGUO', personas=personas, preferida=None)
