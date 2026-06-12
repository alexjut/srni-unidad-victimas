"""
Management command: cargar_buenaventura_v7

Carga los 17 capítulos y preguntas del Perfil Buenaventura V7
basado en el Diccionario oficial UARIV.

Capítulos exclusivos de Buenaventura:
  NA — Información Adicional (nivel HOGAR: IF24, IF25, IF23)
  NP — Información Adicional (nivel PERSONA: IF1–IF26)
  O  — Seguridad Jurídica del Territorio (ST1–ST13)

Uso:
    python manage.py cargar_buenaventura_v7
    python manage.py cargar_buenaventura_v7 --reset
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.formulario.models import (
    Instrumento, Capitulo, Pregunta, OpcionRespuesta,
    NivelPreguntaChoices, TipoPreguntaChoices, PoblacionObjetivoChoices,
)

INSTRUMENTO_PK = "22222222-0002-0002-0002-000000000002"  # Buenaventura V7

# ─────────────────────────────────────────────────────────────────────────────
# Capítulos: (codigo, nombre, orden, nivel, poblacion_objetivo)
# ─────────────────────────────────────────────────────────────────────────────
CAPITULOS = [
    # NIVEL HOGAR
    ("A",   "A. IDENTIFICACIÓN",                          1,   "HOGAR",   "TODOS_MIEMBROS"),
    ("C",   "C. VIVIENDA",                                2,   "HOGAR",   "TODOS_MIEMBROS"),
    ("D",   "D. RETORNO Y REUBICACIONES",                 3,   "HOGAR",   "TODOS_MIEMBROS"),
    ("FA",  "F. REUNIFICACIÓN FAMILIAR",                  4,   "HOGAR",   "TODOS_MIEMBROS"),
    ("JA",  "J. ALIMENTACIÓN",                            9,   "HOGAR",   "TODOS_MIEMBROS"),
    ("M",   "M. USO Y DISFRUTE DEL TERRITORIO",          13,   "HOGAR",   "TODOS_MIEMBROS"),
    ("NA",  "N. INFORMACIÓN ADICIONAL (HOGAR)",          14,   "HOGAR",   "TODOS_MIEMBROS"),
    ("O",   "O. SEGURIDAD JURÍDICA DEL TERRITORIO",      15,   "HOGAR",   "TODOS_MIEMBROS"),
    ("T",   "T. CONTROL",                                16,   "HOGAR",   "TODOS_MIEMBROS"),
    # NIVEL PERSONA
    ("B",   "B. DATOS BÁSICOS",                           5,   "PERSONA", "TODOS_MIEMBROS"),
    ("F",   "F. EDUCACIÓN",                               6,   "PERSONA", "VICTIMAS_RUV_3_ANOS_MAS"),
    ("G",   "G. SALUD",                                   7,   "PERSONA", "TODOS_MIEMBROS"),
    ("H",   "H. REHABILITACIÓN",                          8,   "PERSONA", "TODOS_MIEMBROS"),
    ("JF",  "J. FUERZA DE TRABAJO",                      10,   "PERSONA", "TODOS_MIEMBROS"),
    ("K",   "K. PERFIL SOCIOLABORAL",                    11,   "PERSONA", "TODOS_MIEMBROS"),
    ("L",   "L. FUERZA PÚBLICA",                         12,   "PERSONA", "TODOS_MIEMBROS"),
    ("NP",  "N. INFORMACIÓN ADICIONAL (PERSONA)",        17,   "PERSONA", "TODOS_MIEMBROS"),
]

# ─────────────────────────────────────────────────────────────────────────────
# Preguntas por capítulo
# Formato: (no_pregunta, codigo_externo, id_preg, texto, tipo, nivel,
#           obligatoria, orden, es_precargada, fuente_precarga, validaciones)
# ─────────────────────────────────────────────────────────────────────────────
PREGUNTAS = {
    "A": [
        ("A1",  "DT_ATENCION",  1161, "Dirección Territorial",                                              "COMBO_DINAMICO", "HOGAR", False, 1,  True,  "TABLA_USUARIOS", {}),
        ("A2",  "Z2",           1,    "Lugar de la Encuesta",                                               "COMBO_DINAMICO", "HOGAR", True,  2,  False, "",               {}),
        ("A3",  "Z3",           2,    "Método de recolección",                                              "LISTA",          "HOGAR", True,  3,  False, "",               {}),
        ("A4",  "Z4",           35,   "¿Cómo se autoreconoce culturalmente?",                               "LISTA",          "HOGAR", True,  4,  False, "",               {}),
        ("A5",  "Z5A",          3,    "Lugar de residencia (municipio)",                                    "COMBO_DINAMICO", "HOGAR", True,  5,  False, "",               {}),
        ("A6",  "Z6",           5,    "Zona de residencia",                                                 "LISTA",          "HOGAR", True,  6,  False, "",               {}),
        ("A7",  "Z7",           4,    "Barrio, centro poblado o vereda",                                    "TEXTO",          "HOGAR", False, 7,  False, "",               {"max_length": 200}),
        ("A8",  "VEREDA",       882,  "Ingrese el nombre de la vereda",                                     "TEXTO",          "HOGAR", False, 8,  False, "",               {"max_length": 150}),
        ("A9",  "Z8",           6,    "Dirección de la vivienda o nombre de la finca/predio",               "TEXTO",          "HOGAR", False, 9,  False, "",               {"max_length": 300}),
        ("A10", "Z9A",          7,    "Teléfono fijo",                                                      "NUMERICO",       "HOGAR", False, 10, False, "",               {"min": 1000000, "max": 9999999999}),
        ("A11", "Z9B",          8,    "Teléfono celular",                                                   "NUMERICO",       "HOGAR", False, 11, False, "",               {"min": 3000000000, "max": 3999999999}),
        ("A12", "Z9C",          788,  "Otro teléfono de contacto",                                          "NUMERICO",       "HOGAR", False, 12, False, "",               {}),
        ("A13", "Z10",          389,  "Correo electrónico",                                                 "TEXTO",          "HOGAR", False, 13, False, "",               {"regex": "^[^@]+@[^@]+\\.[^@]+$"}),
        ("A14", "Z11",          789,  "¿El lugar de correspondencia es el mismo de residencia?",            "BOOLEAN",        "HOGAR", True,  14, False, "",               {}),
        ("A15", "Z15",          1163, "Lugar de correspondencia (municipio)",                               "COMBO_DINAMICO", "HOGAR", False, 15, False, "",               {}),
        ("A16", "Z16",          1164, "Zona de correspondencia",                                            "LISTA",          "HOGAR", False, 16, False, "",               {}),
        ("A17", "Z17",          1165, "Barrio, centro poblado o vereda (correspondencia)",                  "TEXTO",          "HOGAR", False, 17, False, "",               {"max_length": 200}),
        ("A18", "Z18",          1166, "Ingrese el nombre de la vereda (correspondencia)",                   "TEXTO",          "HOGAR", False, 18, False, "",               {"max_length": 150}),
        ("A19", "Z12",          790,  "Dirección de correspondencia",                                       "TEXTO",          "HOGAR", False, 19, False, "",               {"max_length": 300}),
        ("A20", "T6",           10,   "Supervisor de la encuesta",                                          "TEXTO",          "HOGAR", True,  20, True,  "TABLA_USUARIOS", {}),
    ],
    "C": [
        ("C1",  "C1",    36,  "¿En qué tipo de vivienda habita el hogar?",                                          "LISTA",          "HOGAR", True,  1,  False, "", {}),
        ("C2",  "D5",    45,  "La vivienda ocupada por este hogar es:",                                             "LISTA",          "HOGAR", True,  2,  False, "", {}),
        ("C3",  "D7",    47,  "¿Qué tipo de documento soporte tiene?",                                             "LISTA",          "HOGAR", False, 3,  False, "", {}),
        ("C4",  "C2",    37,  "¿Cuál es el material predominante de las paredes exteriores?",                      "LISTA",          "HOGAR", True,  4,  False, "", {}),
        ("C5",  "C3",    38,  "¿Cuál es el material predominante de los pisos?",                                   "LISTA",          "HOGAR", True,  5,  False, "", {}),
        ("C6",  "C7",    275, "¿La vivienda es adecuada para su hogar según sus usos y costumbres?",               "BOOLEAN",        "HOGAR", True,  6,  False, "", {}),
        ("C7",  "D8A",   318, "¿Con cuáles servicios cuenta el hogar? Energía eléctrica",                          "BOOLEAN",        "HOGAR", True,  7,  False, "", {}),
        ("C8",  "D8B",   319, "¿Con cuáles servicios cuenta el hogar? Alcantarillado",                             "BOOLEAN",        "HOGAR", True,  8,  False, "", {}),
        ("C9",  "D8C",   320, "¿Con cuáles servicios cuenta el hogar? Acueducto",                                  "BOOLEAN",        "HOGAR", True,  9,  False, "", {}),
        ("C10", "D8D",   796, "¿Con cuáles servicios cuenta el hogar? Gas natural conectado a red pública",        "BOOLEAN",        "HOGAR", True,  10, False, "", {}),
        ("C11", "D8E",   797, "¿Con cuáles servicios cuenta el hogar? Recolección de basuras",                     "BOOLEAN",        "HOGAR", True,  11, False, "", {}),
        ("C12", "D8F",   871, "¿Su hogar tiene acceso a servicios públicos a través de vecinos?",                  "BOOLEAN",        "HOGAR", True,  12, False, "", {}),
        ("C13", "D10",   300, "¿De dónde proviene principalmente el agua que utilizan para beber?",                "LISTA",          "HOGAR", True,  13, False, "", {}),
        ("C14", "D13A",  49,  "¿Cómo eliminan principalmente las basuras en este hogar?",                         "LISTA_MULTIPLE",  "HOGAR", True,  14, False, "", {}),
        ("C15", "D14",   50,  "¿Cuál es el principal servicio sanitario con el que cuenta el hogar?",             "LISTA",          "HOGAR", True,  15, False, "", {}),
        ("C16", "D1",    42,  "Incluyendo sala-comedor, ¿de cuántos cuartos dispone este hogar?",                  "NUMERICO",       "HOGAR", True,  16, False, "", {"min": 1, "max": 30}),
        ("C17", "D2",    43,  "¿En cuántos de esos cuartos duermen las personas de este hogar?",                   "NUMERICO",       "HOGAR", True,  17, False, "", {"min": 1, "max": 30}),
        ("C18", "D6",    46,  "¿Cuánto cobraría usted por el arriendo del lugar que ocupa su hogar?",              "NUMERICO",       "HOGAR", True,  18, False, "", {"min": 0}),
        ("C19", "C5",    40,  "¿La vivienda se encuentra en zona de alto riesgo de desastre natural?",             "LISTA",          "HOGAR", True,  19, False, "", {}),
        ("C20", "C6A",   None,"¿La zona se ha visto afectada por factores naturales?",                             "LISTA_MULTIPLE",  "HOGAR", False, 20, False, "", {}),
        ("C21", "C17A",  None,"¿La zona se ha visto afectada por factores del conflicto armado?",                  "LISTA_MULTIPLE",  "HOGAR", False, 21, False, "", {}),
        ("C22", "C_OBSERVA", 252, "Observaciones al capítulo Vivienda",                                            "TEXTO_LARGO",    "HOGAR", False, 22, False, "", {"max_length": 1000}),
    ],
    "D": [
        ("D2",  "E1A",   798, "¿En la actualidad … respecto al derecho del retorno o reubicación?",            "LISTA",          "HOGAR", True,  1,  False, "", {}),
        ("D3",  "E1B",   799, "¿Cuál ha sido su decisión en relación con el derecho del retorno o reubicación?", "LISTA",        "HOGAR", True,  2,  False, "", {}),
        ("D4",  "E1",    62,  "¿Solicitó apoyo del Gobierno para retornar o reubicarse?",                       "BOOLEAN",        "HOGAR", True,  3,  False, "", {}),
        ("D5",  "E2",    63,  "¿En su proceso de retorno o reubicación lo acompañó alguna entidad del Estado?", "BOOLEAN",        "HOGAR", True,  4,  False, "", {}),
        ("D6",  "RR1",   800, "¿Cuál fue el departamento y municipio en el cuál se retornó o se reubicó?",      "COMBO_DINAMICO", "HOGAR", False, 5,  False, "", {}),
        ("D7",  "RR2",   883, "¿A qué Resguardo indígena se retornó o se reubicó?",                            "TEXTO",          "HOGAR", False, 6,  False, "", {"max_length": 150}),
        ("D8",  "RR3",   884, "¿A qué comunidad indígena se retornó o se reubicó?",                            "TEXTO",          "HOGAR", False, 7,  False, "", {"max_length": 150}),
        ("D9",  "RR4",   885, "¿A qué Territorio Colectivo de Comunidades Negras se retornó o se reubicó?",    "TEXTO",          "HOGAR", False, 8,  False, "", {"max_length": 200}),
        ("D10", "RR5A",  886, "¿A qué Kumpania se retornó o se reubicó?",                                      "LISTA",          "HOGAR", False, 9,  False, "", {}),
        ("D11", "RR6",   801, "¿A qué departamento y municipio quiere retornar o reubicarse?",                  "COMBO_DINAMICO", "HOGAR", False, 10, False, "", {}),
        ("D12", "RR7",   887, "¿A qué Resguardo indígena desea retornar o reubicarse?",                        "TEXTO",          "HOGAR", False, 11, False, "", {"max_length": 150}),
        ("D13", "RR8",   888, "¿A qué comunidad indígena desea retornar o reubicarse?",                        "TEXTO",          "HOGAR", False, 12, False, "", {"max_length": 150}),
        ("D14", "RR9",   889, "¿A qué Territorio Colectivo de Comunidades Negras desea retornar o reubicarse?", "TEXTO",         "HOGAR", False, 13, False, "", {"max_length": 200}),
        ("D15", "RR10A", 890, "¿A qué Kumpania desea retornar o reubicarse?",                                  "LISTA",          "HOGAR", False, 14, False, "", {}),
        ("D16", "E1C",   334, "¿Cuáles son las razones por las que residen en este municipio?",                 "LISTA_MULTIPLE", "HOGAR", False, 15, False, "", {}),
    ],
    "FA": [
        ("E1", "F1",       66,  "A causa del desplazamiento forzado, ¿algún miembro del hogar se vio obligado a separarse?", "BOOLEAN",     "HOGAR", True,  1, False, "", {}),
        ("E2", "F3",       68,  "¿El hogar solicitó apoyo del gobierno u otra entidad para la reunificación familiar?",       "BOOLEAN",     "HOGAR", False, 2, False, "", {}),
        ("E3", "F3A",      69,  "¿El hogar recibió el apoyo para la reunificación familiar?",                                 "BOOLEAN",     "HOGAR", False, 3, False, "", {}),
        ("E4", "F5",       803, "¿El hogar logró reunificarse?",                                                              "BOOLEAN",     "HOGAR", False, 4, False, "", {}),
        ("E5", "F4",       70,  "¿Por qué no ha solicitado apoyo para la reunificación familiar?",                            "LISTA",       "HOGAR", False, 5, False, "", {}),
        ("E6", "F6",       804, "¿Está interesado en iniciar un proceso de reunificación familiar?",                          "LISTA",       "HOGAR", False, 6, False, "", {}),
        ("E7", "F_OBSERVA", 255,"Observaciones al capítulo Reunificación Familiar",                                           "TEXTO_LARGO", "HOGAR", False, 7, False, "", {"max_length": 1000}),
    ],
    "JA": [
        ("I2",  "I1A1",  877,  "¿Generalmente cómo se aprovisiona el hogar de alimentos? — Donación",       "BOOLEAN",    "HOGAR", False, 1,  False, "", {}),
        ("I3",  "I1B",   878,  "¿Ha tenido dificultades para adquirir los alimentos en el último mes?",     "BOOLEAN",    "HOGAR", True,  2,  False, "", {}),
        ("I4",  "J1A",   None, "¿En los últimos 7 días consumió Leguminosas (fríjol, lentejas, etc.)?",     "BOOLEAN",    "HOGAR", True,  3,  False, "", {}),
        ("I5",  "J1B",   None, "¿En los últimos 7 días consumió Cereales (arroz, harina, avena)?",          "BOOLEAN",    "HOGAR", True,  4,  False, "", {}),
        ("I6",  "J1C",   None, "¿En los últimos 7 días consumió Tubérculos y plátanos?",                   "BOOLEAN",    "HOGAR", True,  5,  False, "", {}),
        ("I7",  "J1D",   None, "¿En los últimos 7 días consumió Verduras y hortalizas?",                   "BOOLEAN",    "HOGAR", True,  6,  False, "", {}),
        ("I8",  "J1E",   None, "¿En los últimos 7 días consumió Frutas?",                                   "BOOLEAN",    "HOGAR", True,  7,  False, "", {}),
        ("I9",  "J1F",   None, "¿En los últimos 7 días consumió Carnes (res, pollo, cerdo, cabra)?",       "BOOLEAN",    "HOGAR", True,  8,  False, "", {}),
        ("I10", "J1T",   1185, "¿En los últimos 7 días consumió Pescados y/o mariscos?",                   "BOOLEAN",    "HOGAR", True,  9,  False, "", {}),
        ("I11", "J1G",   None, "¿En los últimos 7 días consumió Otras carnes (patos, tortugas, etc.)?",    "BOOLEAN",    "HOGAR", False, 10, False, "", {}),
        ("I12", "J1H",   None, "¿En los últimos 7 días consumió Huevo?",                                   "BOOLEAN",    "HOGAR", True,  11, False, "", {}),
        ("I13", "J1J",   None, "¿En los últimos 7 días consumió Lácteos?",                                 "BOOLEAN",    "HOGAR", True,  12, False, "", {}),
        ("I14", "J1K",   None, "¿En los últimos 7 días consumió Grasas y aceites?",                        "BOOLEAN",    "HOGAR", True,  13, False, "", {}),
        ("I15", "J1L",   None, "¿En los últimos 7 días consumió Azúcar o panela?",                         "BOOLEAN",    "HOGAR", True,  14, False, "", {}),
        ("I16", "J1M",   None, "¿En los últimos 7 días consumió Bienestarina?",                            "BOOLEAN",    "HOGAR", False, 15, False, "", {}),
        ("I17", "J1N",   None, "¿En los últimos 7 días consumió Condimentos y especias?",                  "BOOLEAN",    "HOGAR", False, 16, False, "", {}),
        ("I18", "I1D",   880,  "Observaciones al capítulo Alimentación",                                    "TEXTO_LARGO","HOGAR", False, 17, False, "", {"max_length": 1000}),
    ],
    "M": [
        ("M1",  "AT1A",     1209, "¿Por cuáles de los siguientes motivos mantiene una relación urbano-rural?",             "LISTA_MULTIPLE", "HOGAR", True,  1, False, "", {}),
        ("M2",  "AT2",      900,  "¿A su hogar se le ha adjudicado materialmente terreno/lote/predio/habitación?",         "BOOLEAN",        "HOGAR", True,  2, False, "", {}),
        ("M3",  "AT3",      901,  "¿Este terreno o predio es parte de un resguardo o territorio colectivo?",               "LISTA",          "HOGAR", False, 3, False, "", {}),
        ("M4",  "AT4",      902,  "¿Cuál es la forma de tenencia de la tierra de este predio?",                            "LISTA",          "HOGAR", False, 4, False, "", {}),
        ("M5",  "AT5A",     904,  "¿Cuáles son las principales actividades que se realizan en el predio?",                 "LISTA_MULTIPLE", "HOGAR", False, 5, False, "", {}),
        ("M6",  "AT6A",     905,  "¿El principal destino de la producción final es?",                                      "LISTA",          "HOGAR", False, 6, False, "", {}),
        ("M7",  "AT7",      906,  "¿Cuál es la extensión del predio (hectáreas o m²)?",                                    "NUMERICO",       "HOGAR", False, 7, False, "", {"min": 0}),
        ("M8",  "AT8A",     907,  "¿En el predio existen factores de riesgo? (selección múltiple)",                        "LISTA_MULTIPLE", "HOGAR", False, 8, False, "", {}),
        ("M9",  "AT_OBSERVA", None, "Observaciones al capítulo Uso y Disfrute del Territorio",                             "TEXTO_LARGO",    "HOGAR", False, 9, False, "", {"max_length": 1000}),
    ],
    # ── N. INFORMACIÓN ADICIONAL — HOGAR ──────────────────────────────────────
    "NA": [
        ("IF24", "IF24", 1186, "¿En cada habitación destinada para dormir hay por lo menos una ventana?",                              "BOOLEAN",    "HOGAR", True,  1, False, "", {}),
        ("IF25", "IF25", 1187, "¿En los últimos 7 días algún miembro del hogar dejó de desayunar, almorzar o merendar por falta de dinero? ¿Con qué frecuencia?", "LISTA", "HOGAR", True, 2, False, "", {}),
        ("IF23", "IF23", 1211, "Observaciones Finales (Información Adicional)",                                                         "TEXTO_LARGO","HOGAR", False, 3, False, "", {"max_length": 1000}),
    ],
    # ── O. SEGURIDAD JURÍDICA DEL TERRITORIO ──────────────────────────────────
    "O": [
        ("ST1",  "ST1",  1423, "¿Cuáles son las características del predio/lote/terreno con el cual se mantiene una relación urbano-rural?",        "LISTA_MULTIPLE", "HOGAR", True,  1,  False, "", {}),
        ("ST2",  "ST2",  1424, "¿Están sus derechos a las tierras, territorios y recursos reconocidos y garantizados por el Gobierno?",             "LISTA",          "HOGAR", True,  2,  False, "", {}),
        ("ST3",  "ST3",  1425, "¿Tiene su hogar títulos de propiedad u otros acuerdos vinculantes que reconozcan la propiedad sobre el predio?",    "BOOLEAN",        "HOGAR", True,  3,  False, "", {}),
        ("ST4",  "ST4",  1426, "¿Tiene su hogar conflictos relacionados con tierras o recursos naturales sobre el predio?",                         "BOOLEAN",        "HOGAR", True,  4,  False, "", {}),
        ("ST5",  "ST5",  1427, "¿Su predio está siendo ocupado por terceros sin su consentimiento?",                                                "BOOLEAN",        "HOGAR", True,  5,  False, "", {}),
        ("ST6",  "ST6",  1428, "¿Ha tenido incidentes de asentamientos, usurpación de tierras o extracción de recursos sin su consentimiento libre, previo e informado?", "BOOLEAN", "HOGAR", True, 6, False, "", {}),
        ("ST7",  "ST7",  1429, "¿Ha tenido incidentes de desplazamiento o reubicación sin su consentimiento libre, previo e informado?",            "BOOLEAN",        "HOGAR", True,  7,  False, "", {}),
        ("ST8",  "ST8",  1430, "¿Ha establecido su hogar área/s de conservación en el predio?",                                                     "BOOLEAN",        "HOGAR", True,  8,  False, "", {}),
        ("ST9",  "ST9",  1431, "En caso afirmativo, ¿cuál es la superficie (hectáreas o m²) de tal área?",                                          "TEXTO",          "HOGAR", False, 9,  False, "", {"max_length": 100}),
        ("ST10", "ST10", 1432, "¿Ha declarado el Estado alguna parte del predio como parque o área protegida sin su consentimiento?",               "BOOLEAN",        "HOGAR", True,  10, False, "", {}),
        ("ST11", "ST11", 1433, "¿Ha habido actividades militares en el predio sin su consentimiento?",                                              "BOOLEAN",        "HOGAR", True,  11, False, "", {}),
        ("ST12", "ST12", 1434, "¿Ha habido actividades subversivas en el predio sin su consentimiento?",                                            "BOOLEAN",        "HOGAR", True,  12, False, "", {}),
        ("ST13", "ST13", 1437, "Observaciones Finales (Seguridad Jurídica del Territorio)",                                                          "TEXTO_LARGO",    "HOGAR", False, 13, False, "", {"max_length": 1000}),
    ],
    "T": [],
    # ── CAPÍTULOS PERSONA ──────────────────────────────────────────────────────
    "B": [
        ("B1",  "NOMBRE_1",   13,   "Primer nombre",                                                           "TEXTO",    "PERSONA", True,  1,  True,  "RUV",                     {"max_length": 60}),
        ("B2",  "A2",         15,   "Segundo nombre",                                                          "TEXTO",    "PERSONA", False, 2,  True,  "RUV",                     {"max_length": 60}),
        ("B3",  "A6",         27,   "Fecha de nacimiento",                                                     "FECHA",    "PERSONA", True,  3,  True,  "RUV",                     {}),
        ("B4",  "B9",         14,   "¿Cuántos años cumplidos tiene?",                                          "NUMERICO", "PERSONA", True,  4,  False, "",                        {"min": 0, "max": 120}),
        ("B5",  "B10",        1177, "Grupo etario",                                                            "LISTA",    "PERSONA", False, 5,  False, "",                        {}),
        ("B6",  "A3",         30,   "¿Qué tipo de documento de identificación tiene?",                         "LISTA",    "PERSONA", True,  6,  True,  "TABLA_CONFORMACION_HOGAR", {}),
        ("B7",  "A4",         32,   "¿Cuenta con el documento de identificación?",                             "BOOLEAN",  "PERSONA", True,  7,  False, "",                        {}),
        ("B8",  "A5",         31,   "Número de documento de identificación",                                   "TEXTO",    "PERSONA", True,  8,  True,  "RUV",                     {"max_length": 20}),
        ("B9",  "B11",        1169, "NUIP",                                                                    "TEXTO",    "PERSONA", False, 9,  True,  "RUV",                     {"max_length": 15}),
        ("B10", "A8",         24,   "Sexo",                                                                    "LISTA",    "PERSONA", True,  10, False, "",                        {}),
        ("B11", "A8A",        792,  "¿Cuál es su orientación sexual?",                                        "LISTA",    "PERSONA", False, 11, False, "",                        {}),
        ("B12", "B5",         274,  "¿Cuál es su identidad de género?",                                       "LISTA",    "PERSONA", False, 12, False, "",                        {}),
        ("B13", "B6",         33,   "¿Tiene resuelta su situación militar?",                                  "LISTA",    "PERSONA", False, 13, False, "",                        {}),
        ("B14", "B12",        1167, "¿Cuenta con libreta militar en físico?",                                  "BOOLEAN",  "PERSONA", False, 14, False, "",                        {}),
        ("B15", "B8",         793,  "¿Pertenece o ha pertenecido a la Fuerza Pública?",                       "BOOLEAN",  "PERSONA", True,  15, False, "",                        {}),
        ("B16", "I6",         88,   "¿Presenta alguna discapacidad?",                                         "BOOLEAN",  "PERSONA", True,  16, False, "",                        {}),
        ("B17", "I7A",        89,   "¿Qué tipo de discapacidad presenta?",                                    "LISTA_MULTIPLE", "PERSONA", False, 17, False, "",               {}),
        ("B18", "I7E",        400,  "¿Presenta diagnóstico de enfermedades ruinosas o de alto costo?",        "BOOLEAN",  "PERSONA", True,  18, False, "",                        {}),
        ("B19", "I13",        None, "¿Cuál enfermedad?",                                                       "LISTA_MULTIPLE", "PERSONA", False, 19, False, "",               {}),
        ("B20", "B13A",       865,  "Enfermedades de alto costo específicas",                                  "LISTA_MULTIPLE", "PERSONA", False, 20, False, "",               {}),
        ("B21", "B2",         26,   "¿Se encuentra alguna mujer del hogar en estado de embarazo?",             "BOOLEAN",  "PERSONA", True,  21, False, "",                        {}),
        ("B22", "B2A",        393,  "¿En la actualidad es madre lactante?",                                    "BOOLEAN",  "PERSONA", False, 22, False, "",                        {}),
        ("B23", "A9",         28,   "El parentesco frente al jefe del hogar es:",                              "LISTA",    "PERSONA", True,  23, True,  "TABLA_CONFORMACION_HOGAR", {}),
        ("B25", "A11",        289,  "¿La Unidad para las Víctimas incluyó a … en el RUPD/RUV?",               "LISTA",    "PERSONA", True,  24, True,  "RUV",                     {}),
        ("B26", "A30",        867,  "¿Se encuentra habitando algún territorio colectivo?",                     "BOOLEAN",  "PERSONA", True,  25, False, "",                        {}),
        ("B27", "B17",        866,  "¿En qué tipo de territorio se encuentra?",                                "LISTA",    "PERSONA", False, 26, False, "",                        {}),
        ("B28", "A12",        290,  "¿A qué pueblo indígena pertenece?",                                      "TEXTO",    "PERSONA", False, 27, False, "",                        {"max_length": 150}),
        ("B29", "A13",        291,  "¿A qué comunidad indígena pertenece?",                                   "TEXTO",    "PERSONA", False, 28, False, "",                        {"max_length": 150}),
        ("B30", "A13A",       868,  "¿A qué cabildo indígena pertenece?",                                     "TEXTO",    "PERSONA", False, 29, False, "",                        {"max_length": 150}),
        ("B31", "A25",        1182, "¿Pertenece a un Consejo Comunitario?",                                    "BOOLEAN",  "PERSONA", False, 30, False, "",                        {}),
        ("B32", "A13B",       795,  "¿A qué consejo comunitario pertenece?",                                   "TEXTO",    "PERSONA", False, 31, False, "",                        {"max_length": 150}),
        ("B33", "A13C",       372,  "¿A qué Vitsa pertenece?",                                                "LISTA",    "PERSONA", False, 32, False, "",                        {}),
        ("B34", "A13E",       373,  "¿A qué Kumpania pertenece?",                                             "LISTA",    "PERSONA", False, 33, False, "",                        {}),
        ("B35", "A17",        None, "¿Reconoce alguna autoridad propia?",                                      "BOOLEAN",  "PERSONA", False, 34, False, "",                        {}),
        ("B36", "A19",        296,  "¿Reconoce la autoridad del Resguardo?",                                   "BOOLEAN",  "PERSONA", False, 35, False, "",                        {}),
        ("B37", "A14",        292,  "¿Su comunidad o pueblo tiene un idioma propio?",                         "BOOLEAN",  "PERSONA", False, 36, False, "",                        {}),
        ("B38", "A15",        273,  "¿Habla el idioma propio de su comunidad o pueblo?",                      "LISTA",    "PERSONA", False, 37, False, "",                        {}),
        ("B39", "A16",        293,  "¿Escribe en el idioma propio?",                                          "LISTA",    "PERSONA", False, 38, False, "",                        {}),
        ("B40", "A16A",       869,  "¿Lee en el idioma propio?",                                              "LISTA",    "PERSONA", False, 39, False, "",                        {}),
        ("B41", "B18B",       1158, "¿El hogar tiene miembros inscritos en el ICBF?",                         "BOOLEAN",  "PERSONA", False, 40, False, "",                        {}),
        ("B42", "A20",        16,   "Estado de inclusión en el RUV",                                          "LISTA",    "PERSONA", True,  41, True,  "RUV",                     {}),
        ("B43", "A20A",       None, "¿Ha declarado nuevos hechos victimizantes?",                              "BOOLEAN",  "PERSONA", False, 42, False, "",                        {}),
        ("B44", "A26A",       1436, "¿Ha solicitado inscripción en el RUV anteriormente?",                    "BOOLEAN",  "PERSONA", False, 43, False, "",                        {}),
        ("B45", "A21",        17,   "Hecho victimizante principal",                                           "LISTA",    "PERSONA", True,  44, True,  "RUV",                     {}),
        ("B46", "A22",        18,   "Fecha de ocurrencia del hecho victimizante",                             "FECHA",    "PERSONA", True,  45, True,  "RUV",                     {}),
        ("B47", "A23A",       19,   "Municipio de ocurrencia del hecho victimizante",                         "COMBO_DINAMICO", "PERSONA", True, 46, True, "RUV",               {}),
    ],
    "F": [
        ("F1", "G2",         None, "¿Actualmente está matriculado(a) en preescolar, escuela, colegio o universidad?", "BOOLEAN", "PERSONA", True,  1, True,  "MODELO_EDUCACION", {}),
        ("F2", "G15",        339,  "¿Sabe leer y escribir?",                                                         "BOOLEAN", "PERSONA", True,  2, False, "",                  {}),
        ("F3", "G16",        805,  "¿Sabe leer y escribir en su idioma propio?",                                     "BOOLEAN", "PERSONA", False, 3, False, "",                  {}),
        ("F4", "G11",        None, "¿Recibe enseñanza sobre prácticas de su grupo étnico?",                          "BOOLEAN", "PERSONA", False, 4, False, "",                  {}),
        ("F5", "G17",        873,  "¿Asiste a clases de idioma propio?",                                             "BOOLEAN", "PERSONA", False, 5, False, "",                  {}),
        ("F6", "G4",         73,   "¿Por qué no asiste actualmente a un establecimiento educativo?",                 "LISTA",   "PERSONA", False, 6, False, "",                  {}),
        ("F7", "G7B_GRADO",  76,   "¿Cuál es el nivel educativo más alto alcanzado?",                               "LISTA",   "PERSONA", True,  7, False, "",                  {}),
        ("F8", "G18",        None, "¿Completó el último nivel de básica primaria?",                                  "BOOLEAN", "PERSONA", False, 8, False, "",                  {}),
    ],
    "G": [
        ("G1", "H8",   None, "¿Está afiliado a algún régimen de seguridad social en salud?",                "LISTA",   "PERSONA", True,  1, True,  "MODELO_SALUD", {}),
        ("G2", "H9",   None, "¿La atención en salud está de acuerdo con sus usos y costumbres?",           "LISTA",   "PERSONA", False, 2, False, "",             {}),
        ("G3", "H10",  None, "¿Qué hizo principalmente cuando tuvo problemas de salud?",                   "LISTA",   "PERSONA", True,  3, False, "",             {}),
        ("G4", "H11",  875,  "¿Accede a medicina tradicional de su comunidad?",                            "BOOLEAN", "PERSONA", False, 4, False, "",             {}),
        ("G5", "H12A", 876,  "¿Cuál es el motivo principal por el que no accede a medicina tradicional?",  "LISTA",   "PERSONA", False, 5, False, "",             {}),
        ("G6", "H13",  807,  "¿Tiene diagnóstico de enfermedad crónica no transmisible?",                  "BOOLEAN", "PERSONA", True,  6, False, "",             {}),
        ("G7", "H14",  808,  "¿Cuál enfermedad crónica?",                                                   "LISTA_MULTIPLE", "PERSONA", False, 7, False, "",    {}),
    ],
    "H": [
        ("H1", "I8",   90,   "¿Necesita o requiere atención en salud mental?",                              "BOOLEAN",        "PERSONA", True,  1, False, "", {}),
        ("H2", "I10A", 92,   "¿Ha recibido atención psicosocial?",                                          "BOOLEAN",        "PERSONA", True,  2, False, "", {}),
        ("H3", "I11A", 93,   "¿Con qué frecuencia ha recibido atención psicosocial?",                      "LISTA",          "PERSONA", False, 3, False, "", {}),
        ("H4", "I25B", 809,  "¿Qué institución le brindó atención psicosocial?",                           "LISTA",          "PERSONA", False, 4, False, "", {}),
        ("H5", "I26",  None, "¿Considera que la atención recibida ha contribuido a su recuperación?",      "LISTA",          "PERSONA", False, 5, False, "", {}),
        ("H6", "I27",  811,  "¿Ha recibido medidas de rehabilitación física o psicológica?",               "BOOLEAN",        "PERSONA", True,  6, False, "", {}),
        ("H7", "I28A", 812,  "¿Qué tipo de medidas de rehabilitación?",                                    "LISTA_MULTIPLE", "PERSONA", False, 7, False, "", {}),
        ("H8", "I29",  891,  "¿Accede a mecanismos de medicina tradicional para su recuperación?",         "BOOLEAN",        "PERSONA", False, 8, False, "", {}),
        ("H9", "I30",  892,  "Observaciones al capítulo Rehabilitación",                                    "TEXTO_LARGO",    "PERSONA", False, 9, False, "", {"max_length": 1000}),
    ],
    "JF": [
        ("J1",  "L1",    119, "¿Cuál fue la actividad principal la semana pasada?",                          "LISTA",    "PERSONA", True,  1,  False, "", {}),
        ("J2",  "L2",    None,"¿Realizó la semana pasada alguna actividad paga por una hora o más?",        "BOOLEAN",  "PERSONA", True,  2,  False, "", {}),
        ("J3",  "L3",    None,"¿Tenía algún trabajo o negocio que genera ingresos aunque no trabajó?",      "BOOLEAN",  "PERSONA", True,  3,  False, "", {}),
        ("J4",  "L4",    122, "¿Trabajó en negocio familiar sin remuneración la semana pasada?",             "BOOLEAN",  "PERSONA", True,  4,  False, "", {}),
        ("J5",  "L5",    123, "¿Buscó trabajo la semana pasada?",                                            "BOOLEAN",  "PERSONA", True,  5,  False, "", {}),
        ("J6",  "L6",    124, "¿Por qué no buscó trabajo activamente?",                                     "LISTA",    "PERSONA", False, 6,  False, "", {}),
        ("J7",  "L7",    125, "¿En las últimas 4 semanas hizo alguna diligencia para conseguir trabajo?",   "BOOLEAN",  "PERSONA", True,  7,  False, "", {}),
        ("J8",  "L8",    None,"¿Por qué motivo principal no hizo diligencias para buscar trabajo?",         "LISTA",    "PERSONA", False, 8,  False, "", {}),
        ("J9",  "L9",    127, "¿Ha trabajado al menos 2 semanas en los últimos 12 meses?",                  "BOOLEAN",  "PERSONA", True,  9,  False, "", {}),
        ("J10", "L10",   None,"¿Ha hecho alguna diligencia para conseguir trabajo en el último mes?",       "BOOLEAN",  "PERSONA", True,  10, False, "", {}),
        ("J11", "L11",   129, "¿Estaría disponible para trabajar la semana pasada si hubiera habido?",      "BOOLEAN",  "PERSONA", True,  11, False, "", {}),
        ("J12", "L12",   130, "¿Cuántos meses hace que dejó de buscar trabajo?",                            "NUMERICO", "PERSONA", False, 12, False, "", {"min": 0, "max": 600}),
        ("J13", "L13",   131, "¿En qué ocupación trabajó la semana pasada?",                                "TEXTO",    "PERSONA", False, 13, False, "", {"max_length": 200}),
        ("J14", "L14",   132, "¿En qué actividad económica trabajó?",                                       "LISTA",    "PERSONA", False, 14, False, "", {}),
        ("J15", "L15",   133, "¿Cuántas horas trabajó la semana pasada?",                                   "NUMERICO", "PERSONA", False, 15, False, "", {"min": 0, "max": 168}),
        ("J16", "L28",   893, "¿Desea trabajar más horas de las que trabaja actualmente?",                  "BOOLEAN",  "PERSONA", False, 16, False, "", {}),
        ("J17", "L16",   134, "¿Tiene contrato de trabajo?",                                                "LISTA",    "PERSONA", False, 17, False, "", {}),
        ("J18", "L17",   None,"¿Cuánto ganó el mes pasado (salario, honorarios)?",                          "NUMERICO", "PERSONA", False, 18, False, "", {"min": 0}),
        ("J19", "L18",   137, "¿Cuánto ganó el mes pasado por trabajo independiente?",                      "NUMERICO", "PERSONA", False, 19, False, "", {"min": 0}),
        ("J20", "L19",   138, "¿Cuánto ganó el mes pasado en especie?",                                     "NUMERICO", "PERSONA", False, 20, False, "", {"min": 0}),
        ("J21", "L20",   None,"¿Recibió alimentos como parte de pago?",                                     "BOOLEAN",  "PERSONA", False, 21, False, "", {}),
        ("J22", "L21",   None,"¿Recibió vivienda como parte de pago?",                                      "BOOLEAN",  "PERSONA", False, 22, False, "", {}),
        ("J23", "L22",   141, "¿Recibió pensión de jubilación?",                                            "BOOLEAN",  "PERSONA", False, 23, False, "", {}),
        ("J24", "L22B",  142, "¿Recibió pensión de invalidez?",                                             "BOOLEAN",  "PERSONA", False, 24, False, "", {}),
        ("J25", "L22C",  143, "¿Recibió pensión de sobreviviente?",                                         "BOOLEAN",  "PERSONA", False, 25, False, "", {}),
        ("J26", "L22D",  144, "¿Recibió pensión de vejez?",                                                 "BOOLEAN",  "PERSONA", False, 26, False, "", {}),
        ("J27", "L22E",  145, "¿Recibió pensión de sustitución pensional?",                                 "BOOLEAN",  "PERSONA", False, 27, False, "", {}),
        ("J28", "L23",   146, "¿Recibió cesantías?",                                                        "BOOLEAN",  "PERSONA", False, 28, False, "", {}),
        ("J29", "L24",   147, "¿Recibió pagos por arriendos o pensiones?",                                  "BOOLEAN",  "PERSONA", False, 29, False, "", {}),
        ("J30", "M1",    None,"¿Recibió pagos por arriendos de inmuebles o vehículos?",                     "BOOLEAN",  "PERSONA", False, 30, False, "", {}),
        ("J31", "M2A",   None,"¿Recibió pensión de invalidez por accidente?",                               "BOOLEAN",  "PERSONA", False, 31, False, "", {}),
        ("J32", "M2B",   None,"¿Recibió pensión de invalidez?",                                             "BOOLEAN",  "PERSONA", False, 32, False, "", {}),
        ("J33", "M2C",   None,"¿Recibió pensión alimentaria por divorcio o separación?",                    "BOOLEAN",  "PERSONA", False, 33, False, "", {}),
        ("J34", "M5",    None,"¿Recibió dinero de otros hogares, personas o instituciones?",                "BOOLEAN",  "PERSONA", False, 34, False, "", {}),
        ("J35", "M6",    894, "¿Recibió remesas del exterior?",                                             "BOOLEAN",  "PERSONA", False, 35, False, "", {}),
        ("J36", "M7",    895, "¿Cuánto recibió por remesas el mes pasado?",                                 "NUMERICO", "PERSONA", False, 36, False, "", {"min": 0}),
        ("J37", "M8",    896, "¿Recibió subsidios del Estado?",                                             "BOOLEAN",  "PERSONA", False, 37, False, "", {}),
        ("J38", "M9",    897, "¿Recibió intereses de cuentas o depósitos de ahorro?",                      "BOOLEAN",  "PERSONA", False, 38, False, "", {}),
        ("J39", "M10",   898, "¿Recibió dividendos de acciones?",                                           "BOOLEAN",  "PERSONA", False, 39, False, "", {}),
        ("J40", "M11",   None,"¿Recibió indemnizaciones por seguros?",                                      "BOOLEAN",  "PERSONA", False, 40, False, "", {}),
        ("J41", "M4C1A", 161, "Observaciones al capítulo Fuerza de Trabajo",                                "TEXTO_LARGO", "PERSONA", False, 41, False, "", {"max_length": 1000}),
    ],
    "K": [
        ("K2",  "PL1",   813, "¿Considera útil su formación académica para el mercado laboral?",            "LISTA",    "PERSONA", True,  1,  False, "", {}),
        ("K3",  "PL2",   814, "¿Maneja algún idioma diferente al español?",                                 "BOOLEAN",  "PERSONA", True,  2,  False, "", {}),
        ("K4",  "PL3",   815, "¿Cuál es su nivel en ese segundo idioma?",                                  "LISTA",    "PERSONA", False, 3,  False, "", {}),
        ("K5",  "PL4",   816, "¿Cuántos cargos u oficios ha ocupado en su vida laboral?",                  "NUMERICO", "PERSONA", True,  4,  False, "", {"min": 0, "max": 50}),
        ("K6",  "PL5A",  817, "¿En qué área laboral tiene más experiencia? — Primera opción",              "LISTA",    "PERSONA", False, 5,  False, "", {}),
        ("K7",  "PL5B",  818, "¿En qué área laboral tiene más experiencia? — Segunda opción",              "LISTA",    "PERSONA", False, 6,  False, "", {}),
        ("K8",  "PL5C",  819, "¿En qué área laboral tiene más experiencia? — Tercera opción",              "LISTA",    "PERSONA", False, 7,  False, "", {}),
        ("K9",  "PL6A",  820, "¿Tiene alguna habilidad artística o artesanal? — Primera opción",           "LISTA",    "PERSONA", False, 8,  False, "", {}),
        ("K10", "PL6B",  821, "¿Tiene alguna habilidad artística o artesanal? — Segunda opción",           "LISTA",    "PERSONA", False, 9,  False, "", {}),
        ("K11", "PL6C",  822, "¿Tiene alguna habilidad artística o artesanal? — Tercera opción",           "LISTA",    "PERSONA", False, 10, False, "", {}),
        ("K12", "PL7A",  823, "¿Tiene habilidades en actividades tradicionales? — Primera opción",          "LISTA",    "PERSONA", False, 11, False, "", {}),
        ("K13", "PL7B",  824, "¿Tiene habilidades en actividades tradicionales? — Segunda opción",          "LISTA",    "PERSONA", False, 12, False, "", {}),
        ("K14", "PL7C",  825, "¿Tiene habilidades en actividades tradicionales? — Tercera opción",          "LISTA",    "PERSONA", False, 13, False, "", {}),
        ("K15", "PL8A",  831, "¿Realiza actividades de economía propia o tradicional?",                    "LISTA_MULTIPLE", "PERSONA", False, 14, False, "", {}),
        ("K16", "PL25",  826, "¿Ha realizado alguna capacitación o formación laboral?",                    "BOOLEAN",  "PERSONA", True,  15, False, "", {}),
        ("K17", "PL9A",  827, "¿En qué tipo de formación laboral?",                                        "LISTA",    "PERSONA", False, 16, False, "", {}),
        ("K18", "PL10A", 828, "¿Cuántas capacitaciones ha realizado?",                                     "NUMERICO", "PERSONA", False, 17, False, "", {"min": 0, "max": 50}),
        ("K19", "PL11A", 829, "¿Cuánto tiempo duró la última capacitación?",                               "LISTA",    "PERSONA", False, 18, False, "", {}),
        ("K20", "PL12A", 830, "¿La capacitación fue con enfoque diferencial étnico?",                      "BOOLEAN",  "PERSONA", False, 19, False, "", {}),
        ("K21", "PL27",  1159,"¿Le gustaría recibir capacitación laboral?",                                 "BOOLEAN",  "PERSONA", True,  20, False, "", {}),
        ("K22", "PL13A", 832, "¿En qué área le gustaría capacitarse?",                                     "LISTA",    "PERSONA", False, 21, False, "", {}),
        ("K23", "PL14",  833, "¿Alguna vez ha llevado a cabo una iniciativa de negocio propio?",            "BOOLEAN",  "PERSONA", True,  22, False, "", {}),
        ("K24", "PL15",  840, "¿Actualmente se encuentra activo su negocio?",                              "BOOLEAN",  "PERSONA", False, 23, False, "", {}),
        ("K25", "PL16",  834, "¿Cuánto tiempo ha estado activo su negocio?",                               "LISTA",    "PERSONA", False, 24, False, "", {}),
        ("K26", "PL17",  835, "¿Hace parte de una organización productiva?",                               "BOOLEAN",  "PERSONA", False, 25, False, "", {}),
        ("K27", "PL18",  836, "¿Qué tipo de organización productiva?",                                     "LISTA",    "PERSONA", False, 26, False, "", {}),
        ("K28", "PL19",  837, "¿Cuántas personas emplea su negocio?",                                      "NUMERICO", "PERSONA", False, 27, False, "", {"min": 0, "max": 100}),
        ("K29", "PL20",  838, "¿El negocio tiene registro mercantil?",                                     "BOOLEAN",  "PERSONA", False, 28, False, "", {}),
        ("K30", "PL26A", 839, "¿El negocio tiene enfoque étnico propio?",                                  "BOOLEAN",  "PERSONA", False, 29, False, "", {}),
        ("K31", "PL28",  841, "¿Dónde se encuentra ubicado su negocio?",                                   "COMBO_DINAMICO", "PERSONA", False, 30, False, "", {}),
        ("K32", "PL29",  842, "¿En qué sector económico opera su negocio?",                                "LISTA",    "PERSONA", False, 31, False, "", {}),
        ("K33", "PL21A", 843, "¿Cuáles son los principales obstáculos para su negocio?",                   "LISTA_MULTIPLE", "PERSONA", False, 32, False, "", {}),
        ("K34", "PL22",  None,"¿Qué lo motivó a crear su negocio?",                                        "LISTA_MULTIPLE", "PERSONA", False, 33, False, "", {}),
        ("K35", "PL23",  845, "¿Ha solicitado crédito para su negocio?",                                   "BOOLEAN",  "PERSONA", False, 34, False, "", {}),
        ("K36", "PL23B", 846, "¿Le fue aprobado el crédito?",                                              "BOOLEAN",  "PERSONA", False, 35, False, "", {}),
        ("K37", "PL23D", 847, "¿A qué entidad le solicitó el crédito?",                                    "LISTA",    "PERSONA", False, 36, False, "", {}),
        ("K38", "PL23E", 848, "¿Por qué no solicitó crédito?",                                             "LISTA",    "PERSONA", False, 37, False, "", {}),
        ("K39", "PL24",  849, "Observaciones al capítulo Perfil Sociolaboral",                              "TEXTO_LARGO", "PERSONA", False, 38, False, "", {"max_length": 1000}),
    ],
    "L": [
        ("L1",  "FP1",  851, "¿Pertenece o perteneció a la Fuerza Pública en el momento del hecho?",     "BOOLEAN",        "PERSONA", True,  1,  False, "", {}),
        ("L2",  "FP2",  852, "¿A qué institución pertenecía?",                                           "LISTA",          "PERSONA", False, 2,  False, "", {}),
        ("L3",  "FP3",  853, "¿Cuál era su rango o grado?",                                              "LISTA",          "PERSONA", False, 3,  False, "", {}),
        ("L4",  "FP4",  854, "¿Estaba en servicio activo en el momento del hecho?",                      "BOOLEAN",        "PERSONA", False, 4,  False, "", {}),
        ("L5",  "FP5",  855, "¿El hecho ocurrió en desarrollo de operaciones militares?",                "BOOLEAN",        "PERSONA", False, 5,  False, "", {}),
        ("L6",  "FP6",  856, "¿Fue reconocido como víctima por la Fuerza Pública?",                     "BOOLEAN",        "PERSONA", False, 6,  False, "", {}),
        ("L7",  "FP7",  857, "¿Ha recibido alguna reparación por parte de la Fuerza Pública?",          "BOOLEAN",        "PERSONA", False, 7,  False, "", {}),
        ("L8",  "FP8",  858, "¿En qué consistió la reparación recibida?",                                "LISTA_MULTIPLE", "PERSONA", False, 8,  False, "", {}),
        ("L9",  "FP9",  859, "¿Ha presentado demanda ante el Tribunal Administrativo?",                  "BOOLEAN",        "PERSONA", False, 9,  False, "", {}),
        ("L10", "FP10", 860, "Observaciones al capítulo Fuerza Pública",                                 "TEXTO_LARGO",    "PERSONA", False, 10, False, "", {"max_length": 1000}),
    ],
    # ── N. INFORMACIÓN ADICIONAL — PERSONA ────────────────────────────────────
    "NP": [
        ("IF1",  "IF1",  1188, "Indique el tipo de remedios caseros / forma en que se automedicó",                         "LISTA_MULTIPLE", "PERSONA", False, 1,  False, "", {}),
        ("IF2A", "IF2A", 1189, "¿A cuál de los siguientes programas de promoción en salud asistió en los últimos 12 meses?","LISTA_MULTIPLE", "PERSONA", False, 2,  False, "", {}),
        ("IF3",  "IF3",  1190, "¿Por qué no asistió a los programas de promoción en salud?",                               "LISTA",          "PERSONA", False, 3,  False, "", {}),
        ("IF4A", "IF4A", 1191, "¿Qué métodos conoce o ha oído hablar para evitar un embarazo?",                            "LISTA_MULTIPLE", "PERSONA", False, 4,  False, "", {}),
        ("IF5A", "IF5A", 1192, "¿Cuáles métodos de planificación familiar utiliza?",                                       "LISTA_MULTIPLE", "PERSONA", False, 5,  False, "", {}),
        ("IF6",  "IF6",  1193, "¿Conoce métodos para la prevención de enfermedades de transmisión sexual?",                "BOOLEAN",        "PERSONA", False, 6,  False, "", {}),
        ("IF7",  "IF7",  1194, "¿Hubo algún parto en el hogar en los últimos 12 meses?",                                   "BOOLEAN",        "PERSONA", False, 7,  False, "", {}),
        ("IF8",  "IF8",  1195, "¿Dónde atendieron el parto?",                                                              "LISTA",          "PERSONA", False, 8,  False, "", {}),
        ("IF9",  "IF9",  1196, "¿Cuántas veces ha asistido a controles prenatales?",                                       "NUMERICO",       "PERSONA", False, 9,  False, "", {"min": 0, "max": 50}),
        ("IF10A","IF10A",1197, "¿Qué complementos nutricionales le recetó el médico?",                                     "LISTA_MULTIPLE", "PERSONA", False, 10, False, "", {}),
        ("IF11", "IF11", 1422, "¿Usa complementos nutricionales tradicionales o propios de su grupo étnico?",              "BOOLEAN",        "PERSONA", False, 11, False, "", {}),
        ("IF12", "IF12", 1198, "¿Está consumiendo la cantidad de suplemento formulada por su médico?",                     "BOOLEAN",        "PERSONA", False, 12, False, "", {}),
        ("IF13", "IF13", 1199, "¿Por qué no está consumiendo la cantidad de suplemento formulada?",                        "LISTA",          "PERSONA", False, 13, False, "", {}),
        ("IF14", "IF14", 1200, "¿Cada cuánto se realiza la citología vaginal?",                                            "LISTA",          "PERSONA", False, 14, False, "", {}),
        ("IF15", "IF15", 1201, "¿Cuándo fue la última vez que se hizo una citología vaginal?",                             "LISTA",          "PERSONA", False, 15, False, "", {}),
        ("IF16", "IF16", 1202, "¿Cuál es la principal razón por la que no se ha hecho la citología?",                     "LISTA",          "PERSONA", False, 16, False, "", {}),
        ("IF17", "IF17", 1203, "¿Se ha realizado el auto examen de mama? ¿Cuántas veces al año?",                         "LISTA",          "PERSONA", False, 17, False, "", {}),
        ("IF18", "IF18", 1204, "¿Se ha realizado el examen de próstata? ¿Cuántas veces al año?",                          "LISTA",          "PERSONA", False, 18, False, "", {}),
        ("IF19", "IF19", 1205, "¿Considera que la educación que le brindan es la adecuada para enfrentar el mercado?",    "BOOLEAN",        "PERSONA", False, 19, False, "", {}),
        ("IF20", "IF20", 1206, "¿Considera que hay oportunidades para que la población víctima se integre laboralmente?", "BOOLEAN",        "PERSONA", False, 20, False, "", {}),
        ("IF21", "IF21", 1207, "¿Por qué no considera que hay oportunidades?",                                             "LISTA",          "PERSONA", False, 21, False, "", {}),
        ("IF22", "IF22", 1208, "¿Cuál es el estado de su documento de identidad en este momento?",                        "LISTA",          "PERSONA", False, 22, False, "", {}),
        ("IF26", "IF26", 1438, "¿Qué diagnóstico de enfermedad presenta?",                                                 "LISTA_MULTIPLE", "PERSONA", False, 23, False, "", {}),
    ],
}


class Command(BaseCommand):
    help = "Carga los 17 capítulos y preguntas del Perfil Buenaventura V7"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Elimina los capítulos existentes antes de recargar",
        )

    def handle(self, *args, **options):
        try:
            instrumento = Instrumento.objects.get(pk=INSTRUMENTO_PK)
        except Instrumento.DoesNotExist:
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
                    f"\nBuenaventura V7 cargado: "
                    f"{len(CAPITULOS)} capítulos, {total_preguntas} preguntas."
                )
            )
