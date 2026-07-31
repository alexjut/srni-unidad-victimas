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
# per_numerodoc, n1, n2, a1, a2, fecha_nac, pert_etnica, genero_hom, discap,
# estado_ruv)
FILAS = [
    (1001, "Cedula de Ciudadanía / Contraseña", "1030547250",
     "MARIA", "LUISA", "GOMEZ", "RENDON",
     datetime.datetime(1985, 6, 15), "Ninguna", "Mujer", None, 1),
    (1002, "TI", "1122334455", "JUAN", "", "PEREZ", "LOPEZ",
     datetime.datetime(2012, 3, 8), "Indigena", "Hombre", "1", 3),
    # sin tipo de documento: el 14,5 % de la fuente
    (1003, "SIN INFORMACION", "9988776655", "ANA", "", "TORRES", "",
     datetime.datetime(1990, 1, 1), None, None, None, None),
    # sin número: se descarta
    (1004, "CC", "   ", "PEDRO", "", "SILVA", "", None, "Ninguna", "Hombre", None, 2),
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


def test_el_estado_ruv_se_carga(fuente):
    from apps.victimas.models import Victima
    call_command("cargar_padron_oracle", "--confirmar", verbosity=0)

    assert Victima.objects.get(cons_persona=1001).estado_ruv == "INCLUIDO"
    assert Victima.objects.get(cons_persona=1002).estado_ruv == "EN_PROCESO"


def test_sin_estado_en_la_fuente_queda_el_default(fuente):
    from apps.victimas.models import Victima
    call_command("cargar_padron_oracle", "--confirmar", verbosity=0)
    assert Victima.objects.get(cons_persona=1003).estado_ruv == "EN_PROCESO"


# ── el filtro de víctimas: quién entra al padrón ─────────────────────────────
# El filtro vive en el SQL (`WHERE c.estado_ruv IN (...)`), así que lo que se prueba
# es que el SQL que sale del comando lleve el estado correcto. Un cursor simulado
# devuelve lo que se le ponga; Oracle no.
def test_por_defecto_solo_pide_victimas_incluidas(fuente):
    """
    Sin esto el padrón llevaría 1,83 millones de personas que **no son víctimas
    incluidas** — no incluidas, en valoración y excluidas. Medido en producción:
    de 7,76 M en GIC_PERSONA solo 5.936.769 tienen estado 1.
    """
    cursores = []
    original = fuente.cursor
    fuente.cursor = lambda: cursores.append(original()) or cursores[-1]
    call_command("cargar_padron_oracle", verbosity=0)

    sql = cursores[0].sql
    assert "estado_ruv IN (1)" in sql
    # INNER JOIN, no LEFT: con LEFT entrarían las que no están en el corte, y además
    # Oracle cambia a lookups fila a fila (220 filas/s contra 3.943).
    assert "LEFT JOIN" not in sql.upper()


def test_se_pueden_pedir_otros_estados_explicitamente(fuente):
    cursores = []
    original = fuente.cursor
    fuente.cursor = lambda: cursores.append(original()) or cursores[-1]
    call_command("cargar_padron_oracle", "--estados", "1,2", verbosity=0)
    assert "estado_ruv IN (1, 2)" in cursores[0].sql


def test_estados_no_numericos_se_rechazan(fuente):
    """`--estados` se interpola en el SQL (Oracle no acepta listas en un bind), así
    que si no se valida es una inyección."""
    from django.core.management.base import CommandError
    with pytest.raises(CommandError, match="números separados por coma"):
        call_command("cargar_padron_oracle", "--estados", "1) OR (1=1", verbosity=0)
