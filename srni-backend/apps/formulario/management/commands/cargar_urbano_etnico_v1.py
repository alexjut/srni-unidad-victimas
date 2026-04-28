"""
Management command: cargar_urbano_etnico_v1

Carga los 12 capítulos y ~200 preguntas del Perfil Urbano Étnico V1
(comunidades étnicas en contexto urbano).

Contexto del perfil:
  Aplica a hogares de pueblos indígenas, afrocolombianos, raizales, palenqueros
  y rom que residen en cabeceras municipales urbanas.
  Combina preguntas del instrumento general con módulos de identidad étnica
  y adaptaciones para el entorno urbano (sin módulo de territorio rural).

Capítulos:
  A  — Identificación                (HOGAR)
  C  — Vivienda                      (HOGAR)
  D  — Retornos y Reubicaciones       (HOGAR)
  E  — Reunificación Familiar         (HOGAR)
  JA — Alimentación                   (HOGAR)
  T  — Control                        (HOGAR)
  B  — Datos Básicos + Identidad Étnica (PERSONA)
  F  — Educación                      (PERSONA)
  G  — Salud                          (PERSONA)
  H  — Rehabilitación                 (PERSONA)
  JF — Fuerza de Trabajo              (PERSONA)
  K  — Perfil Sociolaboral            (PERSONA)

Fuente: Diccionario_de_datos_Entrevista de Caracterización_Perfil Urbano EtnicoV1.xlsx

Uso:
    python manage.py cargar_urbano_etnico_v1
    python manage.py cargar_urbano_etnico_v1 --reset
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.formulario.models import (
    InstrumentoVersion, Capitulo, Pregunta,
)

INSTRUMENTO_PK = "22222222-0005-0005-0005-000000000005"  # Urbano Étnico V1

CAPITULOS = [
    ("A",  "A. IDENTIFICACIÓN",                  1,  "HOGAR",   "TODOS_MIEMBROS"),
    ("C",  "C. VIVIENDA",                         2,  "HOGAR",   "TODOS_MIEMBROS"),
    ("D",  "D. RETORNOS Y REUBICACIONES",         3,  "HOGAR",   "TODOS_MIEMBROS"),
    ("E",  "E. REUNIFICACIÓN FAMILIAR",            4,  "HOGAR",   "TODOS_MIEMBROS"),
    ("JA", "J. ALIMENTACIÓN",                     9,  "HOGAR",   "TODOS_MIEMBROS"),
    ("T",  "T. CONTROL",                         10,  "HOGAR",   "TODOS_MIEMBROS"),
    ("B",  "B. DATOS BÁSICOS E IDENTIDAD ÉTNICA", 5,  "PERSONA", "TODOS_MIEMBROS"),
    ("F",  "F. EDUCACIÓN",                        6,  "PERSONA", "VICTIMAS_RUV_3_ANOS_MAS"),
    ("G",  "G. SALUD",                            7,  "PERSONA", "TODOS_MIEMBROS"),
    ("H",  "H. REHABILITACIÓN",                   8,  "PERSONA", "TODOS_MIEMBROS"),
    ("JF", "J. FUERZA DE TRABAJO",               10,  "PERSONA", "TODOS_MIEMBROS"),
    ("K",  "K. PERFIL SOCIOLABORAL",             11,  "PERSONA", "TODOS_MIEMBROS"),
]

PREGUNTAS = {
    # ── A. IDENTIFICACIÓN ─────────────────────────────────────────────────────
    "A": [
        ("A1",  "DT_ATENCION",  1161, "Dirección Territorial",                                                  "COMBO_DINAMICO", "HOGAR", False, 1,  True,  "TABLA_USUARIOS", {}),
        ("A2",  "Z2",           1,    "Lugar de la Encuesta",                                                    "COMBO_DINAMICO", "HOGAR", True,  2,  False, "",               {}),
        ("A3",  "Z3",           2,    "Método de recolección",                                                   "LISTA",          "HOGAR", True,  3,  False, "",               {}),
        ("A4",  "Z4",           35,   "De acuerdo con su cultura, pueblo o rasgos físicos, ¿cómo se autoreconoce?", "LISTA",       "HOGAR", True,  4,  False, "",               {}),
        ("A5",  "Z5A",          3,    "Lugar de residencia (municipio)",                                         "COMBO_DINAMICO", "HOGAR", True,  5,  False, "",               {}),
        ("A6",  "Z6",           5,    "Zona de residencia",                                                      "LISTA",          "HOGAR", True,  6,  False, "",               {}),
        ("A7",  "Z7",           4,    "Barrio o sector",                                                         "TEXTO",          "HOGAR", False, 7,  False, "",               {"max_length": 200}),
        ("A8",  "Z8",           6,    "Dirección de la vivienda",                                                "TEXTO",          "HOGAR", False, 8,  False, "",               {"max_length": 300}),
        ("A9",  "Z9A",          7,    "Teléfono fijo",                                                           "NUMERICO",       "HOGAR", False, 9,  False, "",               {"min": 1000000, "max": 9999999999}),
        ("A10", "Z9B",          8,    "Teléfono celular",                                                        "NUMERICO",       "HOGAR", False, 10, False, "",               {"min": 3000000000, "max": 3999999999}),
        ("A11", "Z9C",          788,  "Otro teléfono de contacto",                                               "NUMERICO",       "HOGAR", False, 11, False, "",               {}),
        ("A12", "Z10",          389,  "Correo electrónico",                                                      "TEXTO",          "HOGAR", False, 12, False, "",               {"regex": "^[^@]+@[^@]+\\.[^@]+$"}),
        ("A13", "Z11",          789,  "¿El lugar de correspondencia es el mismo de residencia?",                 "BOOLEAN",        "HOGAR", True,  13, False, "",               {}),
        ("A14", "Z12",          790,  "Dirección de correspondencia",                                            "TEXTO",          "HOGAR", False, 14, False, "",               {"max_length": 300}),
        ("A15", "T6",           10,   "Supervisor de la encuesta",                                               "TEXTO",          "HOGAR", True,  15, True,  "TABLA_USUARIOS", {}),
    ],
    # ── C. VIVIENDA ───────────────────────────────────────────────────────────
    "C": [
        ("C1",  "C1",       36,   "¿En qué tipo de vivienda habita el hogar?",                                   "LISTA",          "HOGAR", True,  1,  False, "", {}),
        ("C2",  "D5",       45,   "La vivienda ocupada por este hogar es:",                                      "LISTA",          "HOGAR", True,  2,  False, "", {}),
        ("C3",  "D7",       47,   "¿Qué tipo de documento soporte tiene?",                                       "LISTA",          "HOGAR", False, 3,  False, "", {}),
        ("C4",  "C2",       37,   "¿Cuál es el material predominante de las paredes exteriores?",                "LISTA",          "HOGAR", True,  4,  False, "", {}),
        ("C5",  "C3",       38,   "¿Cuál es el material predominante de los pisos?",                             "LISTA",          "HOGAR", True,  5,  False, "", {}),
        ("C6",  "C7",       275,  "De acuerdo con sus usos y costumbres, ¿la vivienda es adecuada para su hogar?", "BOOLEAN",      "HOGAR", True,  6,  False, "", {}),
        ("C7",  "D8A",      318,  "¿Con cuáles servicios cuenta el hogar? Energía eléctrica",                    "BOOLEAN",        "HOGAR", True,  7,  False, "", {}),
        ("C8",  "D8B",      319,  "¿Con cuáles servicios cuenta el hogar? Alcantarillado",                       "BOOLEAN",        "HOGAR", True,  8,  False, "", {}),
        ("C9",  "D8C",      320,  "¿Con cuáles servicios cuenta el hogar? Acueducto",                            "BOOLEAN",        "HOGAR", True,  9,  False, "", {}),
        ("C10", "D8D",      796,  "¿Con cuáles servicios cuenta el hogar? Gas natural conectado a red",          "BOOLEAN",        "HOGAR", True,  10, False, "", {}),
        ("C11", "D8E",      797,  "¿Con cuáles servicios cuenta el hogar? Recolección de basuras",               "BOOLEAN",        "HOGAR", True,  11, False, "", {}),
        ("C12", "D10",      300,  "¿De dónde proviene principalmente el agua que utilizan para beber?",          "LISTA",          "HOGAR", True,  12, False, "", {}),
        ("C13", "D14",      50,   "¿Cuál es el principal servicio sanitario con el que cuenta el hogar?",        "LISTA",          "HOGAR", True,  13, False, "", {}),
        ("C14", "D1",       42,   "Incluyendo sala-comedor, ¿de cuántos cuartos dispone este hogar?",            "NUMERICO",       "HOGAR", True,  14, False, "", {"min": 1, "max": 30}),
        ("C15", "D2",       43,   "¿En cuántos de esos cuartos duermen las personas de este hogar?",             "NUMERICO",       "HOGAR", True,  15, False, "", {"min": 1, "max": 30}),
        ("C16", "C5",       40,   "¿La vivienda se encuentra en zona de alto riesgo de desastre natural?",       "LISTA",          "HOGAR", True,  16, False, "", {}),
        ("C17", "C_OBSERVA",252,  "Observaciones al capítulo Vivienda",                                          "TEXTO_LARGO",    "HOGAR", False, 17, False, "", {"max_length": 1000}),
    ],
    # ── D. RETORNOS Y REUBICACIONES ───────────────────────────────────────────
    "D": [
        ("D2",  "E1A",  798, "¿El hogar se encuentra en proceso de retorno?",                                    "BOOLEAN",     "HOGAR", True,  1,  False, "", {}),
        ("D3",  "E1B",  799, "¿El hogar se encuentra en proceso de reubicación?",                                "BOOLEAN",     "HOGAR", True,  2,  False, "", {}),
        ("D4",  "E1",   62,  "¿Está de acuerdo con el proceso de retorno o reubicación?",                       "LISTA",       "HOGAR", False, 3,  False, "", {}),
        ("D5",  "RR1",  800, "¿Está en el lugar habitual de residencia antes del desplazamiento?",               "BOOLEAN",     "HOGAR", True,  4,  False, "", {}),
        ("D6",  "RR3",  884, "¿Voluntariamente decidió retornar o reubicarse?",                                  "BOOLEAN",     "HOGAR", True,  5,  False, "", {}),
        ("D7",  "RR6",  801, "¿En el proceso lo acompañó alguna entidad del Estado?",                            "BOOLEAN",     "HOGAR", True,  6,  False, "", {}),
        ("D8",  "E1C",  334, "Observaciones al capítulo Retornos y Reubicaciones",                               "TEXTO_LARGO", "HOGAR", False, 7,  False, "", {"max_length": 1000}),
    ],
    # ── E. REUNIFICACIÓN FAMILIAR ─────────────────────────────────────────────
    "E": [
        ("E1", "F1",  None, "¿Algún miembro del hogar se vio obligado a separarse del núcleo familiar?",        "BOOLEAN",     "HOGAR", True,  1, False, "", {}),
        ("E2", "F3A", 69,   "¿Conoce el paradero actual de los miembros separados?",                            "BOOLEAN",     "HOGAR", False, 2, False, "", {}),
        ("E3", "F5",  803,  "¿Ha realizado alguna gestión para reunificarse?",                                   "BOOLEAN",     "HOGAR", False, 3, False, "", {}),
        ("E4", "F4",  70,   "¿Por qué no ha podido reunificarse?",                                               "LISTA",       "HOGAR", False, 4, False, "", {}),
        ("E5", "F6",  804,  "Observaciones al capítulo Reunificación Familiar",                                  "TEXTO_LARGO", "HOGAR", False, 5, False, "", {"max_length": 1000}),
    ],
    # ── JA. ALIMENTACIÓN ──────────────────────────────────────────────────────
    "JA": [
        ("I3",  "I1B",  878,  "¿Ha tenido dificultades para adquirir alimentos en el último mes?",              "BOOLEAN",     "HOGAR", True,  1,  False, "", {}),
        ("I4",  "J1A",  None, "¿En los últimos 7 días consumió Leguminosas?",                                   "BOOLEAN",     "HOGAR", True,  2,  False, "", {}),
        ("I5",  "J1B",  None, "¿En los últimos 7 días consumió Cereales?",                                      "BOOLEAN",     "HOGAR", True,  3,  False, "", {}),
        ("I6",  "J1C",  None, "¿En los últimos 7 días consumió Tubérculos y plátanos?",                         "BOOLEAN",     "HOGAR", True,  4,  False, "", {}),
        ("I7",  "J1D",  None, "¿En los últimos 7 días consumió Verduras y hortalizas?",                         "BOOLEAN",     "HOGAR", True,  5,  False, "", {}),
        ("I8",  "J1E",  None, "¿En los últimos 7 días consumió Frutas?",                                        "BOOLEAN",     "HOGAR", True,  6,  False, "", {}),
        ("I9",  "J1F",  None, "¿En los últimos 7 días consumió Carnes?",                                        "BOOLEAN",     "HOGAR", True,  7,  False, "", {}),
        ("I10", "J1T",  1185, "¿En los últimos 7 días consumió Pescados y/o mariscos?",                         "BOOLEAN",     "HOGAR", True,  8,  False, "", {}),
        ("I12", "J1H",  None, "¿En los últimos 7 días consumió Huevo?",                                         "BOOLEAN",     "HOGAR", True,  9,  False, "", {}),
        ("I13", "J1J",  None, "¿En los últimos 7 días consumió Lácteos?",                                       "BOOLEAN",     "HOGAR", True,  10, False, "", {}),
        ("I18", "I1D",  880,  "Observaciones al capítulo Alimentación",                                         "TEXTO_LARGO", "HOGAR", False, 11, False, "", {"max_length": 1000}),
    ],
    # ── T. CONTROL ────────────────────────────────────────────────────────────
    "T": [],
    # ── B. DATOS BÁSICOS E IDENTIDAD ÉTNICA ───────────────────────────────────
    # Incluye preguntas étnicas ampliadas para comunidades en contexto urbano
    "B": [
        ("B1",  "NOMBRE_1",   13,   "Primer nombre",                                                             "TEXTO",          "PERSONA", True,  1,  True,  "RUV",                     {"max_length": 60}),
        ("B2",  "A2",         15,   "Segundo nombre",                                                            "TEXTO",          "PERSONA", False, 2,  True,  "RUV",                     {"max_length": 60}),
        ("B3",  "A6",         27,   "Fecha de nacimiento",                                                       "FECHA",          "PERSONA", True,  3,  True,  "RUV",                     {}),
        ("B4",  "B9",         14,   "¿Cuántos años cumplidos tiene?",                                            "NUMERICO",       "PERSONA", True,  4,  False, "",                        {"min": 0, "max": 120}),
        ("B5",  "B10",        1177, "Grupo etario",                                                              "LISTA",          "PERSONA", False, 5,  False, "",                        {}),
        ("B6",  "A3",         30,   "¿Qué tipo de documento de identificación tiene?",                           "LISTA",          "PERSONA", True,  6,  True,  "TABLA_CONFORMACION_HOGAR", {}),
        ("B7",  "A4",         32,   "¿Cuenta con el documento de identificación?",                               "BOOLEAN",        "PERSONA", True,  7,  False, "",                        {}),
        ("B8",  "A5",         31,   "Número de documento de identificación",                                     "TEXTO",          "PERSONA", True,  8,  True,  "RUV",                     {"max_length": 20}),
        ("B9",  "A8",         24,   "Sexo",                                                                      "LISTA",          "PERSONA", True,  9,  False, "",                        {}),
        ("B10", "A8A",        792,  "¿Cuál es su orientación sexual?",                                          "LISTA",          "PERSONA", False, 10, False, "",                        {}),
        ("B11", "B5",         274,  "¿Cuál es su identidad de género?",                                         "LISTA",          "PERSONA", False, 11, False, "",                        {}),
        ("B12", "I6",         88,   "¿Presenta alguna discapacidad?",                                            "BOOLEAN",        "PERSONA", True,  12, False, "",                        {}),
        ("B13", "I7A",        89,   "¿Qué tipo de discapacidad presenta?",                                       "LISTA_MULTIPLE",  "PERSONA", False, 13, False, "",                       {}),
        ("B14", "I7E",        400,  "¿Presenta diagnóstico de enfermedades ruinosas o de alto costo?",          "BOOLEAN",        "PERSONA", True,  14, False, "",                        {}),
        ("B15", "B2",         26,   "¿Se encuentra alguna mujer del hogar en estado de embarazo?",               "BOOLEAN",        "PERSONA", True,  15, False, "",                        {}),
        ("B16", "A9",         28,   "El parentesco frente al jefe del hogar es:",                                "LISTA",          "PERSONA", True,  16, True,  "TABLA_CONFORMACION_HOGAR", {}),
        ("B17", "A11",        289,  "¿La Unidad para las Víctimas incluyó a … en el RUPD/RUV?",                 "LISTA",          "PERSONA", True,  17, True,  "RUV",                     {}),
        # Identidad étnica — ampliada para perfil urbano
        ("B18", "A30",        867,  "¿Se encuentra habitando algún territorio colectivo en el área urbana?",     "BOOLEAN",        "PERSONA", True,  18, False, "",                        {}),
        ("B19", "A12",        290,  "¿A qué pueblo indígena pertenece?",                                        "TEXTO",          "PERSONA", False, 19, False, "",                        {"max_length": 150}),
        ("B20", "A13",        291,  "¿A qué comunidad indígena pertenece?",                                     "TEXTO",          "PERSONA", False, 20, False, "",                        {"max_length": 150}),
        ("B21", "A13A",       868,  "¿A qué cabildo urbano pertenece?",                                         "TEXTO",          "PERSONA", False, 21, False, "",                        {"max_length": 150}),
        ("B22", "A25",        1182, "¿Pertenece a un Consejo Comunitario?",                                      "BOOLEAN",        "PERSONA", False, 22, False, "",                        {}),
        ("B23", "A13B",       795,  "¿A qué consejo comunitario pertenece?",                                     "TEXTO",          "PERSONA", False, 23, False, "",                        {"max_length": 150}),
        ("B24", "A13C",       372,  "¿A qué Vitsa pertenece?",                                                  "LISTA",          "PERSONA", False, 24, False, "",                        {}),
        ("B25", "A13E",       373,  "¿A qué Kumpania pertenece?",                                               "LISTA",          "PERSONA", False, 25, False, "",                        {}),
        ("B26", "A17",        None, "¿Reconoce alguna autoridad propia?",                                        "BOOLEAN",        "PERSONA", False, 26, False, "",                        {}),
        ("B27", "A14",        292,  "¿Su comunidad o pueblo tiene un idioma propio?",                           "BOOLEAN",        "PERSONA", False, 27, False, "",                        {}),
        ("B28", "A15",        273,  "¿Habla el idioma propio de su comunidad o pueblo?",                        "LISTA",          "PERSONA", False, 28, False, "",                        {}),
        ("B29", "A20",        16,   "Estado de inclusión en el RUV",                                             "LISTA",          "PERSONA", True,  29, True,  "RUV",                     {}),
        ("B30", "A21",        17,   "Hecho victimizante principal",                                              "LISTA",          "PERSONA", True,  30, True,  "RUV",                     {}),
        ("B31", "A22",        18,   "Fecha de ocurrencia del hecho victimizante",                                "FECHA",          "PERSONA", True,  31, True,  "RUV",                     {}),
        ("B32", "A23A",       19,   "Municipio de ocurrencia del hecho victimizante",                            "COMBO_DINAMICO",  "PERSONA", True, 32, True,  "RUV",                    {}),
    ],
    # ── F. EDUCACIÓN ──────────────────────────────────────────────────────────
    "F": [
        ("F1", "G2",        None, "¿Actualmente está matriculado(a) en preescolar, escuela, colegio o universidad?", "BOOLEAN", "PERSONA", True,  1, True,  "MODELO_EDUCACION", {}),
        ("F2", "G15",       339,  "¿Sabe leer y escribir?",                                                          "BOOLEAN", "PERSONA", True,  2, False, "",                 {}),
        ("F3", "G4",        73,   "¿Por qué no asiste actualmente a un establecimiento educativo?",                  "LISTA",   "PERSONA", False, 3, False, "",                 {}),
        ("F4", "G7B_GRADO", 76,   "¿Cuál es el nivel educativo más alto alcanzado?",                                "LISTA",   "PERSONA", True,  4, False, "",                 {}),
    ],
    # ── G. SALUD ──────────────────────────────────────────────────────────────
    "G": [
        ("G1", "H8",   None, "¿Está afiliado a algún régimen de seguridad social en salud?",                          "LISTA",          "PERSONA", True,  1, True,  "MODELO_SALUD", {}),
        ("G2", "H9",   None, "¿La atención en salud está de acuerdo con sus usos y costumbres?",                      "LISTA",          "PERSONA", False, 2, False, "",             {}),
        ("G3", "H10",  None, "¿Qué hizo principalmente cuando tuvo problemas de salud?",                              "LISTA",          "PERSONA", True,  3, False, "",             {}),
        ("G4", "H11",  875,  "¿Accede a medicina tradicional de su comunidad en el entorno urbano?",                  "BOOLEAN",        "PERSONA", False, 4, False, "",             {}),
        ("G5", "H13",  807,  "¿Tiene diagnóstico de enfermedad crónica no transmisible?",                             "BOOLEAN",        "PERSONA", True,  5, False, "",             {}),
        ("G6", "H14",  808,  "¿Cuál enfermedad crónica?",                                                             "LISTA_MULTIPLE",  "PERSONA", False, 6, False, "",            {}),
    ],
    # ── H. REHABILITACIÓN ─────────────────────────────────────────────────────
    "H": [
        ("H1", "I8",   90,   "¿Necesita o requiere atención en salud mental?",                                        "BOOLEAN",        "PERSONA", True,  1, False, "", {}),
        ("H2", "I10A", 92,   "¿Ha recibido atención psicosocial?",                                                    "BOOLEAN",        "PERSONA", True,  2, False, "", {}),
        ("H3", "I11A", 93,   "¿Con qué frecuencia ha recibido atención psicosocial?",                                 "LISTA",          "PERSONA", False, 3, False, "", {}),
        ("H4", "I27",  811,  "¿Ha recibido medidas de rehabilitación física o psicológica?",                          "BOOLEAN",        "PERSONA", True,  4, False, "", {}),
        ("H5", "I28A", 812,  "¿Qué tipo de medidas de rehabilitación?",                                               "LISTA_MULTIPLE",  "PERSONA", False, 5, False, "", {}),
        ("H6", "I30",  892,  "Observaciones al capítulo Rehabilitación",                                              "TEXTO_LARGO",    "PERSONA", False, 6, False, "", {"max_length": 1000}),
    ],
    # ── JF. FUERZA DE TRABAJO ─────────────────────────────────────────────────
    "JF": [
        ("J1",  "L1",    119, "¿Cuál fue la actividad principal la semana pasada?",                                    "LISTA",    "PERSONA", True,  1,  False, "", {}),
        ("J2",  "L2",    None,"¿Realizó la semana pasada alguna actividad paga por una hora o más?",                   "BOOLEAN",  "PERSONA", True,  2,  False, "", {}),
        ("J5",  "L5",    123, "¿Buscó trabajo la semana pasada?",                                                      "BOOLEAN",  "PERSONA", True,  3,  False, "", {}),
        ("J7",  "L7",    125, "¿En las últimas 4 semanas hizo alguna diligencia para conseguir trabajo?",              "BOOLEAN",  "PERSONA", True,  4,  False, "", {}),
        ("J9",  "L9",    127, "¿Ha trabajado al menos 2 semanas en los últimos 12 meses?",                             "BOOLEAN",  "PERSONA", True,  5,  False, "", {}),
        ("J13", "L13",   131, "¿En qué ocupación trabajó la semana pasada?",                                           "TEXTO",    "PERSONA", False, 6,  False, "", {"max_length": 200}),
        ("J14", "L14",   132, "¿En qué actividad económica trabajó?",                                                  "LISTA",    "PERSONA", False, 7,  False, "", {}),
        ("J15", "L15",   133, "¿Cuántas horas trabajó la semana pasada?",                                              "NUMERICO", "PERSONA", False, 8,  False, "", {"min": 0, "max": 168}),
        ("J18", "L17",   None,"¿Cuánto ganó el mes pasado?",                                                           "NUMERICO", "PERSONA", False, 9,  False, "", {"min": 0}),
        ("J41", "M4C1A", 161, "Observaciones al capítulo Fuerza de Trabajo",                                           "TEXTO_LARGO", "PERSONA", False, 10, False, "", {"max_length": 1000}),
    ],
    # ── K. PERFIL SOCIOLABORAL ────────────────────────────────────────────────
    "K": [
        ("K3",  "PL2",   814, "¿Maneja algún idioma diferente al español?",                                            "BOOLEAN",       "PERSONA", True,  1,  False, "", {}),
        ("K5",  "PL4",   816, "¿Cuántos cargos u oficios ha ocupado en su vida laboral?",                             "NUMERICO",      "PERSONA", True,  2,  False, "", {"min": 0, "max": 50}),
        ("K15", "PL8A",  831, "¿Realiza actividades de economía propia o tradicional en el entorno urbano?",           "LISTA_MULTIPLE", "PERSONA", False, 3,  False, "", {}),
        ("K16", "PL25",  826, "¿Ha realizado alguna capacitación o formación laboral?",                                "BOOLEAN",       "PERSONA", True,  4,  False, "", {}),
        ("K21", "PL27",  1159,"¿Le gustaría recibir capacitación laboral?",                                            "BOOLEAN",       "PERSONA", True,  5,  False, "", {}),
        ("K23", "PL14",  833, "¿Alguna vez ha llevado a cabo una iniciativa de negocio propio?",                      "BOOLEAN",       "PERSONA", True,  6,  False, "", {}),
        ("K24", "PL15",  840, "¿Actualmente se encuentra activo su negocio?",                                          "BOOLEAN",       "PERSONA", False, 7,  False, "", {}),
        ("K39", "PL24",  849, "Observaciones al capítulo Perfil Sociolaboral",                                         "TEXTO_LARGO",   "PERSONA", False, 8,  False, "", {"max_length": 1000}),
    ],
}


class Command(BaseCommand):
    help = "Carga los 12 capítulos del Perfil Urbano Étnico V1"

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true",
                            help="Elimina los capítulos existentes antes de recargar")

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
                    defaults={"nombre": nombre, "orden": orden,
                              "nivel": nivel, "poblacion_objetivo": poblacion},
                )
                cap_objs[codigo] = cap
                self.stdout.write(
                    f"  Capítulo {codigo}: {nombre} [{'creado' if created else 'actualizado'}]"
                )

            total = 0
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
                            "no_pregunta": no_preg, "id_preg": id_preg,
                            "variable_bd": cod_ext,
                            "texto": texto, "tipo": tipo, "nivel": nivel,
                            "obligatoria": obligatoria, "orden": orden,
                            "es_precargada": es_precarg, "fuente_precarga": fuente,
                            "validaciones": validaciones, "activa": True,
                        },
                    )
                    total += 1

            self.stdout.write(self.style.SUCCESS(
                f"\nUrbano Étnico V1 cargado: {len(CAPITULOS)} capítulos, {total} preguntas."
            ))
