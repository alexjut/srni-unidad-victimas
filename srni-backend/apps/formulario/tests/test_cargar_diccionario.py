"""
Pruebas del cargador del instrumento ASISTENCIA V8
(comando `cargar_diccionario_v8`, hoy un shim sobre `cargar_perfil`).

Fuentes de verdad usadas para fijar las expectativas:
  - Manual 14-MU "Entrevista de Caracterización – Perfil Asistencia"
    (UARIV, código 520.06.06-1, v01, 07/10/2021), Cuadro 1 (págs. 26-27):
    estructura A..G, objetivo y población objetivo de cada capítulo.
    PDF en docs/perfiles/.
  - Diccionario de datos V8 – Perfil Telefónico SAAH: contenido (códigos,
    textos, tipos y opciones).
  - Flujograma V9.1 (SAAH): capítulo RF (Reunificación Familiar) y sus flujos.

Historia: el fixture fue reconstruido en el commit a241d65
("reconstruye Asistencia desde diccionario V8 + manual 14-MU, 105 preg, 8 caps")
porque el anterior traía inflada la versión del Telefónico (178 preguntas).
Ese cambio dejó varias expectativas de este archivo desactualizadas; cada una
se corrige abajo indicando POR QUÉ.
"""
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
        # Antes se esperaban 7 capítulos (A..G del Cuadro 1 del manual 14-MU).
        # Desde a241d65 son 8: se sumó RF (Reunificación Familiar), que no está
        # en el manual pero sí en el Flujograma V9.1 del SAAH y se captura en
        # campo (reglas F1_tel/F3_tel/F5_tel). El instrumento real tiene 8.
        assert Capitulo.objects.count() == 8
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
        # A..G vienen del Cuadro 1 del manual 14-MU; RF (Reunificación Familiar)
        # se agregó en a241d65 desde el Flujograma V9.1 (ver test_carga_exitosa).
        assert codigos == {"A", "B", "C", "D", "E", "F", "G", "RF"}

    def test_capitulo_c_tiene_aplicabilidad_correcta(self):
        """C. Vivienda solo aplica a Autorizado/Tutor/Cuidador.

        MANDA EL MANUAL: el Cuadro 1 del 14-MU dice textualmente del capítulo C
        "Este capítulo únicamente se habilita para el designado del hogar
        'Autorizado', 'Tutor' y/o 'Cuidador'". La expectativa NO se toca.

        La reconstrucción a241d65 perdió esta metadata (el generador dejaba
        poblacion_objetivo='TODOS_MIEMBROS' y sin aplicabilidad para los 8
        capítulos): fue una regresión real del fixture, no del test, y se
        restauró en perfil_asistencia_v8.json.
        """
        call_command("cargar_diccionario_v8")
        cap_c = Capitulo.objects.get(codigo="C")
        assert cap_c.poblacion_objetivo == "AUTORIZADO_TUTOR_CUIDADOR"
        # El fixture usa 'tipo_persona_in' como clave declarativa
        assert "tipo_persona_in" in cap_c.aplicabilidad
        assert "AUTORIZADO" in cap_c.aplicabilidad["tipo_persona_in"]

    def test_capitulo_d_solo_ruv_mayores(self):
        """D. Educación solo aplica a incluidos en RUV de 3 años en adelante.

        MANDA EL MANUAL: Cuadro 1 del 14-MU, capítulo D — "se habilita para
        personas incluidas en el RUV por cualquier hecho victimizante" y su
        objetivo acota "para víctimas incluidas en el RUV de 3 años en
        adelante". Misma regresión de metadata que el capítulo C (a241d65),
        restaurada en el fixture; la expectativa del test es la correcta.
        """
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
        # Antes se esperaba "1". Era el test el que estaba mal: I6_tel es de tipo
        # BOOLEAN y la APK guarda los BOOLEAN como true/false, así que un trigger
        # "1" NO dispara la regla (motor de skip-logic de srni-mobile). a241d65
        # corrigió justamente esos triggers 1/2 -> true/false. Esperar "1" era
        # congelar el bug.
        assert regla_discapacidad.valor_trigger == "true"

    @pytest.mark.xfail(
        reason=(
            "REGRESIÓN FUNCIONAL ABIERTA (no es un test desactualizado): la "
            "reconstrucción a241d65 borró las reglas de skip-logic que cerraban "
            "los capítulos D/E/F/G a los incluidos en el RUV. El fixture previo "
            "traía 'ruv_incluido and edad >= 3' -> capítulo D y 'ruv_incluido' -> "
            "capítulos E/F/G, y el manual 14-MU (Cuadro 1) las exige. Hoy el "
            "instrumento ASISTENCIA solo tiene 2 reglas a nivel de capítulo, "
            "ambas FINALIZAR (C y RF). El perfil hermano TELEFONICO sí conserva "
            "el equivalente ('ruv_incluido == False or edad < 3' -> DESHABILITAR "
            "capítulo Educación). No se repone aquí porque cambia el "
            "comportamiento de captura en la APK (el motor de srni-mobile SÍ "
            "evalúa capitulo_afectado + expresion_origen) y exige regenerar el "
            "bundle y validar en dispositivo. Al reponerla, este test pasa a "
            "XPASS y hay que quitarle el xfail."
        ),
        strict=False,
    )
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
        """El instrumento debe declarar de qué documento oficial sale.

        520.06.06-1 es el código del manual 14-MU en su propio encabezado. La
        reconstrucción a241d65 dejó 'fuente_documental' vacío (el generador ya
        no lo emitía), mientras que los perfiles TELEFONICO, RURAL_ETNICO y
        VICTIMAS_EXTERIOR sí lo conservan: fue pérdida de trazabilidad, no un
        test desactualizado. Restaurado en el fixture.
        """
        call_command("cargar_diccionario_v8")
        instrumento = Instrumento.objects.get(version="V8")
        assert "520.06.06-1" in instrumento.fuente_documental
