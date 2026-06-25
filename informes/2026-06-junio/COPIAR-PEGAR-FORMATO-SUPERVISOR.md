# Copiar-pegar al formato del supervisor — Informe Junio 2026

> Este documento concentra las **2 secciones que pide el formato del supervisor**
> (Actividad desarrollada en este periodo + Evidencia que soporta esta actividad)
> para cada una de las 9 obligaciones. Listo para copiar y pegar directo
> en el formato oficial UARIV al cierre del mes.
>
> *Actualizado: 23-jun-2026.*

---

## Obligación 1 — Apoyar actividades de desarrollo, mantenimiento, documentación y soporte de las soluciones tecnológicas y aplicativos móviles

### Actividad desarrollada en este periodo

Se realizó una auditoría técnica exhaustiva de la aplicación móvil de caracterización (APK "Vínculo Colombiano") y se corrigieron los hallazgos en oleadas sucesivas: integridad de la cola de sincronización, flujo de inicio de sesión, privacidad, motor de captura de formularios, cálculo del porcentaje de avance con lógica de saltos (skip-logic), captura de hogares creados en línea cuando se pierde la conexión, flujo asistido por IA, degradación funcional sin conexión, reconciliación de la cola al iniciar la app y consentimiento explícito de biometría. Adicionalmente se ajustó el instrumento Territorial (nuevas preguntas y sub-campos condicionales), se implementó la identidad institucional "Vínculo Colombiano" en el inicio de sesión y el nombre de la aplicación, y se compiló y publicó la APK de forma continua. Se brindó soporte y guía técnica al desarrollador del panel web.

### Evidencia que soporta esta actividad

- Commits versionados en `main` (repositorios GitHub y Azure DevOps), con prefijos `fix(mobile)/feat(instrumento)/feat(mobile)`.
- Compilaciones EAS publicadas y desplegadas en el servidor (página de descarga con código QR).
- `docs/INFORME-ARQUITECTURA-ESTADO.md` y `OE1-desarrollo/guia-brando-modulo-usuarios.md`.

---

## Obligación 2 — Realizar la captura, el procesamiento, la transformación y la gestión de calidad de datos de las fuentes recibidas por la entidad

### Actividad desarrollada en este periodo

Se modeló, cargó y validó el instrumento de caracterización Territorial (14 capítulos, 218 preguntas, 19 reglas de lógica de saltos) en la base de datos mediante un comando idempotente, y se exportó al paquete offline que la APK empaqueta para operar sin conexión. Se aplicaron reglas de calidad: preguntas obligatorias visibles, agrupación de sub-campos condicionales y conteo de avance acotado. Se generaron datos de demostración y casos de víctimas de prueba para la validación funcional.

### Evidencia que soporta esta actividad

- `srni-backend/apps/formulario/fixtures/perfil_territorial_v7.json` y `srni-mobile/assets/instrumentos/territorial_v7.json`.
- `OE8-informes/victimas-prueba-funcionales.md`, `OE2-datos/`.

---

## Obligación 3 — Procesar, implementar y documentar medidas de seguridad para proteger integridad, confiabilidad y confidencialidad de los datos

### Actividad desarrollada en este periodo

Se implementó el ingreso biométrico como **opción explícita del usuario** (antes se activaba automáticamente sin consentimiento), alineado con la protección de datos personales. Se incorporó la reconciliación de la cola offline al iniciar la app para evitar pérdida silenciosa de información capturada. Se mantuvo el cifrado de datos personales en reposo en el backend y se documentó el plan de cifrado en reposo del dispositivo (SQLCipher, fase posterior). Se atendió el análisis de seguridad de la solución.

### Evidencia que soporta esta actividad

- Commit de biometría opt-in; `docs/mobile/offline-cifrado-en-reposo.md`.
- `docs/gestion/respuesta-analisis-seguridad-2026-06.md`, `OE3-seguridad/`.

---

## Obligación 4 — Realizar el diseño e implementación de las soluciones tecnológicas y aplicativos móviles

### Actividad desarrollada en este periodo

