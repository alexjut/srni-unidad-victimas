"""
La idempotencia se lleva POR DESTINO, no en global.

Bug que protege (encontrado el 2026-07-28, revisando el escritor antes del primer
piloto en producción): el ledger se consultaba por (hogar, paso, origen) sin mirar
`destino_entorno`. Como el hogar demo ya estaba escrito y VERIFICADO contra la
réplica LOCAL, al correr contra PRODUCCIÓN el paso HOGAR habría devuelto
`idempotente=True` **sin escribir nada**, y los pasos siguientes se habrían anclado
a un HOG_CODIGO inexistente allí. El comando habría dicho "11/11 VERIFICADO"
después de no migrar absolutamente nada.

Es el peor tipo de fallo posible en esta capa: uno que se lee como éxito.
"""
import pytest

from apps.sincronizacion.models import EstadoPaso, PasoEscritura, RegistroEscrituraOracle
from apps.sincronizacion.oracle.escritor import EscritorOracle
from apps.sincronizacion.oracle.mapeo import ResolverCatalogos

pytestmark = pytest.mark.django_db


def _catalogos():
    return ResolverCatalogos(usuario_servicio_id="999999", perfil_servicio_id="1",
                             estricto=True)


def _escritor(destino):
    # No se abre conexión: solo se consulta el ledger.
    return EscritorOracle(confirmar=True, destino=destino, catalogos=_catalogos())


@pytest.fixture
def hogar(db):
    from apps.hogares.models import Hogar
    from apps.parametricas.models import TipoDocumento
    from apps.victimas.models import Victima

    tipo = TipoDocumento.objects.create(codigo="CC", nombre="Cédula")
    victima = Victima.objects.create(
        tipo_documento=tipo, numero_documento="900001",
        primer_nombre="A", primer_apellido="B",
        fecha_nacimiento="1990-01-01", genero="M",
    )
    return Hogar.objects.create(codigo_hogar="PILOTO-TEST-1", autorizado=victima,
                                estado="BORRADOR")


def _marcar_escrito(hogar, destino, hog_codigo="999999-LOCAL"):
    RegistroEscrituraOracle.objects.create(
        hogar=hogar, paso=PasoEscritura.HOGAR, origen_id=str(hogar.pk),
        estado=EstadoPaso.VERIFICADO, destino_hog_codigo=hog_codigo,
        destino_entorno=destino, intento=1,
    )


def test_lo_escrito_en_local_no_cuenta_como_escrito_en_produccion(hogar):
    """El caso que habría hecho fracasar el piloto en silencio."""
    _marcar_escrito(hogar, "local")
    assert _escritor("produccion")._ya_verificado(hogar, PasoEscritura.HOGAR, hogar.pk) is False


def test_lo_escrito_en_produccion_no_cuenta_como_escrito_en_local(hogar):
    """Y al revés: cada destino lleva su propia contabilidad."""
    _marcar_escrito(hogar, "produccion", hog_codigo="999999-PROD")
    assert _escritor("local")._ya_verificado(hogar, PasoEscritura.HOGAR, hogar.pk) is False


def test_el_mismo_destino_si_es_idempotente(hogar):
    """Lo que sí debe seguir funcionando: re-correr contra el mismo destino no duplica."""
    _marcar_escrito(hogar, "local")
    escritor = _escritor("local")
    assert escritor._ya_verificado(hogar, PasoEscritura.HOGAR, hogar.pk) is True
    reg = escritor._registro_verificado(hogar, PasoEscritura.HOGAR, hogar.pk)
    assert reg.destino_hog_codigo == "999999-LOCAL"


def test_el_registro_recuperado_es_el_del_destino_correcto(hogar):
    """
    Con el hogar escrito en AMBOS destinos, cada corrida debe recuperar su propio
    HOG_CODIGO: mezclarlos anclaría las respuestas al hogar de la otra base.
    """
    _marcar_escrito(hogar, "local", hog_codigo="999999-LOCAL")
    _marcar_escrito(hogar, "produccion", hog_codigo="999999-PROD")
    local = _escritor("local")._registro_verificado(hogar, PasoEscritura.HOGAR, hogar.pk)
    prod = _escritor("produccion")._registro_verificado(hogar, PasoEscritura.HOGAR, hogar.pk)
    assert local.destino_hog_codigo == "999999-LOCAL"
    assert prod.destino_hog_codigo == "999999-PROD"
