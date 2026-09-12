"""
Límites de peticiones — y por qué ninguno funcionaba.

─── El defecto, medido en producción el 12-sep-2026 ─────────────────────────
Ocho ingresos seguidos y sesenta peticiones anónimas contra producción, sin un
solo 429. Los límites estaban configurados, la caché funcionaba, Redis respondía,
y aun así no contaban nada.

La causa estaba en las claves que quedaban en Redis:

    throttle_anon_191.107.130.174:54030,30.0.1.5,172.21.0.7
    throttle_anon_191.107.130.174:53238,30.0.1.5,172.21.0.7
                               └── el puerto de origen, distinto cada vez

El FortiWeb antepone al cliente como `IP:puerto`, y detrás vienen el NPM y la red
interna de Docker. DRF toma esa cadena **completa** como identidad del cliente, y
el puerto efímero cambia en cada conexión: cada petición parecía venir de un
cliente nuevo, así que el contador nacía en 1 y nunca llegaba al tope.

Es la misma causa que ya estaba documentada en `apps/auditoria/red.py` —«el WAF
manda IP:puerto y sin limpiarlo el INSERT de auditoría falla»— pero allí se
arregló solo para la auditoría. Acá seguía intacta.

**Lo que NO estaba roto:** los límites por usuario (`UserRateThrottle` y los que
heredan de él) se cuentan por el identificador del usuario, no por la IP, así que
siempre funcionaron. Y el bloqueo de cuenta por intentos fallidos —cinco intentos,
quince minutos, en `autenticacion/views.py`— también, porque se guarda por código
de usuario. Esa era, sin saberlo, la única defensa real contra fuerza bruta.

─── Por qué arreglarlo solo no alcanzaba ────────────────────────────────────
Corregir la identidad **enciende de golpe** todos los límites por IP, y con los
valores que había eso habría roto la operación en vez de protegerla: 20 peticiones
anónimas por hora y 5 ingresos por minuto son cifras pensadas para una persona,
no para una entidad detrás de una sola salida a internet.

El caso concreto que lo hace evidente: el 15 de septiembre hay quince personas en
una sala compartiendo IP. Con 5 ingresos por minuto, la sexta ve «demasiados
intentos» con la clave correcta, y eso se lee como que las credenciales no sirven.
Con 20 peticiones anónimas por hora, el pre-test se cae para dos tercios del
grupo.

Así que los topes de este módulo se fijaron pensando en **una entidad por IP**, y
la defensa contra fuerza bruta se apoya donde sí es precisa: el bloqueo por cuenta.
"""
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

from apps.auditoria.red import ip_de_request


class IPLimpiaMixin:
    """
    Identifica al cliente por su IP, sin el puerto y sin la cadena de proxies.

    Delega en `apps.auditoria.red.ip_de_request`, que es el único lugar del
    proyecto que sabe desenredar lo que llega detrás del FortiWeb. Duplicar esa
    lógica acá es cómo se llega a que la auditoría vea una IP y el limitador otra.

    ⚠️ `ip_de_request` devuelve `'0.0.0.0'` cuando no puede determinar la IP, y
    para la auditoría eso está bien: nunca rompe el INSERT del registro. Para un
    limitador sería lo contrario de lo que se quiere. Si un día el WAF deja de
    reenviar la cabecera, **todos los usuarios del país compartirían ese cubo** y
    el sistema entero se cortaría a sí mismo con el tope de una sola IP.

    Así que el centinela se traduce a `None`, que DRF entiende como «no se puede
    identificar» y **no aplica el límite**. El modo de fallo correcto es quedarse
    sin protección, no quedarse sin servicio: un problema de cabeceras no puede
    convertirse en una caída. Y el ingreso no queda desnudo por eso, porque su
    defensa real —el bloqueo por cuenta— no depende de la IP.
    """

    #: Lo que `ip_de_request` devuelve cuando no hay nada utilizable.
    SIN_IP = '0.0.0.0'

    def get_ident(self, request):
        ip = ip_de_request(request)
        return None if (not ip or ip == self.SIN_IP) else ip


class LoginRateThrottle(IPLimpiaMixin, AnonRateThrottle):
    """
    Tope de ingresos por IP. Dimensionado para **una sala entera**, no una persona.

    Lo que frena la fuerza bruta contra una cuenta concreta no es esto: es el
    bloqueo por cuenta de `LoginView` —cinco intentos fallidos, quince minutos—,
    que se cuenta por código de usuario y por lo tanto no lo afecta que veinte
    personas compartan salida a internet.

    Esto es el techo contra una avalancha: un guion que dispare miles de ingresos
    desde una misma IP se corta, y una sala de veinte personas entrando a la vez
    —con algún dedo equivocado de por medio— pasa sin enterarse.
    """

    scope = 'login'


class PruebaPublicaThrottle(IPLimpiaMixin, AnonRateThrottle):
    """
    El cuestionario en línea de la capacitación, que no pide credenciales.

    Treinta y siete personas lo responden desde la misma oficina, y cada una hace
    del orden de cuatro peticiones —pedir el cuestionario, consultar si ya
    respondió, enviar—. El pre-test y el post-test caen además dentro de la misma
    hora. Con el tope genérico de 20 por hora, la mayoría del grupo se quedaba sin
    poder responder.

    No queda sin límite: es un endpoint público que escribe en la base, y
    responder dos veces ya lo impide la restricción de un intento por correo.
    """

    scope = 'prueba_publica'


class MovilPublicoThrottle(IPLimpiaMixin, AnonRateThrottle):
    """
    Lo que la APK consulta sin haber ingresado: la versión publicada y la descarga.

    La consulta de versión la hace cada teléfono al abrir la aplicación. Una
    territorial con veinte encuestadoras detrás de una IP supera veinte peticiones
    por hora sin esfuerzo, y quedarse sin saber la versión disponible es
    exactamente cómo alguien sale a campo con una APK vieja.
    """

    scope = 'movil_publico'


class BusquedaRNIThrottle(UserRateThrottle):
    """
    30 búsquedas del padrón por hora **por usuario**.

    Se cuenta por usuario, así que nunca estuvo afectado por el defecto de la IP:
    este límite sí venía funcionando. Es antienumeración —evitar que una cuenta
    recorra el padrón— y por eso tiene que seguir siendo por persona y estrecho.
    """

    scope = 'busqueda_rni'


class IAConsultaThrottle(UserRateThrottle):
    """20 consultas de IA por hora por usuario. También por usuario, también sano."""

    scope = 'ia_consulta'
