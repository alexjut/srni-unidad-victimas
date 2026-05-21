# Perfil Buenaventura V7

**Código:** `BUENAVENTURA`
**Versión:** V7
**Población objetivo:** Víctimas en el municipio de Buenaventura — comunidades Afro-colombianas
**Capítulos:** 17
**Preguntas estimadas:** ~300
**Loader:** `python manage.py cargar_buenaventura_v7`
**Estado:** ✅ Listo
**InstrumentoVersion PK:** `22222222-0002-0002-0002-000000000002`

---

## Fuente documental

`Diccionario_de_datos__Entrevista de Caracterización_V7_perfilBuenaventura.xlsx`

---

## Capítulos

### Capítulos compartidos con Territorial V7

| Código | Nombre |
|--------|--------|
| A | Datos del Hogar |
| B | Datos Básicos e Identidad |
| C | Vivienda |
| D | Economía del Hogar |
| F | Educación |
| G | Salud |
| H | Generación de Ingresos |
| JA | Justicia y Reparación (Hogar) |
| JF | Justicia y Reparación (Persona) |
| K | Discapacidad y Salud Mental |
| L | Hechos Victimizantes y Fuerza Pública |
| M | Tierras y Territorio |
| T | Datos Finales |

### Capítulos exclusivos de Buenaventura

| Código | Nombre | Descripción |
|--------|--------|-------------|
| FA | Formas de Atención (Hogar) | Acceso a servicios institucionales en Buenaventura |
| NA | Información Adicional del Hogar | Datos específicos de contexto Afro-Buenaventura |
| NP | Información Adicional de la Persona | Datos específicos de la persona en contexto Afro |
| O | Seguridad Jurídica del Territorio | Derechos territoriales colectivos — comunidades negras |

---

## Capítulo O — Seguridad Jurídica del Territorio (exclusivo)

Diseñado específicamente para las comunidades negras de Buenaventura. Incluye variables:

| Variable | Descripción |
|----------|-------------|
| ST1 | ¿El territorio cuenta con título colectivo? |
| ST2 | Nombre del Consejo Comunitario |
| ST3 | ¿Tiene representación ante el Consejo Comunitario? |
| ST4–ST6 | Uso del territorio colectivo |
| ST7–ST9 | Conflictos sobre el territorio |
| ST10–ST13 | Acceso a servicios en el territorio |

---

## Diferencias clave respecto a Territorial V7

1. **3 capítulos adicionales** — NA, NP, O (no existen en Territorial)
2. **Capítulo FA** — reemplaza y amplía el módulo de atención institucional
3. **Capítulo B ampliado** — mayor detalle de identidad afro (consejos comunitarios, territorio colectivo)
4. **Capítulo M ampliado** — incluye preguntas sobre derechos colectivos del territorio
5. **Total preguntas mayor** — ~300 vs ~248 del Territorial

---

## Cómo cargar

```bash
cd srni-backend
python manage.py loaddata perfiles_iniciales   # prerequisito una sola vez
python manage.py cargar_buenaventura_v7        # idempotente — puede repetirse
```
