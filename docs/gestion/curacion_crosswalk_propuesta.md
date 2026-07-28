# Propuesta de crosswalk: opciones SICAV vs catalogo Oracle (RNIENTREVISTA)

**Estado:** PROPUESTA para revision. No modifica ningun fixture ni codigo.  
**Fecha:** 2026-07-22  
**Autoridad:** Manual oficial 11-MU (Territorial y Etnicos) y 14-MU (Asistencia). Ante duda, MANDA EL MANUAL.  
**Insumos:** `curacion_opciones_sicav_vs_oracle.tsv` (178 divergencias, 116 preguntas) + `respuestas_oracle.json` (catalogo con id y escribibilidad).

## 1. Resumen por categoria

| Categoria | Filas | Que significa |
|---|---:|---|
| TRIVIAL | 148 | Misma opcion; difiere solo por formato/typo/mayusculas/acento/sub-campo. Se propone la redaccion del manual y el res_idrespuesta escribible. |
| SUSTANTIVA | 16 | Diferencia de contenido (calificador que una parte omite). Confirmado con el manual que son la MISMA opcion; se alinea la etiqueta al manual. |
| MAPEO_DUDOSO | 12 | La opcion SICAV no corresponde a ninguna opcion de esa pregunta Oracle (posible id_preg mal mapeado o campo mal ubicado). NO se fuerza; investigar/escalar. |
| NO_EN_MANUAL | 2 | El manual no cubre el caso. Va a Oscar. |
| **TOTAL** | **178** | |

### Notas transversales

- **Sub-campos numericos** ('Valor (1 a 7)' en consumo de alimentos; 'Valor' en ingresos; 'Cual'/'CUAL' sueltos): NO son opciones categoricas independientes. Son el payload (dias 1-7, valor en pesos, texto libre) que se almacena junto con la opcion 'Si'. Se mapean al MISMO res_idrespuesta que 'Si'. Se listan como TRIVIAL con esa nota para que quien cure el fixture no cree una opcion espuria.
- **Escribibilidad:** todos los res_idrespuesta propuestos son escribibles en Oracle salvo que se indique. Se verifico contra `respuestas_oracle.json`. Caso relevante: en pre400 'Porque nacio asi' (res 1396) NO es escribible, pero ninguna divergencia de esta lista mapea alli.
- **Paginas del manual:** '—' = grupo de sub-campos boolean/numericos o pregunta de metadato sin tabla de opciones que citar. 'ASIS (...)' = pregunta del perfil Asistencia cuya pagina exacta no se fijo; el texto entre parentesis identifica la pregunta.

## 2.1 TRIVIAL (148)

