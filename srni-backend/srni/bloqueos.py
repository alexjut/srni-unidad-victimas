"""
Exclusión mutua entre corridas de una misma tarea periódica.

Por qué existe
--------------
Celery beat NO garantiza que una tarea haya terminado antes de volver a
dispararla: el reloj dispara, punto. Con la recarga del padrón eso es un problema
real y no teórico — la carga idempotente hace `update_or_create` fila a fila sobre
5,9 millones de personas (~51 filas/s medidos), así que una corrida puede durar
más de un día. Sin bloqueo, dos corridas simultáneas significan:

* dos lecturas completas del Oracle de producción a la vez, compitiendo por el
  mismo `GIC_PERSONA` que usa la aplicación legacy en horario laboral;
* dos procesos haciendo `update_or_create` sobre las mismas filas de PostgreSQL,
  o sea contención de escritura y el doble de tiempo para ambas;
* un `generar_padron` publicando el SQLite mientras el otro todavía está
  escribiendo la tabla de origen.

El bloqueo no es solo contra beat. También protege del disparo manual (alguien
lanza la tarea desde el shell sin saber que la mensual está corriendo) y de la
re-entrega del broker.

Por qué la caché de Django y no un lock propio en Redis
--------------------------------------------------------
`cache.add()` es exactamente `SET NX EX` en django-redis: atómico, con expiración
en la misma operación. Escribir un cliente de Redis aparte sería reimplementar eso
con otra configuración de conexión que mantener.

Fail-CLOSED, y es deliberado
-----------------------------
En producción la caché está con `IGNORE_EXCEPTIONS: True` (ver settings/production):
si Redis no responde, `add()` devuelve un valor falsy en vez de lanzar. Aquí eso se
interpreta como «no se pudo adquirir» → la tarea NO corre.

Es la decisión correcta para este caso: si no puedo garantizar que soy el único,
prefiero saltarme la corrida mensual —que se recupera sola el mes siguiente, o a
mano— antes que arriesgar dos cargas simultáneas contra el Oracle de la UARIV. Y
en la práctica no se pierde nada: el broker de Celery TAMBIÉN es Redis, así que si
Redis está caído la tarea ni siquiera habría llegado al worker.
"""
import logging
import os
import socket
import uuid
from contextlib import contextmanager
from dataclasses import dataclass

from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)

PREFIJO = "srni:bloqueo:"


@dataclass
class Bloqueo:
    """Lo que ve el cuerpo del `with`: si se adquirió y, si no, quién lo tiene."""

    nombre: str
    adquirido: bool
    token: str = ""
    # Etiqueta del dueño actual cuando NO se adquirió. Sin esto, un "saltado por
    # solapamiento" en el log no dice si el que está corriendo lleva dos minutos o
    # dos días — que es justo lo que el operador necesita para decidir si intervenir.
    dueño_actual: str = ""


def _etiqueta() -> str:
    """Quién soy: contenedor + PID + hora de arranque. Va dentro del valor del lock."""
    return (f"{socket.gethostname()}/pid{os.getpid()} "
            f"desde {timezone.localtime():%Y-%m-%d %H:%M:%S}")


@contextmanager
def bloqueo_exclusivo(nombre: str, *, ttl_segundos: int):
    """
    Toma un bloqueo con nombre; lo suelta al salir del `with`.

    `ttl_segundos` es la RED DE SEGURIDAD, no la duración esperada: si el worker
    muere de golpe (OOM, `docker kill`) nadie ejecuta el `finally`, y sin
    expiración el bloqueo quedaría tomado para siempre y la tarea no volvería a
    correr nunca más — un fallo silencioso peor que el solapamiento que evita.
    Por eso debe ser HOLGADAMENTE mayor que la duración máxima plausible.
    """
    clave = f"{PREFIJO}{nombre}"
    token = f"{uuid.uuid4()}|{_etiqueta()}"

    # `add` solo escribe si la clave no existe: es la operación atómica que decide
    # el ganador. Un `get` + `set` tendría una ventana entre ambos por la que se
    # cuelan dos corridas — el bug clásico que este módulo existe para no tener.
    adquirido = bool(cache.add(clave, token, timeout=ttl_segundos))

    if not adquirido:
        # Puede volver vacío: el dueño soltó el bloqueo entre el `add` y este `get`,
        # o Redis está degradado. Es informativo, no se decide nada con esto.
        dueño = cache.get(clave) or ""
        dueño = dueño.split("|", 1)[-1] if dueño else "(desconocido)"
        logger.warning("bloqueo %r ocupado por %s — se salta esta corrida",
                       nombre, dueño)
        yield Bloqueo(nombre=nombre, adquirido=False, dueño_actual=dueño)
        return

    logger.info("bloqueo %r tomado (ttl %ss)", nombre, ttl_segundos)
    try:
        yield Bloqueo(nombre=nombre, adquirido=True, token=token)
    finally:
        # Solo borro si el valor SIGUE siendo el mío. Si el TTL venció a mitad de
        # una corrida larguísima, otro proceso ya tomó el bloqueo legítimamente y
        # borrarlo lo dejaría desprotegido justo cuando empieza a trabajar.
        #
        # `get` + `delete` no es atómico (haría falta un script Lua), así que la
        # ventana existe; es aceptable porque solo se abre en el caso ya anómalo de
        # haber excedido el TTL, y el daño se limita a perder la exclusión que ya
        # habíamos perdido de hecho al vencer.
        if cache.get(clave) == token:
            cache.delete(clave)
            logger.info("bloqueo %r liberado", nombre)
        else:
            logger.warning("bloqueo %r ya no era mío al terminar (¿venció el TTL "
                           "de %ss?) — no se toca", nombre, ttl_segundos)
