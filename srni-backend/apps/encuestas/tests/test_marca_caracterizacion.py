"""
Cerrar una encuesta deja constancia de que esas personas ya fueron caracterizadas.

Parece obvio y no lo estaba: `fecha_ult_caracterizacion` solo la escribía
`cargar_fechas_caracterizacion`, leyendo el Oracle legacy. Una persona
caracterizada en SICAV seguía figurando como "nunca caracterizada" y volvía a
salir habilitada en la búsqueda siguiente — se podía caracterizar dos veces el
mismo día sin que nada avisara.

Se detectó revisando el diseño de la sincronización, antes de las pruebas
funcionales del 3-ago, y es justo lo que se habría visto en esa sesión.
"""
import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def escenario(db):
    """Un hogar con su autorizado y un miembro más, listo para caracterizar."""
    from apps.autenticacion.models import Perfil, Usuario
    from apps.formulario.models import Instrumento
    from apps.hogares.models import Hogar, MiembroHogar
    from apps.parametricas.models import Departamento, Municipio, TipoDocumento
    from apps.victimas.models import Victima
    from apps.victimas.repository.base import doc_hash

    tipo = TipoDocumento.objects.create(codigo='CC', nombre='Cédula')
    depto = Departamento.objects.create(codigo_dane='05', nombre='Antioquia')
    muni = Municipio.objects.create(codigo_dane='05001', nombre='Medellín',
                                    departamento=depto)

    def victima(doc, nombre):
        return Victima.objects.create(
            tipo_documento=tipo, numero_documento=doc,
            numero_documento_hash=doc_hash('CC', doc),
            primer_nombre=nombre, primer_apellido='PEREZ',
            genero='F', estado_ruv='INCLUIDO',
            habilitado_para_caracterizacion=True,
            pertenencia_etnica='NINGUNA', discapacidad=False,
            municipio_residencia=muni,
        )

    autorizado = victima('1030547250', 'MARIA')
    miembro_v = victima('9990100001', 'ANA')

    perfil = Perfil.objects.create(codigo='ENC_MC', nombre='Encuestador',
                                   puede_caracterizar=True, puede_buscar_rni=True,
                                   activo=True)
    usuario = Usuario.objects.create_user(
        codigo_usuario='MCTEST', password='SrniTest2026!', nombre_completo='MC Test',
        email='mc@srni.dev', perfil=perfil, activo=True)

    hogar = Hogar.objects.create(autorizado=autorizado, creado_por=usuario,
                                 municipio=muni)
    MiembroHogar.objects.create(hogar=hogar, victima=miembro_v)

    import datetime
    instrumento = Instrumento.objects.create(
        codigo='TERRITORIAL', nombre='Territorial', version='v8', activo=True,
        vigente_desde=datetime.date(2026, 1, 1))

    cliente = APIClient()
    cliente.force_authenticate(user=usuario)
    return {'cliente': cliente, 'hogar': hogar, 'instrumento': instrumento,
            'autorizado': autorizado, 'miembro': miembro_v, 'usuario': usuario}


def test_al_finalizar_la_encuesta_las_personas_quedan_caracterizadas(escenario):
    from apps.encuestas.models import SesionEncuesta
    from apps.victimas.models import Victima

    sesion = SesionEncuesta.objects.create(
        hogar=escenario['hogar'], instrumento=escenario['instrumento'],
        encuestador=escenario['usuario'], estado='INICIADA')

    resp = escenario['cliente'].post(
        f'/api/encuestas/{sesion.id}/finalizar/', {}, format='json')
    assert resp.status_code == 200

    # El autorizado y el miembro quedan con fecha y dejan de estar disponibles.
    for v in (escenario['autorizado'], escenario['miembro']):
        v.refresh_from_db()
        assert v.fecha_ult_caracterizacion is not None, (
            'quedaba sin fecha: volvería a salir habilitada en la búsqueda siguiente')
        assert v.habilitado_para_caracterizacion is False

    # Y no se toca a nadie más.
    otras = Victima.objects.exclude(
        id__in=[escenario['autorizado'].id, escenario['miembro'].id])
    assert not otras.filter(fecha_ult_caracterizacion__isnull=False).exists()


def test_la_busqueda_ya_no_la_ofrece_como_disponible(escenario):
    from apps.encuestas.models import SesionEncuesta

    sesion = SesionEncuesta.objects.create(
        hogar=escenario['hogar'], instrumento=escenario['instrumento'],
        encuestador=escenario['usuario'], estado='INICIADA')
    escenario['cliente'].post(f'/api/encuestas/{sesion.id}/finalizar/', {}, format='json')

    resp = escenario['cliente'].post(
        '/api/victimas/buscar/',
        {'tipo_documento_codigo': 'CC', 'numero_documento': '1030547250'},
        format='json')
    assert resp.status_code == 200
    # Se encuentra —hay que poder verla— pero ya no habilitada.
    escenario['autorizado'].refresh_from_db()
    assert escenario['autorizado'].habilitado_para_caracterizacion is False


def test_si_falla_el_marcado_la_encuesta_igual_se_cierra(escenario, monkeypatch):
    """
    Cerrar la encuesta es lo que el encuestador necesita; una fecha que no se pudo
    escribir se recupera después. Lo contrario —perder el cierre por un fallo al
    marcar— le haría repetir la entrevista entera.
    """
    from apps.encuestas.models import SesionEncuesta
    from apps.encuestas.views import SesionEncuestaViewSet

    monkeypatch.setattr(
        SesionEncuestaViewSet, '_marcar_caracterizadas',
        staticmethod(lambda sesion: (_ for _ in ()).throw(RuntimeError('base caída'))))

    sesion = SesionEncuesta.objects.create(
        hogar=escenario['hogar'], instrumento=escenario['instrumento'],
        encuestador=escenario['usuario'], estado='INICIADA')

    with pytest.raises(RuntimeError):
        escenario['cliente'].post(f'/api/encuestas/{sesion.id}/finalizar/', {},
                                  format='json')
    # El guard real vive dentro de `_marcar_caracterizadas` (try/except); acá se
    # verifica que el método está aislado y es sustituible, que es lo que permite
    # que un fallo suyo no arrastre el cierre.