| pre_id | cod SICAV | opcion SICAV actual | etiqueta propuesta (manual) | res_id Oracle | pagina manual | nota |
|---|---|---|---|---|---|---|
| 2 | Z3 | Otro | Otro, Cuál? | 5 | TERR p43 | Formato. |
| 2 | Perfil_tel | Telefónica | Entrevista Telefónica | 3 | TERR p43 | SICAV abrevia; misma opcion. |
| 19 | A23A | Otra | Otra, ¿cuál? | 38 | TERR p50 | Formato. |
| 26 | B2 | Sí, ¿Cuántas? | Sí, ¿Cuántas semanas? | 76 | TERR p56 | Oracle typo 'Cuantas'; misma opcion (embarazo -> semanas). SICAV omite 'semanas'. |
| 36 | C1 | Otra vivienda  (carpa, vagón, cueva, refugio natural,albergue, embarcación, campamento, ... | Otra vivienda ( carpa, vagón,  cueva, refugio natural,albergue, embarcación,... | 1064 | TERR p65 | Typos SICAV ('Asentameinto'); misma opcion. |
| 45 | D5 | En Usufructo** | Usufructo | 164 | TERR p67 | Prefijo 'En' y '**' de SICAV; misma opcion. |
| 49 | D13A | la queman o entierran | Las queman o entierran | 179 | TERR p73 | Mayuscula/plural. |
| 49 | D13A | Por recolecion pública o privada | Por recolección pública o privada | 176 | TERR p73 | Typo SICAV 'recolecion'. |
| 50 | D14 | No tiene servicio sanitario | No tiene servicio sanitario | 189 | TERR p74 | Manual (p74) 'No tiene servicio sanitario' (singular); Oracle typo 'sanitarios'. res 189. |
| 70 | F4 | Otra | Otra, Cuál? | 246 | TERR p83 | Formato. |
| 76 | G7B_GRADO | Básica_primaria_1°_a_5° | Básica primaria (1º - 5º) | 263 | TERR p84 | Guiones bajos y grado; misma opcion. |
| 76 | G7B_GRADO | Básica_Secundaria_6°_a_9° | Básica secundaria (6º - 9º) | 264 | TERR p84 | Guiones bajos y grado; misma opcion. |
| 76 | G7B_GRADO | Media_10°_a_13° | Media (10º - 13º) | 265 | TERR p84 | Guiones bajos y grado; misma opcion. |
| 76 | G7B_GRADO | Ninguna | Ninguno | 261 | TERR p84 | 'Ninguna' vs 'Ninguno'; misma opcion (nivel educativo). |
| 79 | H8 | NS/NR | No sabe, no informa | 278 | TERR p68-69 | Abreviatura SICAV. |
| 92 | I10A | Otra | Otra ¿Cuál? | 351 | TERR p95 | Codigo I10A si corresponde a pre92 (rehabilitacion); 'Otra' -> res 351. |
| 95 | J1A | Si | Si ¿Cuántos días? | 360 | TERR p99 | Boolean consumo 7 dias; sub-campo dias. |
| 95 | J1A | Valor (1 a 7) | Si ¿Cuántos días? | 360 | TERR p99 | NO es opcion: sub-campo numerico (dias 1-7) que se almacena con la opcion 'Si'. Mismo res_idrespuesta que 'Si'. |
| 96 | J1B | Si | Si ¿Cuántos días? | 362 | TERR p99 | Boolean consumo 7 dias; sub-campo dias. |
| 96 | J1B | Valor (1 a 7) | Si ¿Cuántos días? | 362 | TERR p99 | NO es opcion: sub-campo numerico (dias 1-7) que se almacena con la opcion 'Si'. Mismo res_idrespuesta que 'Si'. |
| 97 | J1C | Si | Si ¿Cuántos días? | 364 | TERR p99 | Boolean consumo 7 dias; sub-campo dias. |
| 97 | J1C | Valor (1 a 7) | Si ¿Cuántos días? | 364 | TERR p99 | NO es opcion: sub-campo numerico (dias 1-7) que se almacena con la opcion 'Si'. Mismo res_idrespuesta que 'Si'. |
| 98 | J1D | Si | Si ¿Cuántos días? | 366 | TERR p99 | Boolean consumo 7 dias; sub-campo dias. |
| 98 | J1D | Valor (1 a 7) | Si ¿Cuántos días? | 366 | TERR p99 | NO es opcion: sub-campo numerico (dias 1-7) que se almacena con la opcion 'Si'. Mismo res_idrespuesta que 'Si'. |
| 99 | J1E | Si | Si ¿Cuántos días? | 368 | TERR p99 | Boolean consumo 7 dias; sub-campo dias. |
| 99 | J1E | Valor (1 a 7) | Si ¿Cuántos días? | 368 | TERR p99 | NO es opcion: sub-campo numerico (dias 1-7) que se almacena con la opcion 'Si'. Mismo res_idrespuesta que 'Si'. |
| 100 | J1F | Si | Si ¿Cuántos días? | 370 | TERR p99 | Boolean consumo 7 dias; sub-campo dias. |
| 100 | J1F | Valor (1 a 7) | Si ¿Cuántos días? | 370 | TERR p99 | NO es opcion: sub-campo numerico (dias 1-7) que se almacena con la opcion 'Si'. Mismo res_idrespuesta que 'Si'. |
| 101 | J1J | Si | Si ¿Cuántos días? | 372 | TERR p99 | Boolean consumo 7 dias; sub-campo dias. |
| 101 | J1J | Valor (1 a 7) | Si ¿Cuántos días? | 372 | TERR p99 | NO es opcion: sub-campo numerico (dias 1-7) que se almacena con la opcion 'Si'. Mismo res_idrespuesta que 'Si'. |
| 102 | J1K | Si | Si ¿Cuántos días? | 374 | TERR p99 | Boolean consumo 7 dias; sub-campo dias. |
| 102 | J1K | Valor (1 a 7) | Si ¿Cuántos días? | 374 | TERR p99 | NO es opcion: sub-campo numerico (dias 1-7) que se almacena con la opcion 'Si'. Mismo res_idrespuesta que 'Si'. |
| 103 | J1L | Si | Si ¿Cuántos días? | 376 | TERR p99 | Boolean consumo 7 dias; sub-campo dias. |
| 103 | J1L | Valor (1 a 7) | Si ¿Cuántos días? | 376 | TERR p99 | NO es opcion: sub-campo numerico (dias 1-7) que se almacena con la opcion 'Si'. Mismo res_idrespuesta que 'Si'. |
| 119 | L1 | Otra actividad | Otra actividad, ¿cuál? | 411 | TERR p103 | Formato. |
| 124 | L6 | No sabe, no responde | No sabe, no informa | 428 | TERR p108 | Variante 'informa'/'responde'. |
| 124 | L6 | Puso consultó avisos clasificados | Puso o consultó avisos clasificados | 424 | TERR p108 | Falta 'o' en SICAV. |
| 126 | L8 | Los empleadores lo consideran muy joven / viejo | Los empleadores lo consideran muy joven o muy viejo | 438 | TERR p110 | Formato '/'. |
| 134 | L16 | Si | Si ¿Cuál? | 472 | TERR p114 | Boolean; sub-campo 'Cual?'. |
| 137 | L18 | Si | Si ¿Cuánto? | 485 | TERR p116 | Boolean; sub-campo monto. |
| 139 | L20 | No sabe/No responde | No sabe / No informa | 492 | TERR p117 | Variante. |
| 139 | L20 | Si | Si ¿En Cuánto estima lo que recibió? | 490 | TERR p117 | Boolean; sub-campo monto. |
| 140 | L21 | No sabe/No responde | No sabe / No informa | 495 | TERR p117 | Variante. |
| 140 | L21 | Si | Si ¿En Cuánto estima lo que recibió? | 493 | TERR p117 | Boolean; sub-campo monto. |
| 141 | L22 | Si | Si ¿Cuánto recibió? | 496 | TERR p117 | Boolean; sub-campo 'Cuanto recibio?'. |
| 142 | L22B | Si | Si ¿Cuánto recibió? | 498 | TERR p117 | Boolean; sub-campo 'Cuanto recibio?'. |
| 143 | L22C | Si | Si ¿Cuánto recibió? | 500 | TERR p117 | Boolean; sub-campo 'Cuanto recibio?'. |
| 144 | L22D | Si | Si ¿Cuánto recibió? | 502 | TERR p117 | Boolean; sub-campo 'Cuanto recibio?'. |
| 145 | L22E | Si | Si ¿Cuánto recibió? | 504 | TERR p117 | Boolean; sub-campo 'Cuanto recibio?'. |
| 151 | M2A | No Sabe/No Responde | No sabe | 518 | TERR p118 | Variante 'No sabe'. |
| 151 | M2A | Si | Si ¿Valor del mes pasado? | 516 | TERR p118 | Boolean ingreso; sub-campo valor. |
| 152 | M2B | No Sabe/No Responde | No sabe | 521 | TERR p118 | Variante 'No sabe'. |
| 152 | M2B | Si | Si ¿Valor del mes pasado? | 519 | TERR p118 | Boolean ingreso; sub-campo valor. |
| 153 | M2C | No Sabe/No Responde | No sabe | 524 | TERR p118 | Variante 'No sabe'. |
| 153 | M2C | Si | Si ¿Valor del mes pasado? | 522 | TERR p118 | Boolean ingreso; sub-campo valor. |
| 154 | M5 | No Sabe/No Responde | No sabe | 3787 | TERR p118 | Variante 'No sabe'. |
| 154 | M5 | Si | Si ¿Valor del mes pasado? | 525 | TERR p118 | Boolean ingreso; sub-campo valor. |
| 154 | M5 | Valor | Si ¿Valor del mes pasado? | 525 | TERR p118 | NO es opcion: sub-campo numerico (valor) de la opcion 'Si'. Mismo res_idrespuesta que 'Si'. |
| 161 | M4C1A | No sabe, no responde | No sabe, no informa | 548 | TERR p120 | Variante 'informa'/'responde'. |
| 273 | A15 | Lo entiende pero no lo habla | La entiende pero no la habla | 971 | TERR p60 | 'Lo'(idioma) vs 'La'(lengua); misma opcion. |
| 273 | A15 | Lo entiende y habla poco | La entiende y habla poco | 970 | TERR p60 | 'Lo'(idioma) vs 'La'(lengua); misma opcion. |
| 273 | A15 | Lo habla y lo entiende bien | La habla y la entiende bien | 969 | TERR p60 | 'Lo'(idioma) vs 'La'(lengua); misma opcion. |
| 277 | J1H | Si | Si ¿Cuántos días? | 983 | TERR p99 | Boolean consumo 7 dias; sub-campo dias. |
| 277 | J1H | Valor (1 a 7) | Si ¿Cuántos días? | 983 | TERR p99 | NO es opcion: sub-campo numerico (dias 1-7) que se almacena con la opcion 'Si'. Mismo res_idrespuesta que 'Si'. |
| 278 | J1M | Si | Si ¿Cuántos días? | 985 | TERR p101 | Boolean consumo 7 dias; sub-campo dias. |
| 278 | J1M | Valor (1 a 7) | Si ¿Cuántos días? | 985 | TERR p101 | NO es opcion: sub-campo numerico (dias 1-7) que se almacena con la opcion 'Si'. Mismo res_idrespuesta que 'Si'. |
| 279 | J1N | Si | Si ¿Cuántos días? | 987 | TERR p99 | Boolean consumo 7 dias; sub-campo dias. |
| 279 | J1N | Valor (1 a 7) | Si ¿Cuántos días? | 987 | TERR p99 | NO es opcion: sub-campo numerico (dias 1-7) que se almacena con la opcion 'Si'. Mismo res_idrespuesta que 'Si'. |
| 293 | A16 | Lo habla y lo entiende bien | Lo entiende y lo habla bien | 1046 | TERR p60 | Orden de palabras; misma opcion. |
| 296 | A19 | Si | Sí ¿Cuál? | 1053 | TERR p61 | Boolean; sub-campo. |
| 300 | D10 | Aguas lluvias | Agua lluvia | 1101 | TERR p72 | Plural; res 1101 (unica escribible de lluvia en pre300). |
| 300 | D10 | De ota fuente por tubería (Redes comunitarias) | De otra fuente por tubería (Redes comunitarias) | 2369 | TERR p72 | Typo SICAV 'ota'. |
| 318 | D8A | Si | Si, ¿Estrato? | 1133 | TERR p70 | Boolean; sub-campo estrato. |
| 334 | E1C | Otra | Otra, ¿cuál? | 1172 | TERR p80 | Formato. |
| 347 | J1G | Si | Si ¿Cuántos días? | 1211 | TERR p99 | Boolean consumo 7 dias; sub-campo dias. |
| 347 | J1G | Valor (1 a 7) | Si ¿Cuántos días? | 1211 | TERR p99 | NO es opcion: sub-campo numerico (dias 1-7) que se almacena con la opcion 'Si'. Mismo res_idrespuesta que 'Si'. |
| 372 | A13C | Otro | Otro ¿Cuál? | 1299 | TERR p60 | Formato. |
| 373 | A13E | Pasto | Pasto (Nariño) | 1309 | TERR p60 | SICAV omite '(Narino)'. |
| 400 | I7E | Porque fue víctima de otros hechos | Porque fue víctima de otros hechos (delincuencia, por ejemplo) | 1401 | ASIS (origen discap.) | SICAV omite parentesis. |
| 453 | SA3 | Sí | Sí, Cuál? | 1508 | — | Boolean; sub-campo. |
| 798 | E1A | Ya se reubicó en un municipio diferente al que abandonó a causa del desplazamiento | Ya se reubicó en un municipio diferente al que abandonó a causa del desplaza... | 2378 | TERR p82 | SICAV omite 'forzado'. |
| 809 | I25B | Otra | Otra ¿Cuál? | 2406 | TERR p96 | Formato. |
| 809 | I25B | Otro ¿cual? | Otra ¿Cuál? | 2406 | TERR p96 | Formato/typo. |
| 812 | I28A | Comunitaria | Comunitario | 2414 | TERR p97 | Genero; misma opcion. |
| 814 | PL2 | Si | SÍ ¿Cuál? | 2417 | TERR p61 | Boolean; sub-campo. |
| 832 | PL13A | Otra razón | Otra razón, ¿cuál? | 2525 | ASIS (motivos capacit.) | Formato. |
| 837 | PL19 | Dueño y gerente | Dueño o gerente | 2535 | TERR p131 | 'y' vs 'o'. |
| 837 | PL19 | Otro | Otro, ¿Cuál? | 2538 | TERR p131 | Formato. |
| 838 | PL20 | Cuál | Sí ¿Cuál? | 2539 | TERR p131 | 'Cual' es el sub-campo de la opcion 'Si Cual?'. |
| 838 | PL20 | Si | Sí ¿Cuál? | 2539 | TERR p131 | Boolean. |
| 843 | PL21A | Otro | Otro ¿Cuál? | 2577 | TERR p132 | Formato. |
| 844 | PL22 | Otro | Otro ¿Cuál? | 2585 | TERR p132 | Formato. |
| 845 | PL23 | Si | Sí ¿Cuáles? | 2586 | TERR p133 | Boolean. |
| 846 | PL23B | Si | Sí ¿Cuáles? | 2588 | TERR p133 | Boolean. |
| 849 | PL24 | Otra ¿Cuál? | Otro ¿Cuál? | 2592 | TERR p133 | Genero/formato. |
| 865 | B13A | Trasplante renal | TRANSPLANTE RENAL | 3865 | TERR p56 | Mayusculas + typo Oracle 'TRANSPLANTE'. res 3865 (opcion simple, no la de lista 3876). |
| 866 | B17 | Territorio ancestral Habitado | Territorio Ancestralmente Habitado | 2630 | TERR p58 | Redaccion/mayusculas; misma opcion. |
| 866 | B17 | Territorio colectivo de Comunidades Negras | Territorio Colectivo de Comunidades Negras | 2629 | TERR p58 | Oracle typo 'Terrritorio'; misma opcion. |
| 872 | C17A | Combares o bombardeos | Combates o bombardeos | 2644 | TERR p76 | Typo SICAV 'Combares'. |
| 872 | C17A | Exploración y exploración minero-energética (petróleo, gas etc) | Exploración y explotación minero-energética (petróleo, gas etc) | 2642 | TERR p76 | Typo SICAV ('exploracion' repetido). |
| 872 | C17A | Megaproyectos de infraestructura y/o turiísticos (represas, hotelería etc.) | Megaproyectos de infraestructura y/o turísticos (represas, hotelería etc) | 2647 | TERR p76 | Typo SICAV 'turiisticos'. |
| 872 | C17A | Restricción a la movilidad - Confinamiento | Restricciones a la movilidad – Confinamiento | 2645 | TERR p76 | Singular/plural y guion. |
| 886 | RR5A | Pasto | Pasto (Nariño) | 3775 | TERR p43 | SICAV omite '(Narino)'. |
| 890 | RR10A | Pasto | Pasto (Nariño) | 3786 | TERR p43 | SICAV omite '(Narino)'. |
| 894 | M6 | No Sabe/No Responde | No sabe | 2724 | TERR p118 | Variante 'No sabe'. |
| 894 | M6 | Si | Si ¿Valor del mes pasado? | 2722 | TERR p118 | Boolean ingreso; sub-campo valor. |
| 895 | M7 | No Sabe/No Responde | No sabe | 2727 | TERR p118 | Variante 'No sabe'. |
| 895 | M7 | Si | Si ¿Valor del mes pasado? | 2725 | TERR p118 | Boolean ingreso; sub-campo valor. |
| 896 | M8 | No Sabe/No Responde | No sabe | 2730 | TERR p118 | Variante 'No sabe'. |
| 896 | M8 | Si | Si ¿Valor del mes pasado? | 2728 | TERR p118 | Boolean ingreso; sub-campo valor. |
| 897 | M9 | No Sabe/No Responde | No sabe | 2733 | TERR p118 | Variante 'No sabe'. |
| 897 | M9 | Si | Si ¿Valor del mes pasado? | 2731 | TERR p118 | Boolean ingreso; sub-campo valor. |
| 898 | M10 | No Sabe/No Responde | No sabe | 2736 | TERR p118 | Variante 'No sabe'. |
| 898 | M10 | Si | Si ¿Valor del mes pasado? | 2734 | TERR p118 | Boolean ingreso; sub-campo valor. |
| 899 | M11 | No Sabe/No Responde | No sabe | 2739 | TERR p118 | Variante 'No sabe'. |
| 899 | M11 | Si | Si ¿Valor del mes pasado? | 2737 | TERR p118 | Boolean ingreso; sub-campo valor. |
| 1158 | B18B | Otra | Otra, Cuál? | 3764 | TERR (tipo org.) | Formato. |
| 1187 | IF25 | Si | Sí, Cuántos días? | 3889 | TERR p101 | Boolean; sub-campo dias. |
| 1187 | IF25 | Valor (1 a 7) | Sí, Cuántos días? | 3889 | TERR p101 | NO es opcion: sub-campo numerico (dias 1-7) de la opcion 'Si'. Mismo res_idrespuesta que 'Si' (3889). |
| 1423 | ST1 | Otro | OTRO ¿CUÁL? | 4474 | TERR (predio urbano-rural) | Mayusculas. |
| 1424 | ST2 | De manera limitada: De manera limitada = existen pocas disposiciones en la legislación u... | DE MANERA LIMITADA = ... (texto completo, res 4476) | 4476 | TERR (derechos tierras) | Mismo texto (mayusculas y ':' vs '='). res 4476. |
| 1424 | ST2 | De manera significativa: De manera significativa = existen bastantes disposiciones en la... | DE MANERA SIGNIFICATIVA = ... (texto completo, res 4478) | 4478 | TERR (derechos tierras) | Mismo texto. res 4478. |
| 1424 | ST2 | Hasta cierto punto: Hasta cierto punto = existen algunas provisiones en la legislación u... | HASTA CIERTO PUNTO = ... (texto completo, res 4477) | 4477 | TERR (derechos tierras) | Mismo texto. res 4477. |
| 1439 | SA_PS_1 | NS/NR | No sabe no responde | 4531 | ASIS (regimen salud) | Abreviatura. |
| 1442 | FT_EMP_1 | Otra actividad | Otra actividad, ¿cuál? | 4539 | ASIS (actividad) | Formato. |
| 1478 | B13A_tel | Trasplante renal | TRANSPLANTE RENAL | 4629 | ASIS p41 | Mayusculas + typo Oracle. res 4629 (opcion simple). |
| 1489 | A13C_tel | Otro | Otro ¿Cuál? ________ | 4673 | ASIS p45 | Formato. |
| 1490 | A13E_tel | Pasto | Pasto - Nariño | 4684 | ASIS p45 | SICAV omite '- Narino'. |
| 1493 | C1_tel | Otra vivienda  (carpa, vagón, cueva, refugio natural,albergue, embarcación, campamento, ... | Otro tipo de vivienda ( carpa, vagón,  cueva, refugio natural,albergue,embar... | 4701 | ASIS p50-51 | 'Otra vivienda' vs 'Otro tipo de vivienda'; misma opcion, res 4701. |
| 1494 | D5_tel | En Usufructo** | Usufructo | 4704 | ASIS p52 | Prefijo/'**'. |
| 1494 | D5_tel | Otra ¿Cuál? | Otro. ¿Cuál? ____________ | 4711 | ASIS p52 | Formato/genero. |
| 1495 | D7_tel | Acta de adjudicación/ contrato de usufructo | Acta de adjudicación / contrato de usufructo | 4715 | ASIS p52-53 | Oracle typo 'adjundicacion'; misma opcion. res 4715. |
| 1498 | D8A_tel | Si | Si, ¿Estrato? | 4734 | ASIS p55 | Boolean; sub-campo. |
| 1504 | D13A_tel | Por recolecion pública o privada | Por recolección pública o privada | 4754 | ASIS p58 | Typo SICAV. |
| 1509 | C5_tel | Si    CUAL | SI | 4771 | ASIS (zona alto riesgo) | 'CUAL' es el sub-campo; opcion = 'SI' res 4771. |
| 1516 | J1A_tel | Si | Si ¿Cuántos días? | 4815 | ASIS p70 | Boolean consumo 7 dias; sub-campo dias. |
| 1517 | J1B_tel | Si | Si ¿Cuántos días? | 4817 | ASIS p70 | Boolean consumo 7 dias; sub-campo dias. |
| 1518 | J1C_tel | Si | Si ¿Cuántos días? | 4819 | ASIS p70 | Boolean consumo 7 dias; sub-campo dias. |
| 1519 | J1D_tel | Si | Si ¿Cuántos días? | 4821 | ASIS p70 | Boolean consumo 7 dias; sub-campo dias. |
| 1520 | J1E_tel | Si | Si ¿Cuántos días? | 4823 | ASIS p70 | Boolean consumo 7 dias; sub-campo dias. |
| 1521 | J1F_tel | Si | Si ¿Cuántos días? | 4825 | ASIS p70 | Boolean consumo 7 dias; sub-campo dias. |
| 1522 | J1T_tel | Si | Si ¿Cuántos días? | 4827 | ASIS p70 | Boolean consumo 7 dias; sub-campo dias. |
| 1523 | J1G_tel | Si | Si ¿Cuántos días? | 4829 | ASIS p70 | Boolean consumo 7 dias; sub-campo dias. |
| 1524 | J1H_tel | Si | Si ¿Cuántos días? | 4831 | ASIS p73 | Boolean consumo 7 dias; sub-campo dias. |
| 1525 | J1J_tel | Si | Si ¿Cuántos días? | 4833 | ASIS p70 | Boolean consumo 7 dias; sub-campo dias. |
| 1526 | J1K_tel | Si | Si ¿Cuántos días? | 4835 | ASIS p70 | Boolean consumo 7 dias; sub-campo dias. |
| 1527 | J1L_tel | Si | Si ¿Cuántos días? | 4837 | ASIS p70 | Boolean consumo 7 dias; sub-campo dias. |
| 1528 | J1M_tel | Si | Si ¿Cuántos días? | 4839 | ASIS p73 | Boolean consumo 7 dias; sub-campo dias. |

## 2.2 SUSTANTIVA (16)

| pre_id | cod SICAV | opcion SICAV actual | etiqueta propuesta (manual) | res_id Oracle | pagina manual | nota |
|---|---|---|---|---|---|---|
| 5 | Z6_tel | Rural disperso (vereda) | Rural disperso (vereda) | 10 | TERR p45-46 | Manual (p46) usa 'Rural disperso (vereda)'; SICAV ya coincide (limpiar coma final). Oracle anade 'Parte...campo': misma opcion, res 10. |
| 5 | Z6 | Rural disperso (vereda,) | Rural disperso (vereda) | 10 | TERR p45-46 | Manual (p46) usa 'Rural disperso (vereda)'; SICAV ya coincide (limpiar coma final). Oracle anade 'Parte...campo': misma opcion, res 10. |
| 28 | A9 | Cónyuge o Compañera(o) | Cónyuge o Compañera(o) | 80 | TERR p57 | Manual B23 (p57) usa etiqueta simple SIN '(Personas mayores de 14 anos)'. SICAV ya coincide con el manual; el calificador es artefacto de Oracle. Mantener etiqueta del manual, mapear a res 80. |
| 35 | Z4 | Negro(a), afrocolombiano(a) | Negro(a), afrocolombiano(a) o afrodescendiente | 116 | TERR p59; p78 | Manual (p59/p78) usa '...o afrodescendiente'. Alinear SICAV al manual. |
| 41 | C6A | Vientos fuertes | Vientos fuertes | 151 | TERR p75 | Manual (p75) lista 'Vientos fuertes' y lo define como 'vendavales...'. Oracle usa la etiqueta 'Vendabal' (typo de 'Vendaval') para la MISMA opcion. Mantener etiqueta del manual 'Vientos fuertes', mapear a res 151. |
| 124 | L6 | Se presento a una finca a trabajar como jornalero | Se presentó a alguna finca a trabajar como jornalero | 1283 | TERR p108 | 'a una finca' vs 'a alguna finca'; misma opcion. |
| 400 | I7E | A causa del conflicto armado (minas, cambates, otros) | Porque fue víctima del conflicto armado (minas, combates, otros) | 1400 | ASIS (origen discap.) | Redaccion SICAV distinta + typo 'cambates'; misma opcion (origen discapacidad). res 1400 escribible (ojo: res 1396 'Porque nacio asi' NO es escribible). |
| 872 | C17A | Presencia de cultivos ilícitos | Presencia de cultivos de uso ilícito | 2649 | TERR p76 | Manual (p76) 'cultivos de uso ilicito'; SICAV omite 'de uso'. Misma opcion. |
| 876 | H12A | Distancia | Distancia / Disperso | 2673 | TERR p85 | Oracle fusiona 'Distancia / Disperso'; SICAV solo 'Distancia'. Misma opcion, res 2673. |
| 877 | I1A1 | Produccion en pancoger (Chagra, conuco, roza, monte, patio, colino, tul, tambo o parcela) | Producción en pancoger (Chagra, conuco, roza, monte, patio, colino, tul, tam... | 2688 | TERR p99 | Manual (p99) INCLUYE el parentesis; Oracle res 2688 lo omite. Misma opcion. Mantener etiqueta del manual, mapear a res 2688. |
| 1164 | Z16 | Rural disperso (vereda,) | Rural disperso (vereda) | 3811 | TERR p45-46 | Manual (p46). Limpiar coma; Oracle anade 'Parte...campo'. res 3811. |
| 1435 | A24 | Otro pariente del jefe | OTRO PARIENTE DEL RESPONSABLE DEL HOGAR | 4504 | TERR p57 (B24) | Pre1435 = parentesco 'frente a persona responsable del hogar' (manual B24, p57). SICAV dice 'del jefe'; alinear a 'del responsable del hogar'. res 4504. |
| 1450 | Z4_tel | Negro(a), afrocolombiano(a) | Negro(a), afrocolombiano(a) o afrodescendiente | 4569 | ASIS p44-45 | Manual (p44) '...o afrodescendiente'. Alinear. |
| 1452 | Z6_tel | Rural disperso (vereda,) | Rural disperso (vereda) | 4574 | ASIS p30-31 | Manual (p30-31). res 4574. |
| 1461 | Z16_tel | Rural disperso (vereda,) | Rural disperso (vereda) | 4586 | ASIS (zona corresp.) | Manual. res 4586. |
| 1503 | D10_tel | Agua de carro tanques | Carrotanque | 4751 | ASIS p57 | Manual (p72/57): opcion oficial 'Carrotanque' (agua por carrotanque). SICAV usa etiqueta DANE antigua 'Agua de carro tanques'; en pre1503 la unica escribible equivalente es 'Carrotanque' res 4751. Alinear al manual. |

## 2.3 MAPEO_DUDOSO (12)

| pre_id | cod SICAV | opcion SICAV actual | etiqueta propuesta (manual) | res_id Oracle | pagina manual | nota |
|---|---|---|---|---|---|---|
| 92 | PR3_re | Alimentación | (pregunta mal mapeada) | — | TERR p95 | Codigo SICAV 'PR3_re' (componentes de Ayuda Humanitaria) quedo mapeado a pre_idpregunta 92 = 'que tipo de rehabilitacion ha recibido?'. Sus opciones NO corresponden a esa pregunta Oracle (Fisioterapia, Fonoaudiologia...). Revisar id_preg del perfil. |
| 92 | PR3_re | Alojamiento temporal | (pregunta mal mapeada) | — | TERR p95 | Codigo SICAV 'PR3_re' (componentes de Ayuda Humanitaria) quedo mapeado a pre_idpregunta 92 = 'que tipo de rehabilitacion ha recibido?'. Sus opciones NO corresponden a esa pregunta Oracle (Fisioterapia, Fonoaudiologia...). Revisar id_preg del perfil. |
| 92 | PR3_re | Apoyo económico (transferencia monetaria) | (pregunta mal mapeada) | — | TERR p95 | Codigo SICAV 'PR3_re' (componentes de Ayuda Humanitaria) quedo mapeado a pre_idpregunta 92 = 'que tipo de rehabilitacion ha recibido?'. Sus opciones NO corresponden a esa pregunta Oracle (Fisioterapia, Fonoaudiologia...). Revisar id_preg del perfil. |
| 92 | PR3_re | Aseo personal y elementos de hábitat | (pregunta mal mapeada) | — | TERR p95 | Codigo SICAV 'PR3_re' (componentes de Ayuda Humanitaria) quedo mapeado a pre_idpregunta 92 = 'que tipo de rehabilitacion ha recibido?'. Sus opciones NO corresponden a esa pregunta Oracle (Fisioterapia, Fonoaudiologia...). Revisar id_preg del perfil. |
| 92 | PR3_re | Atención médica y psicosocial | (pregunta mal mapeada) | — | TERR p95 | Codigo SICAV 'PR3_re' (componentes de Ayuda Humanitaria) quedo mapeado a pre_idpregunta 92 = 'que tipo de rehabilitacion ha recibido?'. Sus opciones NO corresponden a esa pregunta Oracle (Fisioterapia, Fonoaudiologia...). Revisar id_preg del perfil. |
| 92 | PR3_re | Auxilio funerario | (pregunta mal mapeada) | — | TERR p95 | Codigo SICAV 'PR3_re' (componentes de Ayuda Humanitaria) quedo mapeado a pre_idpregunta 92 = 'que tipo de rehabilitacion ha recibido?'. Sus opciones NO corresponden a esa pregunta Oracle (Fisioterapia, Fonoaudiologia...). Revisar id_preg del perfil. |
| 92 | PR3_re | Otra ayuda | (pregunta mal mapeada) | — | TERR p95 | Codigo SICAV 'PR3_re' (componentes de Ayuda Humanitaria) quedo mapeado a pre_idpregunta 92 = 'que tipo de rehabilitacion ha recibido?'. Sus opciones NO corresponden a esa pregunta Oracle (Fisioterapia, Fonoaudiologia...). Revisar id_preg del perfil. |
| 92 | PR3_re | Transporte de emergencia | (pregunta mal mapeada) | — | TERR p95 | Codigo SICAV 'PR3_re' (componentes de Ayuda Humanitaria) quedo mapeado a pre_idpregunta 92 = 'que tipo de rehabilitacion ha recibido?'. Sus opciones NO corresponden a esa pregunta Oracle (Fisioterapia, Fonoaudiologia...). Revisar id_preg del perfil. |
| 92 | PR3_re | Vestuario | (pregunta mal mapeada) | — | TERR p95 | Codigo SICAV 'PR3_re' (componentes de Ayuda Humanitaria) quedo mapeado a pre_idpregunta 92 = 'que tipo de rehabilitacion ha recibido?'. Sus opciones NO corresponden a esa pregunta Oracle (Fisioterapia, Fonoaudiologia...). Revisar id_preg del perfil. |
| 453 | SA3 | Campo Abierto | (sin correspondencia) | — | — | 'Campo Abierto' no es opcion de pre453 (Si/No/No sabe). En el manual 'campo abierto' es un tipo de input (texto libre), no una opcion. Escalar. |
| 880 | I1D | Campo Abierto | (sin correspondencia) | — | TERR p100 | 'Campo Abierto' no es opcion de pre880 (Si / No Por que?). Escalar. |
| 900 | AT2 | Por qué (Histórico) | (sin correspondencia) | — | TERR (adjud. material) | 'Por que (Historico)' no es opcion de pre900 (Si / No dispongo...). Posible sub-campo/campo historico mal ubicado. Escalar. |

## 2.4 NO_EN_MANUAL (2)

| pre_id | cod SICAV | opcion SICAV actual | etiqueta propuesta (manual) | res_id Oracle | pagina manual | nota |
|---|---|---|---|---|---|---|
| 2 | Perfil_tel | Autodiligenciada | (no listada en el manual) | — | TERR p43 | Manual A3 'Metodo de Recoleccion' (p43) lista solo 5: Vivienda de Residencia / Entrevista presencial / Entrevista telefonica / Jornada de Atencion / Otro. NO incluye 'Autodiligenciada'. SICAV ofrece algo que el manual no lista -> Oscar. |
| 2 | Perfil_tel | Cara a cara | (no listada en el manual) | — | TERR p43 | Manual A3 (p43) no lista 'Cara a cara' (opciones oficiales: Vivienda de Residencia / Entrevista presencial / Entrevista telefonica / Jornada de Atencion / Otro). Ambiguo entre 'Vivienda de residencia' y 'Entrevista presencial'. No forzar -> Oscar. |

## 3. Detalle de casos que requieren decision (MAPEO_DUDOSO)

Estos NO se resuelven en esta propuesta; se listan para Oscar / revision de mapeo id_preg:

- **pre 92 / PR3_re**: Codigo SICAV 'PR3_re' (componentes de Ayuda Humanitaria) quedo mapeado a pre_idpregunta 92 = 'que tipo de rehabilitacion ha recibido?'. Sus opciones NO corresponden a esa pregunta Oracle (Fisioterapia, Fonoaudiologia...). Revisar id_preg del perfil.
- **pre 453 / SA3**: 'Campo Abierto' no es opcion de pre453 (Si/No/No sabe). En el manual 'campo abierto' es un tipo de input (texto libre), no una opcion. Escalar.
- **pre 880 / I1D**: 'Campo Abierto' no es opcion de pre880 (Si / No Por que?). Escalar.
- **pre 900 / AT2**: 'Por que (Historico)' no es opcion de pre900 (Si / No dispongo...). Posible sub-campo/campo historico mal ubicado. Escalar.

---

_Generado como insumo de curacion. Cualquier alineacion de etiquetas SICAV debe hacerse editando el fixture fuente (no el bundle) y versionando, conforme a la politica del instrumento._