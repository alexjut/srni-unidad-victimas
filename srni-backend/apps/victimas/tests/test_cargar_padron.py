"""
Tests de la carga del padrón, con la fuente Oracle simulada.

Se prueba sin Oracle a propósito: la conexión a `.9` se cortó dos veces en dos días
durante este trabajo, y una carga que solo se puede verificar cuando la red coopera
es una carga que no se verifica.

Lo que se protege:
1. Que el DRY-RUN no escriba **nada**.
2. Que reprocesar no duplique (idempotencia por `cons_persona`).
3. Que las personas sin tipo de documento se carguen igual y queden encontrables.
4. Que la bitácora registre lo que pasó, incluidos los descartes.
"""
from unittest import mock

import datetime
import pytest
from django.core.management import call_command

pytestmark = pytest.mark.django_db


# Filas como las devuelve el cursor de Oracle: (per_idpersona, per_tipodoc,
# per_numerodoc, n1, n2, a1, a2, fecha_nac, pert_etnica, genero_hom, discap)
FILAS = [
    (1001, "Cedula de Ciudadanía / Contraseña", "1030547250",
     "MARIA", "LUISA", "GOMEZ", "RENDON",
     datetime.datetime(1985, 6, 15), "Ninguna", "Mujer", None),
    (1002, "TI", "1122334455", "JUAN", "", "PEREZ", "LOPEZ",
     datetime.datetime(2012, 3, 8), "Indigena", "Hombre", "1"),
    # sin tipo de documento: el 14,5 % de la fuente
    (1003, "SIN INFORMACION", "9988776655", "ANA", "", "TORRES", "",
     datetime.datetime(1990, 1, 1), None, None, None),
    # sin número: se descarta
    (1004, "CC", "   ", "PEDRO", "", "SILVA", "", None, "Ninguna", "Hombre", None),
]


class _CursorFalso:
    """Cursor mínimo con la interfaz que usa el comando."""

    def __init__(self, filas):
        self._filas = list(filas)
        self.arraysize = 1000
        self.sql = None

    def execute(self, sql, params=None):
        self.sql = sql
        self.params = params or {}
        desde = self.params.get("desde", 0)
        self._pendientes = [f for f in self._filas if f[0] > desde]

    def fetchmany(self, n):
        lote, self._pendientes = self._pendientes[:n], self._pendientes[n:]
        return lote


class _ConexionFalsa:
    def __init__(self, filas):
        self._filas = filas
        self.cerrada = False

    def cursor(self):
        return _CursorFalso(self._filas)

    def close(self):
        self.cerrada = True


@pytest.fixture
def fuente(db):
    """Simula Oracle y el catálogo de tipos, y siembra los TipoDocumento de SICAV."""
    from apps.parametricas.models import TipoDocumento
    for codigo, nombre in [("CC", "Cédula de Ciudadanía"), ("TI", "Tarjeta de Identidad"),
                           ("RC", "Registro Civil"), ("CE", "Cédula de Extranjería")]:
        TipoDocumento.objects.get_or_create(codigo=codigo, defaults={"nombre": nombre})

    conexion = _ConexionFalsa(FILAS)
    with mock.patch("apps.sincronizacion.oracle.conexion.abrir_conexion",
                    return_value=conexion), \
         mock.patch("apps.sincronizacion.oracle.conexion.resolver_config",
                    return_value={"user": "U", "host": "30.0.1.9", "port": 1521,
                                  "service": "ENTREVISTARN", "password": "x"}), \
         mock.patch("apps.victimas.homologacion.cargar_catalogo_tipodoc_oracle",
                    return_value={}):
        yield conexion


# ── 1. el dry-run no escribe ─────────────────────────────────────────────────
def test_el_dry_run_no_escribe_nada(fuente):
    from apps.victimas.models import CargaPadron, Victima
    call_command("cargar_padron_oracle", verbosity=0)
    assert Victima.objects.count() == 0
    assert CargaPadron.objects.get().estado == "SIMULADA"


def test_el_dry_run_igual_cuenta_lo_que_haria(fuente):
    from apps.victimas.models import CargaPadron
    call_command("cargar_padron_oracle", verbosity=0)
    carga = CargaPadron.objects.get()
    assert carga.leidas == 4
    assert carga.descartadas == 1                    # la fila sin número
    assert carga.sin_tipo_documento == 1             # "SIN INFORMACION"


