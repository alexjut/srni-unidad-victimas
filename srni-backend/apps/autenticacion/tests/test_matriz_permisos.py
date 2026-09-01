"""
Matriz de permisos por rol — la validación manual, convertida en regresión.

Por qué existe. `docs/frontend/VALIDACION-PERMISOS.md` es una lista de chequeo
que había que recorrer a mano, rol por rol y pantalla por pantalla. Nunca se
diligenció: al 1-sep-2026 sus cuatro usuarios seguían en PENDIENTE y las
columnas de resultado, vacías. Una matriz que nadie recorre no protege nada.

Este archivo la ejecuta. Declara los **cinco perfiles que existen en
producción** —medidos el 1-sep-2026— y comprueba, endpoint por endpoint, quién
entra y quién no. Lo que antes dependía de que alguien se acordara de hacer
clic, ahora falla en la batería si alguien cambia un permiso sin querer.

Los perfiles reales y su población al 1-sep-2026:

    ADMINISTRADOR   rni carac rep admin exc        1 usuario
    COORDINADOR     rni carac rep       exc        1 usuario
    SUPERVISOR      rni       rep       exc        1 usuario
    DOCUMENTADOR    rni       rep                  1 usuario
    ENCUESTADOR     rni carac                  1.157 usuarios

Nota sobre COORDINADOR. Tiene a la vez `caracterizar` y
`autorizar_excepciones`, lo que contradice el criterio con el que se creó el
permiso —«quien autoriza el salto de un control no puede ser el mismo que lo
ejecuta en campo»—. La prueba refleja el estado real, no el deseado: si se
decide separar esas funciones, primero se cambia el perfil y después esta
tabla. Queda anotado para que el cambio sea deliberado y no silencioso.
"""
import pytest
from rest_framework.test import APIClient

from apps.autenticacion.models import Perfil, Usuario

# codigo -> (buscar_rni, caracterizar, ver_reportes, administrar, autorizar_excepciones)
PERFILES = {
    "ADMINISTRADOR": (True,  True,  True,  True,  True),
    "COORDINADOR":   (True,  True,  True,  False, True),
    "SUPERVISOR":    (True,  False, True,  False, True),
    "DOCUMENTADOR":  (True,  False, True,  False, False),
    "ENCUESTADOR":   (True,  True,  False, False, False),
}

ROLES = list(PERFILES)

# Cada fila: (metodo, url, {rol: espera_entrar})
# «Entrar» = el permiso no bloquea (no es 401/403). El código concreto puede ser
# 200, 400 o 404 según el dato; lo que se afirma aquí es el control de acceso.
MATRIZ = [
    # Instrumentos: cualquier rol autenticado (Bug 1)
    ("get", "/api/formulario/instrumentos/",
     {r: True for r in ROLES}),

    # Lectura operativa: campo, supervisión y administración (Bug 3)
    ("get", "/api/hogares/",
     {"ADMINISTRADOR": True, "COORDINADOR": True, "SUPERVISOR": True,
      "DOCUMENTADOR": True, "ENCUESTADOR": True}),
    ("get", "/api/encuestas/",
     {"ADMINISTRADOR": True, "COORDINADOR": True, "SUPERVISOR": True,
      "DOCUMENTADOR": True, "ENCUESTADOR": True}),

    # Escritura operativa: solo quien puede caracterizar
    ("post", "/api/hogares/",
     {"ADMINISTRADOR": True, "COORDINADOR": True, "SUPERVISOR": False,
      "DOCUMENTADOR": False, "ENCUESTADOR": True}),

    # Reportes agregados: ver_reportes o administrar (Bug 2)
    ("get", "/api/reportes/supervisor/",
     {"ADMINISTRADOR": True, "COORDINADOR": True, "SUPERVISOR": True,
      "DOCUMENTADOR": True, "ENCUESTADOR": False}),
    ("get", "/api/reportes/dashboard/series/",
     {"ADMINISTRADOR": True, "COORDINADOR": True, "SUPERVISOR": True,
      "DOCUMENTADOR": True, "ENCUESTADOR": False}),

    # Producción por encuestador: lectura operativa
    ("get", "/api/reportes/encuestador/",
     {r: True for r in ROLES}),

    # Excepciones de vigencia: autorizar_excepciones o administrar.
    # ENCUESTADOR y DOCUMENTADOR quedan fuera a propósito.
    ("get", "/api/habilitaciones/",
     {"ADMINISTRADOR": True, "COORDINADOR": True, "SUPERVISOR": True,
      "DOCUMENTADOR": False, "ENCUESTADOR": False}),

    # Búsqueda en el RNI: todos los perfiles la tienen hoy
    ("post", "/api/victimas/buscar/",
     {r: True for r in ROLES}),

    # Administración de usuarios: solo administrar
    ("get", "/api/usuarios/",
     {"ADMINISTRADOR": True, "COORDINADOR": False, "SUPERVISOR": False,
      "DOCUMENTADOR": False, "ENCUESTADOR": False}),
]

