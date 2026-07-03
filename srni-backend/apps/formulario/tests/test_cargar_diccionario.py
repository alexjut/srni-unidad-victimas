import pytest
from django.core.management import call_command
from apps.formulario.models import (
    Instrumento, Capitulo, Pregunta, OpcionRespuesta, ReglaSkipLogic,
)


@pytest.mark.django_db
class TestCargarDiccionarioV8:

    def test_carga_exitosa(self):
        call_command("cargar_diccionario_v8")
        assert Instrumento.objects.filter(codigo="ASISTENCIA").exists()
        assert Instrumento.objects.filter(version="V8").exists()
        assert Capitulo.objects.count() == 7
        assert Pregunta.objects.count() >= 30

    def test_idempotente(self):
        """Correr 2 veces no duplica registros."""
        call_command("cargar_diccionario_v8")
        pregs_antes = Pregunta.objects.count()
        opts_antes = OpcionRespuesta.objects.count()
        reglas_antes = ReglaSkipLogic.objects.count()

        call_command("cargar_diccionario_v8")
        assert Pregunta.objects.count() == pregs_antes
        assert OpcionRespuesta.objects.count() == opts_antes
        assert ReglaSkipLogic.objects.count() == reglas_antes

    def test_dry_run_no_persiste(self):
        call_command("cargar_diccionario_v8", dry_run=True)
        assert Instrumento.objects.count() == 0
        assert Pregunta.objects.count() == 0

    def test_capitulos_todos_presentes(self):
        call_command("cargar_diccionario_v8")
        codigos = set(Capitulo.objects.values_list("codigo", flat=True))
        assert codigos == {"A", "B", "C", "D", "E", "F", "G"}

    def test_capitulo_c_tiene_aplicabilidad_correcta(self):
        call_command("cargar_diccionario_v8")
        cap_c = Capitulo.objects.get(codigo="C")
        assert cap_c.poblacion_objetivo == "AUTORIZADO_TUTOR_CUIDADOR"
        # El fixture usa 'tipo_persona_in' como clave declarativa
        assert "tipo_persona_in" in cap_c.aplicabilidad
        assert "AUTORIZADO" in cap_c.aplicabilidad["tipo_persona_in"]

    def test_capitulo_d_solo_ruv_mayores(self):
        call_command("cargar_diccionario_v8")
        cap_d = Capitulo.objects.get(codigo="D")
        assert cap_d.aplicabilidad.get("ruv_incluido") is True
        assert cap_d.aplicabilidad.get("edad_min") == 3

    def test_opciones_tienen_id_resp_vivanto(self):
        call_command("cargar_diccionario_v8")
        tipo_doc = Pregunta.objects.filter(codigo_externo="A8_tel").first()
        assert tipo_doc is not None, "Pregunta A8_tel debe existir"
        ids_resp = set(tipo_doc.opciones.values_list("id_resp_vivanto", flat=True))
        assert 4598 in ids_resp  # CC
        assert 4599 in ids_resp  # CE

    def test_reglas_skip_logic_cargadas(self):
        call_command("cargar_diccionario_v8")
        assert ReglaSkipLogic.objects.count() >= 15
        # I6_tel (discapacidad) debe habilitar I7A_tel (tipo de discapacidad)
        regla_discapacidad = ReglaSkipLogic.objects.filter(
            pregunta_origen__codigo_externo="I6_tel",
            accion="HABILITAR",
        ).first()
        assert regla_discapacidad is not None
        assert regla_discapacidad.valor_trigger == "1"

    def test_reglas_expresion_capitulo(self):
        """Las reglas de expresión que afectan capítulos completos están presentes."""
        call_command("cargar_diccionario_v8")
        # El fixture crea reglas HABILITAR para capítulos D, E, F, G con expresion_origen
        regla_cap_d = ReglaSkipLogic.objects.filter(
            capitulo_afectado__codigo="D",
            accion="HABILITAR",
        ).first()
        assert regla_cap_d is not None
        assert "ruv_incluido" in regla_cap_d.expresion_origen

    def test_preguntas_nivel_hogar_y_persona(self):
        call_command("cargar_diccionario_v8")
        niveles = set(Pregunta.objects.values_list("nivel", flat=True))
        assert "HOGAR" in niveles
        assert "PERSONA" in niveles

    def test_pregunta_tipos_validos(self):
        call_command("cargar_diccionario_v8")
        tipos_cargados = set(Pregunta.objects.values_list("tipo", flat=True))
        tipos_validos = {"TEXTO", "TEXTO_LARGO", "NUMERICO", "FECHA", "BOOLEAN",
                         "RADIO", "LISTA", "LISTA_MULTIPLE", "COMBO_DINAMICO"}
        assert tipos_cargados.issubset(tipos_validos)

    def test_version_fuente_documental(self):
        call_command("cargar_diccionario_v8")
        instrumento = Instrumento.objects.get(version="V8")
        assert "520.06.06-1" in instrumento.fuente_documental