# ── 2. la carga real ─────────────────────────────────────────────────────────
def test_carga_las_personas_con_su_homologacion(fuente):
    from apps.victimas.models import Victima
    call_command("cargar_padron_oracle", "--confirmar", verbosity=0)

    assert Victima.objects.count() == 3              # la cuarta se descartó

    maria = Victima.objects.get(cons_persona=1001)
    assert maria.tipo_documento.codigo == "CC"       # de "Cedula de Ciudadanía / Contraseña"
    assert maria.genero == "F"
    assert maria.pertenencia_etnica == "NINGUNA"
    assert maria.discapacidad is False

    juan = Victima.objects.get(cons_persona=1002)
    assert juan.tipo_documento.codigo == "TI"
    assert juan.pertenencia_etnica == "INDIGENA"
    assert juan.discapacidad is True


def test_la_persona_sin_tipo_se_carga_y_queda_encontrable(fuente):
    """
    El caso de 1.126.615 personas. Se cargan sin tipo —no se les inventa— y el índice
    de respaldo las hace encontrables.
    """
    from apps.victimas.models import Victima
    from apps.victimas.repository import DjangoVictimaRepository

    call_command("cargar_padron_oracle", "--confirmar", verbosity=0)
    ana = Victima.objects.get(cons_persona=1003)
    assert ana.tipo_documento is None
    assert ana.numero_documento_hash_sin_tipo

    r = DjangoVictimaRepository().buscar_por_documento("CC", "9988776655")
    assert r.encontrado is True
    assert "VERIFIQUE" in r.mensaje


def test_reprocesar_no_duplica(fuente):
    """
    Idempotencia por `cons_persona`. Importa de verdad: con la conexión cortándose,
    reanudar y solaparse es lo normal, no la excepción.
    """
    from apps.victimas.models import Victima
    call_command("cargar_padron_oracle", "--confirmar", verbosity=0)
    primera = Victima.objects.count()
    call_command("cargar_padron_oracle", "--confirmar", verbosity=0)
    assert Victima.objects.count() == primera


def test_la_segunda_pasada_actualiza_no_crea(fuente):
    from apps.victimas.models import CargaPadron
    call_command("cargar_padron_oracle", "--confirmar", verbosity=0)
    call_command("cargar_padron_oracle", "--confirmar", verbosity=0)
    ultima = CargaPadron.objects.order_by("-iniciada_en").first()
    assert ultima.creadas == 0
    assert ultima.actualizadas == 3


# ── 3. reanudación ───────────────────────────────────────────────────────────
def test_desde_salta_lo_ya_procesado(fuente):
    """El mecanismo que hace la carga viable con una conexión intermitente."""
    from apps.victimas.models import Victima
    call_command("cargar_padron_oracle", "--confirmar", "--desde", "1002", verbosity=0)
    assert Victima.objects.filter(cons_persona=1001).exists() is False
    assert Victima.objects.filter(cons_persona=1003).exists() is True


def test_el_limite_corta(fuente):
    from apps.victimas.models import CargaPadron
    call_command("cargar_padron_oracle", "--confirmar", "--limite", "2", verbosity=0)
    assert CargaPadron.objects.get().leidas == 2


# ── 4. la bitácora ───────────────────────────────────────────────────────────
def test_la_bitacora_guarda_el_motivo_de_los_descartes(fuente):
    from apps.victimas.models import CargaPadron
    call_command("cargar_padron_oracle", "--confirmar", verbosity=0)
    carga = CargaPadron.objects.get()
    assert carga.estado == "COMPLETADA"
    assert carga.terminada_en is not None
    assert "sin número de documento" in carga.motivos_descarte
    assert "30.0.1.9" in carga.origen
    assert "password" not in carga.origen.lower()   # sin credenciales en la bitácora


def test_no_carga_el_estado_ruv(fuente):
    """
    Decisión explícita: los 4 códigos de ESTADO_RUV no tienen catálogo conocido, y ese
    campo decide si una persona puede caracterizarse. Se deja el default del modelo en
    vez de adivinar.
    """
    from apps.victimas.models import Victima
    call_command("cargar_padron_oracle", "--confirmar", verbosity=0)
    victima = Victima.objects.get(cons_persona=1001)
    assert victima.estado_ruv == "EN_PROCESO"        # el default, no algo inventado
    assert victima.habilitado_para_caracterizacion is True