Se consolidó la arquitectura offline-first de la APK (almacenamiento local, cola de sincronización con dependencias y precarga de padrón/jornada). Se mantuvo el despliegue reproducible en el servidor de la entidad (Docker Compose, puerto 8090) y la cascada automatizada de publicación del APK (compilación en la nube → descarga → publicación en el servidor con QR estable). Se implementó la identidad institucional "Vínculo Colombiano" (inicio de sesión, nombre de la aplicación y constantes de marca centralizadas). Se gestionó ante la OTI la solicitud de URLs y base de datos para la fase de producción.

### Evidencia que soporta esta actividad

- `OE4-arquitectura/anexo-tecnico-servidor.md`, `OE4-arquitectura/solicitud-oti-urls-y-bd.md`.
- `infra/deploy/` (scripts de despliegue y cascada de APK); `srni-mobile/src/config/marca.ts`.

---

## Obligación 5 — Crear, diseñar y documentar la estructura de bases de datos

### Actividad desarrollada en este periodo

Se evolucionó el esquema de la base de datos local de la APK (migración v9: tabla de caché de miembros del hogar, que permite capturar offline hogares creados en línea). Se mantuvo y documentó la estructura de la base de datos del backend (PostgreSQL) para instrumentos, capítulos, preguntas, opciones y reglas.

### Evidencia que soporta esta actividad

- `srni-mobile/src/db/schema.ts` (migraciones versionadas); `OE5-bd/`.
- `docs/base-datos/mobile-sqlite.md`, `docs/base-datos/backend-postgresql.md`.

---

## Obligación 6 — Crear y documentar modelos de datos que reflejen con precisión la información

### Actividad desarrollada en este periodo

Se consolidaron los modelos de datos del instrumento (Instrumento, Capítulo, Pregunta, Opción de respuesta y Regla de lógica de saltos), incorporando el primer uso de reglas de tipo HABILITAR para los sub-campos condicionales (un campo numérico que aparece al responder "Sí"). Se documentó el flujo de definición del instrumento: modelo → fixture → carga → exportación al paquete móvil.

### Evidencia que soporta esta actividad

- `srni-backend/apps/formulario/models.py`; `OE6-modelos/`.
- `docs/INFORME-ARQUITECTURA-ESTADO.md` (sección "Modelo de datos del instrumento").

---

## Obligación 7 — Asistir a las reuniones programadas y las requeridas por el supervisor

### Actividad desarrollada en este periodo

Se participó en las reuniones de gestión del proyecto (PETI PRY-0662064) y en la coordinación con el equipo de desarrollo del panel web y la supervisión.

### Evidencia que soporta esta actividad

- `docs/gestion/acta-constitucion-PRY-0662064.md`; `OE7-reuniones/`.

---

## Obligación 8 — Cargar mensualmente los documentos en la ruta dispuesta por la Subdirección

### Actividad desarrollada en este periodo

Se elaboró y organizó la documentación técnica y de gestión del periodo (informe consolidado de arquitectura y estado, credenciales de pruebas, casos de víctimas funcionales, manual de uso y política de privacidad de la aplicación) para su cargue en la ruta dispuesta por la Subdirección.

### Evidencia que soporta esta actividad

- `docs/` (estructura ordenada por área); `OE8-informes/credenciales-usuarios-pruebas.md`, `OE8-informes/victimas-prueba-funcionales.md`.

---

## Obligación 9 — Cumplir las demás actividades acordadas con el supervisor

### Actividad desarrollada en este periodo

Se elaboró un informe consolidado de arquitectura y estado del proyecto (para onboarding y contexto), insumos para la presentación de avance (diapositivas y guion del video de lanzamiento de la APK) y los correos de coordinación con la OTI, el desarrollador del panel web, directivos y el equipo de diseño.

### Evidencia que soporta esta actividad

- `docs/INFORME-ARQUITECTURA-ESTADO.md`; `OE9-adicionales/resumen-diapositivas-avance-dificultad-solucion.md`.
- `EXTRAS-actividades-adicionales/` (correos e insumos de comunicación).
