# Perfil San Andrés / SAI V7

**Código:** `SAN_ANDRES`
**Versión:** V7
**Población objetivo:** Víctimas en el archipiélago de San Andrés, Providencia y Santa Catalina (SAIPSCA) — pueblo RAIZAL
**Capítulos:** 14
**Preguntas estimadas:** ~290
**Loader:** `python manage.py cargar_san_andres_v7`
**Estado:** ✅ Listo
**InstrumentoVersion PK:** `22222222-0003-0003-0003-000000000003`

---

## Fuente documental

`Diccionario_de_datos__Entrevista de Caracterización_V7_Perfil San Andrés.xlsx`

---

## Capítulos

Misma estructura de 14 capítulos que el Perfil Territorial V7, con adaptaciones para el contexto insular:

| Código | Nombre | Adaptaciones SAI |
|--------|--------|-----------------|
| A | Datos del Hogar | Sin "vereda" — usa "sector" o "barrio" |
| B | Datos Básicos e Identidad | Identidad RAIZAL + idioma Creole English |
| C | Vivienda | — |
| D | Economía del Hogar | Incluye pesca artesanal como actividad |
| E | Seguridad Alimentaria | — |
| F | Educación | Incluye preguntas sobre educación en inglés/creole |
| G | Salud | — |
| H | Generación de Ingresos | Pesca, turismo, actividades insulares |
| JA | Justicia y Reparación (Hogar) | — |
| JF | Justicia y Reparación (Persona) | — |
| K | Discapacidad y Salud Mental | — |
| L | Hechos Victimizantes y Fuerza Pública | — |
| M | Tierras y Territorio | Orientado a territorio insular, no continental |
| T | Datos Finales | — |

---

## Adaptaciones específicas al archipiélago

### Capítulo A — Datos del Hogar
- Se elimina la variable `VEREDA` (no existe en las islas)
- Se reemplaza por `SECTOR` y `BARRIO O SECTOR`
- El desplegable de ubicación muestra sectores de San Andrés y Providencia

### Capítulo B — Datos Básicos e Identidad
- Pregunta de pertenencia étnica incluye opción explícita `RAIZAL DEL ARCHIPIELAGO`
- Pregunta adicional: ¿Habla Creole English? (lengua nativa RAIZAL)
- Pregunta adicional: ¿Habla inglés isleño?

### Capítulo M — Tierras y Territorio
- Adaptado para territorio insular (no aplican preguntas de predios rurales continentales)
- Incluye variables sobre acceso a mar y recursos pesqueros
- Variables sobre pesca artesanal como medio de vida territorial

### Capítulo H — Generación de Ingresos
- Opciones de actividad económica incluyen:
  - Pesca artesanal
  - Turismo
  - Buceo
  - Agricultura en parcela insular

---

## Diferencias clave respecto a Territorial V7

| Aspecto | Territorial V7 | SAI V7 |
|---------|:--------------:|:------:|
| División territorial | Vereda | Sector/Barrio |
| Identidad étnica | General | RAIZAL específico |
| Idioma local | N/A | Creole English |
| Actividad económica | Agropecuaria | Pesca/Turismo/Insular |
| Territorio | Continental | Insular |
| Número de capítulos | 14 | 14 |
| Preguntas aprox. | 248 | ~290 |

---

## Cómo cargar

```bash
cd srni-backend
python manage.py loaddata perfiles_iniciales   # prerequisito una sola vez
python manage.py cargar_san_andres_v7          # idempotente — puede repetirse
```
