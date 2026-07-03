# Copiar-pegar al formato del supervisor — Informe Julio 2026

> Este documento concentra las **2 secciones que pide el formato del supervisor**
> (Actividad desarrollada en este periodo + Evidencia que soporta esta actividad)
> para cada una de las 9 obligaciones. Listo para copiar y pegar directo
> en el formato oficial UARIV al cierre del mes.
>
> *Actualizado: 01-jul-2026 (mes en ejecución).*

---

## Obligación 1 — Apoyar actividades de desarrollo, mantenimiento, documentación y soporte de las soluciones tecnológicas y aplicativos móviles

### Actividad desarrollada en este periodo

Se corrigieron dos defectos del módulo "Datos Básicos" del aplicativo móvil de
caracterización, detectados en una entrevista real con un hogar de tres personas.
Primero, la información que ya se conocía de cada integrante (nombres, fecha de
nacimiento, edad, grupo etario y documento) no se estaba precargando y salía en
blanco; se corrigió para que la precarga funcione **para cada miembro del hogar** y
no solo para el titular, tomando los datos de la misma fuente confiable que ya usa el
aplicativo. La edad y el grupo etario quedaron como **campos calculados automáticamente
y no editables**, y el tipo de documento se precarga según la edad cuando no viene el
dato. Segundo, al responder que una mujer del hogar está embarazada no aparecía el
campo para registrar el número de semanas; se creó ese campo y se corrigieron las
opciones de la pregunta. Se coordinó con el líder funcional el criterio de edad para
embarazo y lactancia.

### Evidencia que soporta esta actividad

- Commit versionado en `main` (repositorios GitHub y Azure DevOps): `3249a85`.
- Verificación técnica: revisión de tipos sin errores y batería de pruebas 77/77.
- Detalle en `OE1-desarrollo/README.md`.

---

## Obligación 2 — Realizar la captura, el procesamiento, la transformación y la gestión de calidad de datos de las fuentes recibidas por la entidad

### Actividad desarrollada en este periodo

Se ajustó la calidad de los datos del capítulo de datos básicos en los instrumentos de
cuatro perfiles (Buenaventura, San Andrés, Territorial y Urbano-Étnico): se limpiaron
las opciones de la pregunta de embarazo, se eliminó una opción sobrante mal
reconstruida y se agregó la pregunta de número de semanas de gestación. Los cambios se
aplicaron de forma consistente en la fuente de verdad (base de datos) y en el paquete
que usa la aplicación móvil sin conexión, mediante un procedimiento reproducible.

### Evidencia que soporta esta actividad

- `srni-backend/apps/formulario/fixtures/perfil_*_v*.json` y
  `srni-mobile/assets/instrumentos/*.json`.
- Procedimiento reproducible: `srni-backend/scripts/patch_bug2_embarazo_gestacion.py`.
- Detalle en `OE2-datos/README.md`.

---

## Obligación 3 — Procesar, implementar y documentar medidas de seguridad para proteger integridad, confiabilidad y confidencialidad de los datos

### Actividad desarrollada en este periodo

*(En ejecución — julio 2026.)*

### Evidencia que soporta esta actividad

*(Pendiente de consolidar.)*

---

## Obligación 4 — Realizar el diseño e implementación de las soluciones tecnológicas y aplicativos móviles

### Actividad desarrollada en este periodo

Se realizó la publicación del correctivo del módulo de datos básicos en los dos
repositorios oficiales y se documentó la decisión de arquitectura sobre el versionado
de los instrumentos: como el aplicativo trae los cuestionarios empaquetados y la
entrega de una versión nueva se hace con la publicación de una nueva versión del
aplicativo, no fue necesario cambiar el número de versión del instrumento.

### Evidencia que soporta esta actividad

- Publicación en `main` (GitHub y Azure DevOps).
- Detalle en `OE4-arquitectura/README.md`.

---

## Obligación 5 — Crear, diseñar y documentar la estructura de bases de datos

### Actividad desarrollada en este periodo

*(En ejecución — julio 2026.)*

### Evidencia que soporta esta actividad

*(Pendiente de consolidar.)*

---

## Obligación 6 — Crear y documentar modelos de datos que reflejen con precisión la información

### Actividad desarrollada en este periodo

Se ajustaron y documentaron las reglas de lógica de saltos del capítulo de datos
básicos: la pregunta de embarazo y la de madre lactante se habilitan para mujeres de 12
años en adelante, y el nuevo campo de semanas de gestación aparece únicamente cuando se
responde que sí hay embarazo. El criterio de edad fue avalado por el líder funcional.

### Evidencia que soporta esta actividad

- Reglas en los instrumentos de los cuatro perfiles y prueba automatizada de
  comportamiento (`datosBasicosB2.test.ts`).
- Detalle en `OE6-modelos/README.md`.

---

## Obligación 7 — Asistir a las reuniones programadas

### Actividad desarrollada en este periodo

*(En ejecución — julio 2026.)*

### Evidencia que soporta esta actividad

*(Pendiente actas.)*

---

## Obligación 8 — Cargar mensualmente los documentos de gestión

### Actividad desarrollada en este periodo

Se estructuró el informe de julio 2026 con el índice por obligación y el presente
formato del supervisor.

### Evidencia que soporta esta actividad

- Carpeta `informes/2026-07-julio/`.

---

## Obligación 9 — Cumplir las demás actividades acordadas con el supervisor

### Actividad desarrollada en este periodo

*(En ejecución — julio 2026.)*

### Evidencia que soporta esta actividad

*(Pendiente de consolidar.)*
