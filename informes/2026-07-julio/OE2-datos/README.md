# OE2 — Captura, procesamiento y calidad de datos

> **Obligación contractual:** *Realizar la captura, el procesamiento, la transformación y la gestión de calidad de datos de las fuentes recibidas por la entidad en el desarrollo de las mediciones para las soluciones tecnológicas y aplicativos móviles.*

## Actividad desarrollada en este periodo

Corrección de calidad de datos del **capítulo B (Datos Básicos)** en los instrumentos
de 4 perfiles, alineando la captura con el manual y con la fuente de verdad (fixture).

- **Pregunta de embarazo (B2):** se corrigieron las opciones a **"Sí, ¿Cuántas?" / "No"**
  y se eliminó una opción huérfana (`TEXTO / "Campo Abierto"`) que había quedado mal
  reconstruida desde el diccionario.
- **Nueva pregunta hija "¿Cuántas?" (B2_CANT):** numérica, sin rango (solo numérico),
  que captura las semanas de gestación solo cuando embarazo = "Sí".
- Cambios aplicados de forma **idempotente y consistente** en fixture (fuente de verdad)
  y bundle móvil de los 4 perfiles, con `orden` re-numerado sin colisiones y
  `id_resp_vivanto` preservado.

Perfiles intervenidos: **Buenaventura, San Andrés, Territorial, Urbano-Étnico**.

## Evidencia que soporta esta actividad

- Script de reconciliación versionado: `srni-backend/scripts/patch_bug2_embarazo_gestacion.py`
  (con verificación `--check`).
- Fixtures: `srni-backend/apps/formulario/fixtures/perfil_*_v*.json`.
- Bundles: `srni-mobile/assets/instrumentos/*.json`.
- Aviso agregado a los generadores desde Excel
  (`generar_buenaventura/san_andres_desde_diccionario.py`): tras regenerar hay que
  re-correr el script de reconciliación (la curación del cap. B vive en el fixture).
- Siembra en servidor: `python manage.py cargar_perfil --instrumento {BUENAVENTURA,SAN_ANDRES,TERRITORIAL,URBANO_ETNICO}`
  seguido de `python manage.py exportar_a_mobile`.

## Evidencia física recolectada

Archivos en [`evidencias/`](evidencias/):

| Archivo | Qué prueba |
|---|---|
| `padron-cargado-y-calidad-produccion.txt` | El padrón real cargado, por estado en el RUV, y la clasificación de los documentos compartidos por varias personas |
| `veredicto_calidad_bd.md` | Auditoría de calidad de la base de origen, con los defectos medidos |
| `hallazgos_identidad_padron.md` | Análisis de la identidad no resuelta en la fuente (el 24 % que no pudo incorporarse) |
| `defectos_bd_legacy.md` | Registro de defectos de la base del legado para atender post-migración |
| `commits-calidad-datos-julio.txt` | Los cambios de calidad de datos del mes, del histórico del repositorio |
