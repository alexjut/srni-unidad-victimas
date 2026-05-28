# OE7 — Reuniones y coordinación con supervisor

> **Obligación contractual:** *Asistir a las reuniones programadas para tratar temas relacionados con el desarrollo del objeto del contrato y las demás que sean requeridas por el supervisor.*

## Actividad desarrollada en este periodo

Durante mayo 2026 se asistió a las reuniones de coordinación con el supervisor Oscar Andrés Manosalva García y con el equipo de Caracterización SRNI. Las reuniones de equipo permitieron identificar hallazgos críticos del aplicativo móvil que se atendieron como sprints inmediatos (por ejemplo, el equipo SRNI envió evidencias gráficas el 26/05 mostrando que los 8 instrumentos debían comenzar con un capítulo de Información General de Atención —Dirección Territorial, Departamento, Punto y Municipio de Atención—, lo que se resolvió en el mismo día con el Sprint 19 completo: modelado backend, endpoints de cascada, pantalla móvil con cache local y limpieza de bundles). Adicionalmente se realizó coordinación técnica con el desarrollador del panel web (Brando) mediante un correo formal de onboarding (`docs/correo-brando.md`) que documenta credenciales, endpoints disponibles, procedimiento para solicitar endpoints nuevos y reporte de fallos. *(Sección a complementar por el contratista con las actas firmadas, listados de asistencia y presentaciones formales de cada reunión)*.

## Evidencia que soporta esta actividad

- **Correo de coordinación con frontend (versionado):** `docs/correo-brando.md`.
- **Integración de trabajo del equipo:** commit de merge `d7c9edb` que integró 5 commits del desarrollador frontend Brando sin pisar su trabajo.
- **Hallazgos del equipo SRNI atendidos en sprints inmediatos:** Sprint 19 (capítulo Información General de Atención), Sprint 20 (nombres descriptivos de instrumentos), Sprint 20-QA-B (render selector municipio), Sprint 21 (preguntas por miembro + calendario + wizard).
- **Anexos a aportar por el contratista:**
  - [ ] Acta de reunión inicial de contrato (abril 2026)
  - [ ] Acta de reunión de georreferenciación (21/05/2026)
  - [ ] Listado de asistencia al Taller Aplicativo Tupago (20/05/2026)
  - [ ] Presentación de avance Mayo (PPTX entregado al supervisor)
  - [ ] Correos de retroalimentación de Oscar
  - [ ] Audios o capturas de las reuniones semanales

---

## Actividades del cronograma

1. Reunión semanal con supervisor Oscar Andrés Manosalva García
2. Reuniones con equipo de Caracterización SRNI
3. Presentaciones de avance a jefatura

## Reuniones del mes (a completar Javier)

> **Importante:** este OE depende de documentación que NO está en el repo de código. El contratista debe anexar:
> - Actas firmadas o capturas de los encuentros
> - Listados de asistencia
> - Presentaciones (PPTX) que ya están en `docs/perfiles/` o externos

### Plantilla por reunión

| Fecha | Tipo | Asistentes | Tema | Decisiones | Anexo |
|---|---|---|---|---|---|
| _DD/MM/2026_ | _semanal supervisor / equipo SRNI / jefatura_ | _Oscar M., Javier A., …_ | _resumen 1 línea_ | _decisiones tomadas_ | _archivo.pdf_ |

## Lo que sí tenemos del repo

- **Hallazgo del 26/05** (capturas WhatsApp): el equipo SRNI envió 4 imágenes del APK mostrando que los 8 instrumentos deben comenzar con preguntas DT/Depto/Punto/Mun de atención. Resultado: Sprint 19 completo en el día.
- **Pull request a Brando (26/05):** se envió correo con backend habilitador + cómo solicitar endpoints. Archivo: `docs/correo-brando.md`
- **Iteraciones de UX con Javier (26/05):** 9 ciclos de feedback durante la misma jornada (códigos confusos → nombres descriptivos; lista de miembros en scroll → wizard; input fecha manual → calendario; títulos → nombre real del miembro).

## Documentos referenciados (anexos a complementar)

### Anexos del contratista

- [ ] Acta reunión inicio de contrato (abril)
- [ ] Acta georreferenciación (PDF detectado en raíz del proyecto, 21/05)
- [ ] Listado asistencia taller aplicativo Tupago (PDF detectado, 20/05)
- [ ] Presentación de avance Mayo (PPTX detectado, "Informe_Avance_Caracterizacion_SRNI.pptx")
- [ ] Audios de reuniones con equipo SRNI

### Anexos del supervisor

- [ ] Correos de retroalimentación de Oscar
- [ ] Actas de comité técnico (si aplica)

## Archivos relevantes en el repo

- `docs/correo-brando.md` — coordinación con Brando (frontend)

## Pendientes (a complementar Javier)

- Anexar todos los anexos listados arriba
- Resumen ejecutivo de las reuniones del mes (1-2 párrafos)
- Compromisos pendientes que quedaron de cada reunión
