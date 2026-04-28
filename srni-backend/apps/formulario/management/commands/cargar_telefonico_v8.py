"""
Management command: cargar_telefonico_v8

Carga los 7 capítulos y ~110 preguntas del Perfil Telefónico SAAH V8
(Sistema de Atención y Asistencia al Hogar — entrevista remota).

Características del perfil telefónico:
  - Entrevista remota: sin preguntas de observación presencial
  - Sin capítulos: Vivienda, Territorio, Fuerza Pública, Perfil Sociolaboral
  - Variables con sufijo _tel para distinguirlas de versiones presenciales
  - Fuente: Diccionario_de_datos_V8_Perfil Telefónico SAAH UARIV

Capítulos:
  A — Identificación y Contacto      (HOGAR)
  B — Datos Básicos                   (PERSONA)
  C — Educación                       (PERSONA)
  D — Salud                           (PERSONA)
  E — Fuerza de Trabajo               (PERSONA)
  F — Rehabilitación Psicosocial      (PERSONA)
  T — Control                         (HOGAR)

Uso:
    python manage.py cargar_telefonico_v8
    python manage.py cargar_telefonico_v8 --reset
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.formulario.models import (
    InstrumentoVersion, Capitulo, Pregunta,
)

INSTRUMENTO_PK = "22222222-0004-0004-0004-000000000004"  # Telefónico SAAH V8

# ─────────────────────────────────────────────────────────────────────────────
# Capítulos: (codigo, nombre, orden, nivel, poblacion_objetivo)
# ─────────────────────────────────────────────────────────────────────────────
CAPITULOS = [
    ("A", "A. IDENTIFICACIÓN Y CONTACTO",     1,  "HOGAR",   "TODOS_MIEMBROS"),
    ("B", "B. DATOS BÁSICOS",                  2,  "PERSONA", "TODOS_MIEMBROS"),
    ("C", "C. EDUCACIÓN",                      3,  "PERSONA", "VICTIMAS_RUV_3_ANOS_MAS"),
    ("D", "D. SALUD",                          4,  "PERSONA", "TODOS_MIEMBROS"),
    ("E", "E. FUERZA DE TRABAJO",              5,  "PERSONA", "TODOS_MIEMBROS"),
    ("F", "F. REHABILITACIÓN PSICOSOCIAL",     6,  "PERSONA", "VICTIMAS_RUV"),
    ("T", "T. CONTROL",                        7,  "HOGAR",   "TODOS_MIEMBROS"),
]

# ─────────────────────────────────────────────────────────────────────────────
# Preguntas por capítulo
# Formato: (no_pregunta, codigo_externo, id_preg, texto, tipo, nivel,
#           obligatoria, orden, es_precargada, fuente_precarga, validaciones)
# _tel = versión telefónica de la variable (sin observación presencial)
# ─────────────────────────────────────────────────────────────────────────────
PREGUNTAS = {
    # ── A. IDENTIFICACIÓN Y CONTACTO ─────────────────────────────────────────
    "A": [
        ("A1",  "DT_ATENCION",     1161, "Dirección Territorial",                                           "COMBO_DINAMICO", "HOGAR", False, 1,  True,  "TABLA_USUARIOS",  {}),
        ("A2",  "DEPTO_ATENCION",  None, "Departamento de la Dirección Territorial",                        "COMBO_DINAMICO", "HOGAR", False, 2,  True,  "TABLA_USUARIOS",  {}),
        ("A3",  "Lud_encuesta",    1,    "Lugar de la Encuesta (municipio)",                                 "COMBO_DINAMICO", "HOGAR", True,  3,  False, "",                {}),
        ("A4",  "Perfil_tel",      2,    "Método de recolección",                                            "LISTA",          "HOGAR", True,  4,  False, "",                {}),
        ("A5",  "Z4_tel",          35,   "De acuerdo con su cultura, pueblo o rasgos físicos, ¿cómo se autoreconoce?", "LISTA", "HOGAR", True, 5, False, "",               {}),
        ("A6",  "Z5A_tel",         3,    "Lugar de residencia (municipio)",                                  "COMBO_DINAMICO", "HOGAR", True,  6,  False, "",                {}),
        ("A7",  "Z6_tel",          5,    "Zona de residencia",                                               "LISTA",          "HOGAR", True,  7,  False, "",                {}),
        ("A8",  "Z7_tel",          4,    "Barrio, centro poblado o vereda",                                  "TEXTO",          "HOGAR", False, 8,  False, "",                {"max_length": 200}),
        ("A9",  "Z8_tel",          6,    "Dirección de la vivienda",                                         "TEXTO",          "HOGAR", False, 9,  False, "",                {"max_length": 300}),
        ("A10", "Z9A_tel",         7,    "Teléfono fijo",                                                    "NUMERICO",       "HOGAR", False, 10, False, "",                {"min": 1000000, "max": 9999999999}),
        ("A11", "Z9B_tel",         8,    "Teléfono celular",                                                 "NUMERICO",       "HOGAR", True,  11, False, "",                {"min": 3000000000, "max": 3999999999}),
        ("A12", "Z9C_tel",         788,  "Otro teléfono de contacto",                                        "NUMERICO",       "HOGAR", False, 12, False, "",                {}),
        ("A13", "Z10_tel",         389,  "Correo electrónico",                                               "TEXTO",          "HOGAR", False, 13, False, "",                {"regex": "^[^@]+@[^@]+\\.[^@]+$"}),
        ("A14", "Z11_tel",         789,  "¿El lugar de correspondencia es el mismo de residencia?",          "BOOLEAN",        "HOGAR", True,  14, False, "",                {}),
        ("A15", "Z12_tel",         790,  "Dirección de correspondencia",                                     "TEXTO",          "HOGAR", False, 15, False, "",                {"max_length": 300}),
        ("A16", "Z15_tel",         1163, "Lugar de correspondencia (municipio)",                              "COMBO_DINAMICO", "HOGAR", False, 16, False, "",                {}),
        ("A17", "T6_tel",          10,   "Supervisor de la encuesta",                                        "TEXTO",          "HOGAR", True,  17, True,  "TABLA_USUARIOS",  {}),
    ],
    # ── B. DATOS BÁSICOS ──────────────────────────────────────────────────────
    "B": [
        ("B1",  "NOMBRE_1_tel",   13,   "Primer nombre",                                                     "TEXTO",    "PERSONA", True,  1,  True,  "RUV",                     {"max_length": 60}),
        ("B2",  "A2_tel",         15,   "Segundo nombre",                                                    "TEXTO",    "PERSONA", False, 2,  True,  "RUV",                     {"max_length": 60}),
        ("B3",  "A6_tel",         27,   "Fecha de nacimiento",                                               "FECHA",    "PERSONA", True,  3,  True,  "RUV",                     {}),
        ("B4",  "B9_tel",         14,   "¿Cuántos años cumplidos tiene?",                                    "NUMERICO", "PERSONA", True,  4,  False, "",                        {"min": 0, "max": 120}),
        ("B5",  "B10_tel",        1177, "Grupo etario",                                                      "LISTA",    "PERSONA", False, 5,  False, "",                        {}),
        ("B6",  "A3_tel",         30,   "¿Qué tipo de documento de identificación tiene?",                   "LISTA",    "PERSONA", True,  6,  True,  "TABLA_CONFORMACION_HOGAR", {}),
        ("B7",  "A4_tel",         32,   "¿Cuenta con el documento de identificación?",                      "BOOLEAN",  "PERSONA", True,  7,  False, "",                        {}),
        ("B8",  "A5_tel",         31,   "Número de documento de identificación",                             "TEXTO",    "PERSONA", True,  8,  True,  "RUV",                     {"max_length": 20}),
        ("B9",  "A8_tel",         24,   "Sexo",                                                              "LISTA",    "PERSONA", True,  9,  False, "",                        {}),
        ("B10", "B5_tel",         274,  "¿Cuál es su identidad de género?",                                 "LISTA",    "PERSONA", False, 10, False, "",                        {}),
        ("B11", "I6_tel",         88,   "¿Presenta alguna discapacidad?",                                   "BOOLEAN",  "PERSONA", True,  11, False, "",                        {}),
        ("B12", "I7A_tel",        89,   "¿Qué tipo de discapacidad presenta?",                              "LISTA_MULTIPLE", "PERSONA", False, 12, False, "",               {}),
        ("B13", "A9_tel",         28,   "El parentesco frente al jefe del hogar es:",                       "LISTA",    "PERSONA", True,  13, True,  "TABLA_CONFORMACION_HOGAR", {}),
        ("B14", "A11_tel",        289,  "¿La Unidad para las Víctimas incluyó a … en el RUPD/RUV?",         "LISTA",    "PERSONA", True,  14, True,  "RUV",                     {}),
        ("B15", "A20_tel",        16,   "Estado de inclusión en el RUV",                                    "LISTA",    "PERSONA", True,  15, True,  "RUV",                     {}),
        ("B16", "A21_tel",        17,   "Hecho victimizante principal",                                      "LISTA",    "PERSONA", True,  16, True,  "RUV",                     {}),
        ("B17", "A22_tel",        18,   "Fecha de ocurrencia del hecho victimizante",                       "FECHA",    "PERSONA", True,  17, True,  "RUV",                     {}),
        ("B18", "A23A_tel",       19,   "Municipio de ocurrencia del hecho victimizante",                   "COMBO_DINAMICO", "PERSONA", True, 18, True, "RUV",               {}),
    ],
    # ── C. EDUCACIÓN ──────────────────────────────────────────────────────────
    "C": [
        ("C1", "G2_tel",        None, "¿Actualmente está matriculado(a) en preescolar, escuela, colegio o universidad?", "BOOLEAN", "PERSONA", True, 1, True, "MODELO_EDUCACION", {}),
        ("C2", "G15_tel",       339,  "¿Sabe leer y escribir?",                                                          "BOOLEAN", "PERSONA", True, 2, False, "",                {}),
        ("C3", "G4_tel",        73,   "¿Por qué no asiste actualmente a un establecimiento educativo?",                  "LISTA",   "PERSONA", False, 3, False, "",               {}),
        ("C4", "G7B_GRADO_tel", 76,   "¿Cuál es el nivel educativo más alto alcanzado?",                                "LISTA",   "PERSONA", True, 4, False, "",                {}),
        ("C5", "G18_tel",       None, "¿Completó el último nivel de básica primaria?",                                   "BOOLEAN", "PERSONA", False, 5, False, "",               {}),
    ],
    # ── D. SALUD ──────────────────────────────────────────────────────────────
    "D": [
        ("D1", "H8_tel",   None, "¿Está afiliado a algún régimen de seguridad social en salud?",                         "LISTA",          "PERSONA", True,  1, True,  "MODELO_SALUD", {}),
        ("D2", "H10_tel",  None, "¿Qué hizo principalmente cuando tuvo problemas de salud?",                             "LISTA",          "PERSONA", True,  2, False, "",             {}),
        ("D3", "H13_tel",  807,  "¿Tiene diagnóstico de enfermedad crónica no transmisible?",                            "BOOLEAN",        "PERSONA", True,  3, False, "",             {}),
        ("D4", "H14_tel",  808,  "¿Cuál enfermedad crónica?",                                                             "LISTA_MULTIPLE",  "PERSONA", False, 4, False, "",            {}),
        ("D5", "I7E_tel",  400,  "¿Presenta diagnóstico de enfermedades ruinosas o de alto costo?",                      "BOOLEAN",        "PERSONA", True,  5, False, "",             {}),
        ("D6", "B2_tel",   26,   "¿Se encuentra alguna mujer del hogar en estado de embarazo?",                          "BOOLEAN",        "PERSONA", True,  6, False, "",             {}),
        ("D7", "B2A_tel",  393,  "¿En la actualidad es madre lactante?",                                                 "BOOLEAN",        "PERSONA", False, 7, False, "",             {}),
    ],
    # ── E. FUERZA DE TRABAJO ──────────────────────────────────────────────────
    "E": [
        ("E1",  "L1_tel",    119, "¿Cuál fue la actividad principal la semana pasada?",                                   "LISTA",    "PERSONA", True,  1,  False, "", {}),
        ("E2",  "L2_tel",    None,"¿Realizó la semana pasada alguna actividad paga por una hora o más?",                  "BOOLEAN",  "PERSONA", True,  2,  False, "", {}),
        ("E3",  "L5_tel",    123, "¿Buscó trabajo la semana pasada?",                                                     "BOOLEAN",  "PERSONA", True,  3,  False, "", {}),
        ("E4",  "L7_tel",    125, "¿En las últimas 4 semanas hizo alguna diligencia para conseguir trabajo?",             "BOOLEAN",  "PERSONA", True,  4,  False, "", {}),
        ("E5",  "L9_tel",    127, "¿Ha trabajado al menos 2 semanas en los últimos 12 meses?",                            "BOOLEAN",  "PERSONA", True,  5,  False, "", {}),
        ("E6",  "L13_tel",   131, "¿En qué ocupación trabajó la semana pasada?",                                          "TEXTO",    "PERSONA", False, 6,  False, "", {"max_length": 200}),
        ("E7",  "L14_tel",   132, "¿En qué actividad económica trabajó?",                                                 "LISTA",    "PERSONA", False, 7,  False, "", {}),
        ("E8",  "L15_tel",   133, "¿Cuántas horas trabajó la semana pasada?",                                             "NUMERICO", "PERSONA", False, 8,  False, "", {"min": 0, "max": 168}),
        ("E9",  "L17_tel",   None,"¿Cuánto ganó el mes pasado (salario, honorarios)?",                                    "NUMERICO", "PERSONA", False, 9,  False, "", {"min": 0}),
        ("E10", "L22_tel",   141, "¿Recibió pensión de jubilación?",                                                      "BOOLEAN",  "PERSONA", False, 10, False, "", {}),
        ("E11", "M8_tel",    896, "¿Recibió subsidios del Estado?",                                                       "BOOLEAN",  "PERSONA", False, 11, False, "", {}),
        ("E12", "M4C1A_tel", 161, "Observaciones al capítulo Fuerza de Trabajo",                                          "TEXTO_LARGO", "PERSONA", False, 12, False, "", {"max_length": 1000}),
    ],
    # ── F. REHABILITACIÓN PSICOSOCIAL ─────────────────────────────────────────
    "F": [
        ("F1", "I8_tel",   90,   "¿Necesita o requiere atención en salud mental?",                                        "BOOLEAN",        "PERSONA", True,  1, False, "", {}),
        ("F2", "I10A_tel", 92,   "¿Ha recibido atención psicosocial?",                                                    "BOOLEAN",        "PERSONA", True,  2, False, "", {}),
        ("F3", "I11A_tel", 93,   "¿Con qué frecuencia ha recibido atención psicosocial?",                                 "LISTA",          "PERSONA", False, 3, False, "", {}),
        ("F4", "I25B_tel", 809,  "¿Qué institución le brindó atención psicosocial?",                                      "LISTA",          "PERSONA", False, 4, False, "", {}),
        ("F5", "I27_tel",  811,  "¿Ha recibido medidas de rehabilitación física o psicológica?",                          "BOOLEAN",        "PERSONA", True,  5, False, "", {}),
        ("F6", "I28A_tel", 812,  "¿Qué tipo de medidas de rehabilitación?",                                               "LISTA_MULTIPLE",  "PERSONA", False, 6, False, "", {}),
        ("F7", "I30_tel",  892,  "Observaciones al capítulo Rehabilitación",                                              "TEXTO_LARGO",    "PERSONA", False, 7, False, "", {"max_length": 1000}),
    ],
    # ── T. CONTROL ────────────────────────────────────────────────────────────
    "T": [],
}


class Command(BaseCommand):
    help = "Carga los 7 capítulos del Perfil Telefónico SAAH V8 (entrevista remota)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Elimina los capítulos existentes antes de recargar",
        )

    def handle(self, *args, **options):
        try:
            instrumento = InstrumentoVersion.objects.get(pk=INSTRUMENTO_PK)
        except InstrumentoVersion.DoesNotExist:
            self.stderr.write(
                "Error: ejecuta primero: python manage.py loaddata perfiles_iniciales"
            )
            return

        if options["reset"]:
            instrumento.capitulos.all().delete()
            self.stdout.write("Capítulos previos eliminados.")

        with transaction.atomic():
            cap_objs = {}
            for codigo, nombre, orden, nivel, poblacion in CAPITULOS:
                cap, created = Capitulo.objects.update_or_create(
                    instrumento=instrumento,
                    codigo=codigo,
                    defaults={
                        "nombre": nombre,
                        "orden": orden,
                        "nivel": nivel,
                        "poblacion_objetivo": poblacion,
                    },
                )
                cap_objs[codigo] = cap
                status = "creado" if created else "actualizado"
                self.stdout.write(f"  Capítulo {codigo}: {nombre} [{status}]")

            total_preguntas = 0
            for cap_codigo, preguntas in PREGUNTAS.items():
                cap = cap_objs.get(cap_codigo)
                if not cap:
                    continue
                for (no_preg, cod_ext, id_preg, texto, tipo, nivel,
                     obligatoria, orden, es_precarg, fuente, validaciones) in preguntas:
                    Pregunta.objects.update_or_create(
                        capitulo=cap,
                        codigo_externo=cod_ext,
                        defaults={
                            "no_pregunta": no_preg,
                            "id_preg": id_preg,
                            "variable_bd": cod_ext.replace("_tel", ""),
                            "texto": texto,
                            "tipo": tipo,
                            "nivel": nivel,
                            "obligatoria": obligatoria,
                            "orden": orden,
                            "es_precargada": es_precarg,
                            "fuente_precarga": fuente,
                            "validaciones": validaciones,
                            "activa": True,
                        },
                    )
                    total_preguntas += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f"\nTelefónico SAAH V8 cargado: "
                    f"{len(CAPITULOS)} capítulos, {total_preguntas} preguntas."
                )
            )
