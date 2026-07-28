"""
Tests del endpoint de estado de sincronización.

Para qué sirve el endpoint: que un supervisor pueda responder "¿este hogar llegó a
Oracle?" sin pedírselo a un desarrollador. Y sobre todo, que vea **lo que falló** —
porque los procedures del legacy no avisan de sus propios errores.

Lo que se protege aquí es el resumen: que un hogar con un paso fallido no se
muestre como COMPLETO por tener el resto verificado.
"""
import pytest
from rest_framework.test import APIClient

from apps.sincronizacion.models import EstadoPaso, PasoEscritura, RegistroEscrituraOracle
from apps.sincronizacion.views import _resumir

pytestmark = pytest.mark.django_db


@pytest.fixture
def hogar(db):
    from apps.hogares.models import Hogar
    from apps.parametricas.models import TipoDocumento
    from apps.victimas.models import Victima

    tipo = TipoDocumento.objects.create(codigo="CC", nombre="Cédula")
    victima = Victima.objects.create(
        tipo_documento=tipo, numero_documento="900003", primer_nombre="A",
        primer_apellido="B", fecha_nacimiento="1990-01-01", genero="M",
    )
    return Hogar.objects.create(codigo_hogar="API-TEST-1", autorizado=victima,
                                estado="BORRADOR")


def _paso(hogar, paso, estado, destino="produccion", origen="x"):
    return RegistroEscrituraOracle.objects.create(
        hogar=hogar, paso=paso, origen_id=f"{origen}-{paso}", estado=estado,
        destino_entorno=destino, intento=1,
    )


# ── el resumen, que es lo que mira un supervisor ─────────────────────────────
def test_un_paso_fallido_manda_sobre_el_resto():
    """Nueve pasos bien y uno mal NO es 'completo': es un hogar que hay que revisar."""
    assert _resumir({"pasos_fallidos": 1, "pasos_totales": 10,
                     "pasos_verificados": 9, "pasos_dry_run": 0}) == "CON_FALLOS"


def test_todo_verificado_es_completo():
    assert _resumir({"pasos_fallidos": 0, "pasos_totales": 11,
                     "pasos_verificados": 11, "pasos_dry_run": 0}) == "COMPLETO"


def test_solo_dry_run_es_simulado():
    """Importa distinguirlo: en DRY-RUN no hay NADA escrito en Oracle."""
    assert _resumir({"pasos_fallidos": 0, "pasos_totales": 11,
                     "pasos_verificados": 0, "pasos_dry_run": 11}) == "SIMULADO"


def test_a_medias_es_en_proceso():
    assert _resumir({"pasos_fallidos": 0, "pasos_totales": 11,
                     "pasos_verificados": 5, "pasos_dry_run": 0}) == "EN_PROCESO"


# ── el endpoint ──────────────────────────────────────────────────────────────
def test_el_endpoint_exige_autenticacion(hogar):
    assert APIClient().get("/api/sincronizacion/registros/estado/").status_code in (401, 403)


def test_el_estado_agrupa_por_hogar_y_destino(hogar, django_user_model):
    """
    Un mismo hogar escrito en local y en producción debe salir en DOS renglones:
    mezclarlos haría creer que está en Oracle cuando solo se ensayó en la réplica.
    """
    _paso(hogar, PasoEscritura.HOGAR, EstadoPaso.VERIFICADO, destino="local")
    _paso(hogar, PasoEscritura.HOGAR, EstadoPaso.VERIFICADO, destino="produccion")
    _paso(hogar, PasoEscritura.PERSONA, EstadoPaso.FALLIDO, destino="produccion")

    # El permiso no mira `is_superuser`, mira el perfil: la supervisión puede leer.
    from apps.autenticacion.models import Perfil
    perfil = Perfil.objects.create(codigo="SUP", nombre="Supervisión",
                                   puede_ver_reportes=True, activo=True)
    user = django_user_model.objects.create_user(
        codigo_usuario="SUP999", email="s@uariv.test", password="x",
        nombre_completo="Supervisor", perfil=perfil)
    client = APIClient()
    client.force_authenticate(user=user)
    resp = client.get("/api/sincronizacion/registros/estado/")

    assert resp.status_code == 200
    destinos = {f["destino"]: f for f in resp.data}
    assert set(destinos) == {"local", "produccion"}
    assert destinos["local"]["estado"] == "COMPLETO"
    assert destinos["produccion"]["estado"] == "CON_FALLOS"
    assert destinos["produccion"]["pasos_fallidos"] == 1