BLOQUEADO = (401, 403)


@pytest.fixture
def usuarios(db):
    creados = {}
    for codigo, (rni, carac, rep, admin, exc) in PERFILES.items():
        perfil = Perfil.objects.create(
            codigo=codigo, nombre=codigo.title(),
            puede_buscar_rni=rni, puede_caracterizar=carac,
            puede_ver_reportes=rep, puede_administrar=admin,
            puede_autorizar_excepciones=exc, activo=True,
        )
        creados[codigo] = Usuario.objects.create_user(
            codigo_usuario=f"MP_{codigo}", password="Test2026!",
            nombre_completo=f"Usuario {codigo}", email=f"mp_{codigo.lower()}@test.dev",
            perfil=perfil, activo=True,
        )
    return creados


def _cliente(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def _llamar(cliente, metodo, url):
    if metodo == "get":
        return cliente.get(url)
    return cliente.post(url, {}, format="json")


@pytest.mark.parametrize("metodo,url,esperado", MATRIZ,
                         ids=[f"{m.upper()} {u}" for m, u, _ in MATRIZ])
@pytest.mark.parametrize("rol", ROLES)
def test_matriz_de_permisos(usuarios, rol, metodo, url, esperado):
    """Cada celda de la matriz: el rol entra o el permiso lo bloquea."""
    resp = _llamar(_cliente(usuarios[rol]), metodo, url)
    entra = resp.status_code not in BLOQUEADO

    if esperado[rol]:
        assert entra, (
            f"{rol} debería poder {metodo.upper()} {url} y recibió "
            f"{resp.status_code}. Si el cambio es deliberado, actualiza MATRIZ."
        )
    else:
        assert not entra, (
            f"{rol} NO debería poder {metodo.upper()} {url} y recibió "
            f"{resp.status_code}: el permiso no lo está bloqueando."
        )


@pytest.mark.parametrize("metodo,url,_esperado", MATRIZ,
                         ids=[f"{m.upper()} {u}" for m, u, _ in MATRIZ])
def test_anonimo_siempre_bloqueado(db, metodo, url, _esperado):
    """Ningún endpoint de la matriz responde a quien no ha iniciado sesión."""
    resp = _llamar(APIClient(), metodo, url)
    assert resp.status_code in BLOQUEADO, (
        f"{metodo.upper()} {url} respondió {resp.status_code} sin autenticar."
    )


def test_la_matriz_cubre_los_cinco_perfiles_de_produccion():
    """
    Guarda contra el olvido: si mañana se crea un perfil nuevo en producción y
    no se agrega aquí, esta prueba no lo detecta sola —pero deja constancia de
    cuáles estaban cubiertos y desde cuándo—.
    """
    assert set(PERFILES) == {
        "ADMINISTRADOR", "COORDINADOR", "SUPERVISOR", "DOCUMENTADOR", "ENCUESTADOR",
    }
    for fila in MATRIZ:
        _metodo, url, esperado = fila
        faltantes = set(ROLES) - set(esperado)
        assert not faltantes, f"{url} no declara expectativa para: {faltantes}"


def test_quien_autoriza_excepciones_no_deberia_caracterizar():
    """
    Separación de funciones, documentada como criterio en `PuedeAutorizarExcepciones`.

    Hoy **falla por diseño del dato**: COORDINADOR tiene los dos permisos. Se
    deja marcada como xfail para que el día que se separen las funciones la
    prueba pase sola y avise, en vez de quedar el criterio solo en un docstring.
    """
    conflictivos = [
        codigo for codigo, (_r, carac, _rep, admin, exc) in PERFILES.items()
        if exc and carac and not admin
    ]
    if conflictivos:
        pytest.xfail(
            f"Perfiles que autorizan y además caracterizan: {conflictivos}. "
            "Es una decisión de operación pendiente, no un defecto de código."
        )
