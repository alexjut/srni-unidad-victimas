# OE8 — Carga mensual de documentos

> **Obligación contractual:** *Cargar mensualmente en la ruta dispuesta por la Subdirección todos los documentos que den cuenta de la gestión realizada en el contrato.*

## Actividad desarrollada en este periodo

Durante mayo 2026 se elaboró el **informe mensual completo** del período, estructurado por las 9 obligaciones específicas del cronograma del contrato 2226-2026 (carpeta `informes/2026-05-mayo/` versionada en el repositorio oficial UARIV en Azure DevOps y backup en GitHub). El informe incluye: un README global con resumen ejecutivo del mes (80 commits, 16 sprints completados, indicadores cuantitativos), 9 subcarpetas con un README cada una documentando actividad desarrollada, evidencias y archivos físicos copiados (total 35 archivos autocontenidos), y una carpeta adicional `EXTRAS-actividades-adicionales/` con el trabajo ejecutado por iniciativa del contratista por fuera del cronograma (mejoras UX, refactors técnicos preventivos, auditoría de seguridad propia, higiene del repositorio, automatizaciones, documentación adicional, coordinación de equipo). Adicionalmente se generaron anexos automatizados: log completo de los 80 commits del mes (`git-log-mayo-2026.txt`), snapshot del estado del proyecto (`estado-actual.md`), reporte automatizado de QA por instrumento (`qa-perfiles-sprint20.md`) y correo de onboarding para el desarrollador del panel web (`correo-brando.md`). *(Falta por parte del contratista: completar el formato oficial UARIV con plantilla del supervisor, firmar el PDF, cargar a SECOP II y subir la carpeta a OneDrive del supervisor)*.

## Evidencia que soporta esta actividad

- **Informe mensual estructurado:** `informes/2026-05-mayo/` (carpeta versionada en repositorio Git oficial UARIV y backup GitHub).
- **README global con resumen ejecutivo:** `informes/2026-05-mayo/README.md`.
- **9 README por obligación + EXTRAS:** un archivo por carpeta `OE1-desarrollo/` a `OE9-adicionales/` + `EXTRAS-actividades-adicionales/`.
- **35 archivos físicos copiados** (autocontenidos para SECOP II / OneDrive sin dependencia del repo).
- **Anexos automatizados generados en esta carpeta:**
  - `git-log-mayo-2026.txt` — lista completa de 80 commits del mes
  - `estado-actual.md` — snapshot del proyecto al 28/05
  - `qa-perfiles-sprint20.md` — reporte automatizado de QA
  - `correo-brando.md` — onboarding técnico para frontend
- **Commits de generación del informe:** `6462314` (carpeta inicial) + `7d1a6b9` (EXTRAS).
- **Pendientes a cargo del contratista:**
  - [ ] Formato oficial UARIV firmado en PDF
  - [ ] Carga en SECOP II
  - [ ] Carga en OneDrive del supervisor: `Caracterizacion-Victimas/2026/05-Mayo/`
  - [ ] Correo de notificación al supervisor con los enlaces

---

## Actividades del cronograma

1. Informe mensual Abril — formato entidad + SECOP II + OneDrive
2. **Informe mensual Mayo** — formato entidad + SECOP II + OneDrive  ← (este)
3. Informe mensual Junio — pendiente
4. Informe final Julio — pendiente

## Entrega Mayo 2026

Este informe es el documento físico que se carga en los 3 destinos:

| Destino | Estado | Notas |
|---|---|---|
| Formato entidad UARIV | 📝 a generar con plantilla oficial | Tomar contenido de las 9 carpetas OE |
| SECOP II | 📝 PDF firmado del informe + soportes | Subir a https://community.secop.gov.co |
| OneDrive del supervisor | 📝 carpeta `Caracterizacion-Victimas/2026/05-Mayo/` | Estructura propuesta abajo |

## Estructura sugerida para OneDrive

```
Caracterizacion-Victimas/
└── 2026/
    └── 05-Mayo/
        ├── 00-Informe-Mayo.pdf              (informe firmado)
        ├── 01-OE1-Desarrollo/               (snapshot de carpeta OE1)
        ├── 02-OE2-Datos/
        ├── 03-OE3-Seguridad/
        ├── 04-OE4-Arquitectura/
        ├── 05-OE5-BD/
        ├── 06-OE6-Modelos/
        ├── 07-OE7-Reuniones/                (con actas y presentaciones)
        ├── 08-OE9-Adicionales/              (con soportes de pago, accesos, etc.)
        └── 99-Anexos-tecnicos/
            ├── repositorio-git-log-mayo.txt
            ├── reporte-qa-perfiles.md
            └── correo-brando.md
```

## Anexos técnicos generados automáticamente

Copias locales en esta carpeta:

- [`git-log-mayo-2026.txt`](git-log-mayo-2026.txt) — lista completa de 80 commits del mes
- [`estado-actual.md`](estado-actual.md) — snapshot del proyecto al 28/05
- [`qa-perfiles-sprint20.md`](qa-perfiles-sprint20.md) — reporte automático de QA
- [`correo-brando.md`](correo-brando.md) — documento para frontend (Brando)

## Pendientes (a complementar Javier)

- [ ] Completar formato oficial UARIV (plantilla del supervisor)
- [ ] Firmar PDF
- [ ] Subir a SECOP II
- [ ] Cargar carpeta a OneDrive
- [ ] Notificar a Oscar por correo con los enlaces
