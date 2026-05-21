# Perfil Territorial V7

**Código:** `TERRITORIAL`
**Versión:** V7
**Población objetivo:** Víctimas del conflicto armado en todo el territorio nacional
**Capítulos:** 14
**Preguntas estimadas:** ~248
**Loader:** `python manage.py cargar_territorial_v7`
**Estado:** ✅ Listo
**InstrumentoVersion PK:** `22222222-0001-0001-0001-000000000001`

---

## Fuente documental

`Diccionario_de_datos__Entrevista de Caracterización_V7_Perfil Territorial.xlsx`
Manual UARIV 520.06.06-1 v01 (07/10/2021)

---

## Capítulos

### Capítulos de HOGAR

| Código | Nombre | Descripción |
|--------|--------|-------------|
| A | Datos del Hogar | Ubicación geográfica, municipio, vereda, estrato |
| C | Vivienda | Tipo, material paredes/pisos, servicios públicos |
| D | Economía del Hogar | Ingresos, gastos, fuentes de sustento |
| E | Seguridad Alimentaria | Acceso a alimentos, frecuencia, calidad |
| JA | Justicia y Reparación (Hogar) | Medidas de reparación, retorno, reubicación |
| M | Tierras y Territorio | Tenencia, uso, situación actual |
| T | Datos Finales | Observaciones del encuestador |

### Capítulos de PERSONA

| Código | Nombre | Descripción |
|--------|--------|-------------|
| B | Datos Básicos e Identidad | Documento, fecha nacimiento, pertenencia étnica |
| F | Educación | Nivel, asistencia escolar, barreras de acceso |
| G | Salud | Afiliación, acceso, condiciones especiales |
| H | Generación de Ingresos | Ocupación, empleo, emprendimiento |
| JF | Justicia y Reparación (Persona) | Situación individual |
| K | Discapacidad y Salud Mental | Tipo de discapacidad, atención psicosocial |
| L | Hechos Victimizantes y Fuerza Pública | Hechos, fecha, impacto |

---

## Skip logic relevante

- **B → F:** Solo se pregunta nivel educativo de personas mayores de 5 años
- **G → K:** Si tiene discapacidad (`K1=SI`) → habilita módulo de discapacidad completo
- **M → A:** Si fue desplazado (`A1=SI`) → pregunta por municipio de origen
- **L:** Solo se muestra a personas mayores de 15 años (o tutor para menores)

---

## Comparación con otros perfiles

| Característica | Territorial V7 | Buenaventura V7 | SAI V7 |
|----------------|:--------------:|:---------------:|:------:|
| Capítulos | 14 | 17 | 14 |
| Vereda | ✅ | ✅ | ❌ (sector) |
| Identidad Afro | básico | ampliado (NA/NP/O) | RAIZAL |
| Territorio insular | ❌ | ❌ | ✅ |
| Preguntas aprox. | 248 | ~300 | ~290 |

---

## Cómo cargar

```bash
cd srni-backend
python manage.py loaddata perfiles_iniciales   # prerequisito una sola vez
python manage.py cargar_territorial_v7         # idempotente — puede repetirse
```

El loader usa `update_or_create` con `codigo_externo` como clave única. Se puede ejecutar múltiples veces sin duplicar datos.
