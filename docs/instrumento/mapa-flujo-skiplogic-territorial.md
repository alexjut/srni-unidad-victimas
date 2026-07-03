# Mapa de flujo — Perfil TERRITORIAL y ÉTNICO (skip-logic)

> Fuente: Manual Perfil Territorial y Étnico (cód. 520,06,06-3), 13 capítulos A–M, 262 preguntas.
> Texto completo y opciones de respuesta → manual/diccionario. Aquí solo **tipo + regla de habilitación**.
> Notación: `← X = Y` = se habilita si la pregunta X se respondió Y. `A4` = autorreconocimiento étnico.
> `—` en regla = sin condición explícita en el manual → se muestra siempre (validar contra el alcance del capítulo).
> ⚠️ A, B y C son **iguales** al perfil Asistencia; de D en adelante este perfil difiere.
>
> ⚙️ Las reglas `←` se derivaron del texto del manual. Verificar las vagas (citan "cualquiera de estas
> opciones"/"de respuesta"): **G7** (vacunación: el manual la limita a mujeres de cierta edad),
> **L2, L4, L7, L9** (Fuerza Pública). Corregidas a mano: G6 (← G1 afiliado) y F7 (← edad ≥ 3).

## Capítulo A — Información General
*Alcance:* Mixto. Datos del hogar; A4 (étnico) y contacto **por persona**.

| # | Tipo | Pregunta | Regla |
|---|---|---|---|
| A1 | abierta | Dirección territorial | — |
| A2 | abierta | Lugar de la Encuesta | — |
| A3 | única | Método de Recolección | — |
| A4 | única | Autorreconocimiento étnico | — |
| A5 | abierta | Lugar de Residencia | — |
| A6 | única | Zona de Residencia | — |
| A7 | numérica | Barrio, Centro Poblado, Vereda | — |
| A8 | numérica | Ingrese nombre de la vereda | — |
| A9 | numérica | Dirección de la vivienda o nombre de la finca/predio | — |
| A10 | numérica | Teléfono Fijo | — |
| A11 | numérica | Celular | por cada persona del hogar |
| A12 | numérica | Otro teléfono de contacto | — |
| A13 | abierta | Correo Electrónico | — |
| A14 | única | Lugar de correspondencia es el mismo de residencia | — |
| A15 | abierta | Departamento y municipio de correspondencia | — |
| A16 | única | Zona de correspondencia | — |
| A17 | numérica | Barrio, centro poblado, vereda | — |
| A18 | numérica | Ingrese nombre de la vereda | — |
| A19 | numérica | Dirección de Correspondencia | — |
| A20 | — | Supervisor de la Encuesta | — |
| A21 | — | Observaciones a este capítulo | — |

## Capítulo B — Datos Básicos
*Alcance:* **Por persona** (todos los miembros). Étnicas se desprenden de A4.

| # | Tipo | Pregunta | Regla |
|---|---|---|---|
| B1 | abierta | Nombres y Apellidos | — |
| B2 | única | ¿…Está presente en esta entrevista? | todo el hogar; Si/No |
| B3 | — | Fecha de nacimiento | — |
| B4 | — | Años cumplidos | — |
| B5 | — | Grupo etario | — |
| B6 | única | Tipo de documento | — |
| B7 | única | ¿Cuenta con el documento? | — |
| B8 | numérica | No. Documento | — |
| B9 | única | Novedades en el RUV | todas las personas |
| B10 | — | Sexo (preguntar, no asumir) | todas las personas |
| B11 | única | Orientación sexual | ← edad ≥ 12 |
| B12 | única | Identidad de género | ← edad ≥ 12 |
| B13 | única | ¿Tiene libreta Militar? | — |
| B14 | única | ¿Libreta militar en físico? | — |
| B15 | única | ¿Pertenece/perteneció a Fuerza Pública? | — |
| B16 | única | ¿Presenta alguna discapacidad? | — |
| B17 | múltiple | ¿Qué tipo de discapacidad? | ← B16 = Si |
| B18 | única | ¿Origen de la discapacidad? | ← B16 = Si |
| B19 | única | ¿Diagnóstico enfermedades ruinosas/catastróficas? | — |
| B20 | múltiple | ¿Cuál enfermedad? | ← B19 = Si |
| B21 | única | ¿Mujeres del hogar en embarazo? | mujeres del hogar (víctimas o no) |
| B22 | única | ¿Madre lactante? | ← solo mujeres 12–50 |
| B23 | única | Parentesco frente al jefe del hogar | — |
| B24 | única | Parentesco frente a responsable del hogar | solo Buenaventura |
| B25 | única | ¿Entorno cultural acorde a usos y costumbres? | ← A4 ≠ Ninguna |
| B26 | única | ¿Habita territorio colectivo? | ← A4 ≠ Ninguna |
| B27 | única | ¿Tipo de territorio? | ← A4 = Indígena |
| B28 | abierta | ¿Pueblo indígena? | ← A4 = Indígena |
| B29 | abierta | ¿Comunidad indígena? | ← A4 = Indígena |
| B30 | abierta | ¿Cabildo indígena? | ← A4 = Indígena |
| B31 | — | ¿Consejo comunitario? | ← A4 = Negro/Afro |
| B32 | abierta | ¿Cuál consejo comunitario? | ← A4 = Negro/Afro |
| B33 | única | ¿Vitsa? | ← A4 = Gitano/Rrom |
| B34 | única | ¿Kumpania? | ← A4 = Gitano/Rrom |
| B35 | única | ¿Reconoce autoridad en sitio de residencia? | ← A4 ≠ Ninguna |
| B36 | única | ¿Reconoce autoridad del Resguardo/comunidad? | ← A4 ≠ Ninguna |
| B37 | única | ¿Comunidad/pueblo tiene idioma propio? | ← A4 ≠ Ninguna |
| B38 | única | En cuanto a su idioma propio: | ← B37 = Si |
| B39 | única | En cuanto al idioma español: | ← edad ≥ 2 |
| B40 | única | ¿Pertenece a alguna organización? | ← A4 ≠ Ninguna |
| B41 | múltiple | ¿Qué tipo de organización? | ← A4 ≠ Ninguna |
| B42 | numérica | ¿Hace cuántos años vive en el municipio? | — |
| B43 | única | ¿Declaró nuevos hechos en últimos 6 meses? | — |
| B44 | múltiple | ¿Cuáles hechos declarados? | ← B43 = Si |
| B45 | única | ¿Es víctima del conflicto armado? | personas no incluidas en RUV |
| B46 | única | ¿Solicitó inclusión RUPD/RUV? | personas no incluidas en RUV |
| B47 | múltiple | ¿Razones para no declarar? | ← B46 = No declaró |
| B48 | — | Fin del capítulo | — |

## Capítulo C — Vivienda
*Alcance:* **Por hogar** (una vez).

| # | Tipo | Pregunta | Regla |
|---|---|---|---|
| C1 | única | ¿Tipo de vivienda? | — (finaliza cap si "otro tipo"/calle/ilegal) |
| C2 | única | La vivienda ocupada es: | ← C1 ≠ (otro) |
| C3 | única | ¿Tipo de documento soporte? | ← C2 = Propia |
| C4 | única | Material de paredes | ← C1 ≠ (otro) |
| C5 | única | Material de pisos | ← C1 ≠ (otro) |
| C6 | única | ¿Vivienda adecuada a usos y costumbres? | ← A4 ≠ Ninguna |
| C7 | única | ¿Servicio energía eléctrica? | — |
| C8 | única | ¿Servicio Alcantarillado? | — |
| C9 | única | ¿Servicio acueducto? | — |
| C10 | única | ¿Gas Natural conectado? | — |
| C11 | — | ¿Recolección de basuras? | — |
| C12 | única | ¿Servicios públicos vía vecinos? | ← A4 = Gitano/Rrom |
| C13 | única | ¿De dónde proviene el agua para beber? | ← C9 = No |
| C14 | múltiple | ¿Cómo eliminan las basuras? | ← C11 = No |
| C15 | única | ¿Principal servicio sanitario? | ← C8 = No |
| C16 | numérica | ¿Cuántos cuartos en total? | ← C1 = Casa/Apto/Cuarto |
| C17 | — | ¿Cuántos cuartos para dormir? | ← C1 = Casa/Apto/Cuarto |
| C18 | numérica | ¿Cuánto cobraría de arriendo? | ← C2 = Propia |
| C19 | única | ¿Zona de alto riesgo? | ← C1 ≠ (otro) |
| C20 | múltiple | Afectación zona últimos 2 años | ← C1 ≠ (otro) |
| C21 | múltiple | Afectación por factores (últimos 2 años) | NO en Buenaventura |
| C22 | — | Observaciones a este capítulo | — |

## Capítulo D — Retornos y Reubicaciones (Territorial)
| # | Tipo | Pregunta | Regla |
|---|---|---|---|
| D1 | — | Observaciones iniciales | — |
| D2 | única | Situación respecto al retorno/reubicación | — |
| D3 | única | Decisión sobre el derecho | ← D2 = Ninguna de las anteriores |
| D4 | única | ¿Solicitó apoyo del Gobierno? | ← A4 ≠ Ninguna |
| D5 | única | ¿Lo acompañó alguna entidad? | — |
| D6 | — | Depto/municipio donde retornó | — |
| D7 | abierta | ¿Resguardo indígena? | ← A4 = Indígena |
| D8 | abierta | ¿Comunidad indígena? | ← A4 = Indígena |
| D9 | abierta | ¿Territorio Colectivo Negras? | ← A4 = Negro/Afro |
| D10 | única | ¿A qué Kumpania? | ← A4 = Gitano/Rrom |
| D11 | — | Depto/municipio donde desea retornar | ← D3 = quiere retornar |
| D12 | abierta | ¿Resguardo deseado? | ← A4 = Indígena |
| D13 | abierta | ¿Comunidad deseada? | ← A4 = Indígena |
| D14 | abierta | ¿Territorio colectivo deseado? | ← A4 = Negro/Afro |
| D15 | única | ¿Kumpania deseada? | ← A4 = Gitano/Rrom |
| D16 | única | Razones para residir aquí | — |
| D17 | — | Observaciones | — |

## Capítulo E — Reunificación Familiar
| # | Tipo | Pregunta | Regla |
|---|---|---|---|
| E1 | única | ¿Hogar obligado a separarse por desplazamiento? | — |
| E2 | única | ¿Solicitó apoyo para reunificación? | ← E1 = Si |
| E3 | única | ¿Recibió el apoyo? | ← E2 = Si |
| E4 | única | ¿Logró reunificarse? | ← E2 = No |
| E5 | única | ¿Por qué no solicitó apoyo? | — |
| E6 | única | ¿Interesado en iniciar proceso? | — |
| E7 | — | Observaciones | — |

## Capítulo F — Educación
*Alcance:* **Por persona**, 3 años o más.

| # | Tipo | Pregunta | Regla |
|---|---|---|---|
| F1 | única | ¿Matriculado actualmente? | — |
| F2 | única | ¿Sabe leer y escribir español? | ← edad ≥ 5 |
| F3 | única | ¿Interesado en alfabetización? | ← F2 = No |
| F4 | única | ¿Recibe enseñanza de prácticas étnicas? | ← A4 ≠ Ninguna |
| F5 | única | ¿Profesor de su grupo étnico? | ← A4 ≠ Ninguna |
| F6 | única | ¿Razón para no estudiar? | ← F1 = No |
| F7 | única | ¿Nivel educativo más alto? | ← edad ≥ 3 |
| F8 | única | ¿Requiere acceder a educación? | — |
| F9 | — | Observaciones | — |

## Capítulo G — Salud
*Alcance:* **Por persona**.

| # | Tipo | Pregunta | Regla |
|---|---|---|---|
| G1 | única | ¿Afiliado/cotizante/beneficiario? | — |
| G2 | única | ¿Servicio acorde a usos y costumbres? | ← A4 ≠ Ninguna |
| G3 | única | ¿Qué hizo para tratar su salud? | — |
| G4 | única | ¿Atención oportuna en IPS? | ← A4 ≠ Ninguna |
| G5 | múltiple | ¿Razones para no asistir a EPS? | ← A4 ≠ Ninguna |
| G6 | única | ¿IPS primaria en municipio de residencia? | ← G1 ≠ No afiliado/NS-NR |
| G7 | única | ¿Esquema de vacunación al día? | ← mujeres (cierta edad) ⚠️verificar |
| G8 | — | Observaciones | — |

## Capítulo H — Rehabilitación
*Alcance:* **Por persona** incluida en RUV.

| # | Tipo | Pregunta | Regla |
|---|---|---|---|
| H1 | — | Observaciones Iniciales | — |
| H2 | — | ¿Recibe rehabilitación? | — |
| H3 | — | ¿Qué tipo de rehabilitación? | ← H2 = Si |
| H4 | múltiple | ¿Ha recibido acompañamiento psicosocial? | — |
| H5 | múltiple | ¿Por parte de qué entidad? | ← H4 recibió |
| H6 | única | ¿La atención contribuyó? | ← H4 recibió |
| H7 | única | ¿Requiere acompañamiento psicosocial? | — |
| H8 | — | Desea que el acompañamiento sea: | ← H7 = Si |
| H9 | única | ¿Coordinación de entidades del Estado? | ← A4 ≠ Ninguna |
| H10 | única | ¿Proceso contó con intérpretes/traductores? | ← A4 ≠ Ninguna |

## Capítulo I — Alimentación
*Alcance:* **Por hogar**.

| # | Tipo | Pregunta | Regla |
|---|---|---|---|
| I1 | — | Observaciones iniciales | — |
| I2 | múltiple | ¿Cómo se aprovisiona de alimentos? | ← A4 ≠ Ninguna |
| I3 | única | ¿Dificultades para adquirir alimentos? | ← A4 ≠ Ninguna |
| I4–I17 | única/abierta | Consumo últimos 7 días (por grupo de alimentos) | — |
| I18 | única | ¿Alimentación adecuada? | ← A4 ≠ Ninguna |
| I19 | — | Observaciones | — |

## Capítulos J–M (Territorial — NO aplican a Asistencia)
- **J — Acceso al Trabajo** (por persona, 10+): J1…J42, cadenas de ingresos/primas.
- **K — Perfil Sociolaboral** (por persona): K1…K40.
- **L — Fuerza Pública** (quien pertenece/perteneció): L1…L10. ⚠️ L2/L4/L7/L9 reglas vagas.
- **M — Uso y Disfrute del Territorio** (por hogar): M1…M9. M8 NO en Buenaventura.
