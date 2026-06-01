# EXTRAS — Actividades adicionales por fuera del cronograma

> Trabajo ejecutado durante Mayo 2026 que **no estaba listado** en las 9 obligaciones
> específicas (OE1-OE9) del cronograma del contrato 2226-2026, pero que se realizó
> por iniciativa del contratista para mejorar calidad, seguridad o usabilidad del
> sistema. Se documenta para constancia del supervisor.

---

## 1. Mejoras de UX no pedidas (calidad del producto)

| Mejora | Sprint | Beneficio | Commit |
|---|---|---|---|
| Renombrado descriptivo de los 8 instrumentos | 20 | El encuestador deja de confundir "Perfil Asistencia" con otros — nombres claros tipo "Asistencia humanitaria", "Caracterización territorial" | `771761e` |
| Selector de Municipio con search bar (DIVIPOLA) | 20-QA-B | Las 16 preguntas COMBO_DINAMICO que antes no renderizaban (depto/mun) ahora son dropdown con búsqueda sobre 1102 municipios | `4a0130b` |
| Calendario nativo en preguntas FECHA | 21-D | Reemplaza input manual "AAAA-MM-DD" por picker del SO. Cero errores tipográficos, no permite fechas imposibles | `fb75ca2`, `eab3075` |
| Headers con nombre real del miembro | 21-E | En hogares grandes, "Autorizado · JAVIER AGUILAR" reemplaza el genérico "AUTORIZADO · Cabeza de hogar" | `e847990` |
| Wizard 1-miembro-a-la-vez con Anterior/Siguiente | 21-F | UX profesional: en lugar de scroll vertical largo con 5 miembros × 100 preguntas = 500 preguntas seguidas, navegación lineal por persona | `be8755e` |
| Hub de caracterizaciones por hogar | 14 | Refactor del flujo: en lugar de botones sueltos, todo entra por un hub central | `908dc4b`, `dba81ce` |
| Migas de pan + back navegación coherente | 17 | No se salta al home por error; el botón atrás vuelve al paso anterior | `b65188a` |
| Login con biometría auto-habilitada | 7 | Primer login pide huella/Face ID automáticamente si el dispositivo soporta | `4742167` |
| Imagen indígena auténtica en pantalla búsqueda | 7 | Visual GOV.CO institucional con imagen real de unidadvictimas.gov.co | `4742167` |

## 2. Refactors técnicos por iniciativa propia (deuda técnica preventiva)

| Refactor | Sprint | Por qué | Commit |
|---|---|---|---|
| Arquitectura in-memory para instrumentos | 18 / F1B | Elimina el "database is locked" recurrente. Instrumentos viven en RAM desde bundle JSON, no en SQLite. Performance +10x | `2f6811f`, `e8b1ef6` |
| Mutex global para escrituras SQLite | 18-C | Antes había colisiones cuando cola + borradores + instrumento escribían al mismo tiempo | `31d3477` |
| `busy_timeout = 5000` en SQLite | 18 | SQLite espera 5s en lugar de fallar instantáneamente al colisionar | `f71fb1c` |
| Migration V4: drop tablas de instrumento obsoletas | 18-F | Limpieza del schema mobile (post in-memory) | `e820e32` |
| Migration V5: respuestas.miembro_id + nuevo UNIQUE | 21 | Habilita preguntas PERSONA por miembro sin breaking change | `c9248da` |
| `instrumento_codigo` de sesión como autoridad única | 18-B | Elimina ambigüedad cuando el cliente y el servidor disagree | `478b305` |
| Single perfil en memoria + GC del anterior | 18-C | Previene fugas de memoria al cambiar de instrumento | `31d3477` |

## 3. Auditoría y seguridad por iniciativa propia

| Hallazgo y fix | Sprint | Severidad | Commit |
|---|---|---|---|
| Redactor PII en logs remotos del interceptor axios | 18-G | 🔴 Alta — la URL de búsqueda RNI con número_documento se enviaba al endpoint `/api/_debug/log/` | `d289a7c` |
| Identificación de 5 endpoints PII a redactar | 18-G | Alta — `/api/victimas/`, `/api/hogares/`, `/api/encuestas/`, `/api/auth/login/`, `/api/auth/cambiar-password/` | `d289a7c` |
| ErrorBoundary global mobile + endpoint `/api/_debug/log/` | 17 | Captura errores del celu para debugging remoto | `837519b` |
| Logger remoto activo (log.event / warn / error) | 17 | Visibilidad de problemas en producción | `b515004` |

## 4. Higiene del repositorio Git (gobernanza)

| Acción | Estado |
|---|---|
| Consolidación de 15+ ramas `feature/sprintX` → 3 ramas vivas (`main`, `frontend`, `develop`) | ✅ Completo |
| Configuración doble remote `azure` (oficial UARIV) + `origin` (GitHub backup) | ✅ Completo |
| Alias `git push all` que pushea a ambos remotes simultáneamente | ✅ Configurado |
| Convención post-Sprint 16: NO crear `feature/sprintX`, usar `feat(sprintX):` en commit messages | ✅ Documentado en CLAUDE.md |
| `.gitignore` expandido (Excel UARIV, capturas, PDFs, package-lock frontend) | ✅ `81a9e00` |
| `CLAUDE.md` destrackeado (sigue local, no se sincroniza) | ✅ `81a9e00` |
| Sincronización de las 3 ramas en los 2 remotes — mismo commit en 6 ubicaciones | ✅ Continua |

## 5. Automatizaciones (productividad propia y del equipo)

| Automatización | Archivo | Beneficio |
|---|---|---|
| Script `arrancar-backend.ps1` | raíz del repo | Activa venv, aplica migraciones, abre puerto firewall, arranca runserver. Ejecutar 1 comando |
| Script `arrancar-mobile.ps1` | raíz del repo | Detecta IP local automáticamente, actualiza `.env.local`, verifica backend, arranca Expo. Sin tocar config manual al cambiar de wifi |
| Script `qa_perfiles.py` | `srni-backend/scripts/` | Compara BD vs Bundle JSON automáticamente. Detecta discrepancias, capítulos vacíos, opciones faltantes. Reporte regenerable |
| Script `extraer_municipios_divipola.py` | `srni-backend/scripts/` | Extrae los 1102 municipios DANE del Excel oficial UARIV. CSV listo para cargar |
| Script `probar_cascada_atencion.py` | `srni-backend/scripts/` | Probador end-to-end de los 4 endpoints de la cascada DT→Depto→Mun + Punto |
| Script `probar_respuestas_persona.py` | `srni-backend/scripts/` | Probador end-to-end de la validación HOGAR vs PERSONA en respuestas |
| Comando `cargar_capitulo_control.py` | `srni-backend/...` | Carga las 3 preguntas estándar T1/T2/T3 que faltaban en TERRITORIAL y TELEFONICO |
| Comando `renombrar_instrumentos.py` | `srni-backend/...` | Renombra los 8 instrumentos a nombres descriptivos (reversible) |
| Comando `desactivar_preguntas_atencion.py` | `srni-backend/...` | Desactiva las 4 preguntas obsoletas DT_/DEPTO_/PUNTO_/MUN_ (con `--revertir`) |
| Generador automático de bundles `exportar_a_mobile.py` | `srni-backend/...` | Toma los instrumentos de BD y genera los 8 JSONs en `srni-mobile/assets/` |

## 6. Documentación adicional generada

| Documento | Ubicación | Propósito |
|---|---|---|
| `docs/estado-actual.md` | repo | Snapshot completo del proyecto, regenerable |
| `docs/qa-perfiles-sprint20.md` | repo | Reporte automático QA por instrumento |
| `docs/correo-brando.md` | repo | Onboarding técnico permanente para Brando (incluye cómo solicitar endpoints) |
| `docs/sprints/sprint-07.md` a `sprint-11.md` | repo | Bitácora detallada de cada sprint |
| `informes/2026-05-mayo/` | repo | Este informe mensual organizado por las 9 OE + extras |

## 7. Coordinación de equipo (con Brando, frontend web)

| Acción | Resultado |
|---|---|
| Identificación de mismatches del front (Sprint 20) | 5 endpoints + 6 campos de shape requerían alias |
| Creación de aliases en el backend sin tocar `srni-frontend/` | Brando no debe modificar su código para conectarse |
| Correo formal con credenciales + endpoints + cómo solicitar nuevos | `docs/correo-brando.md` |
| Sincronización de rama `frontend` con `main` y push a ambos remotes | Brando hace `git pull` y queda al día |
| Integración del trabajo de Brando en `main` (sin pisar) | 5 commits suyos integrados con merge |

## 8. Resolución de hallazgos del equipo SRNI

| Hallazgo (origen) | Resultado | Sprint |
|---|---|---|
| Equipo SRNI envía 4 imágenes WhatsApp del APK mostrando capítulo "INFORMACION GENERAL" faltante | Sprint 19 completo en el día: 5 fases A-E |
| Javier reporta nombres confusos ("perfil asistencial") | Sprint 20 — renombrado descriptivo + cap T cargado |
| Javier reporta "solo veo algunas preguntas no todas" | Sprint 20-QA-B — render COMBO_DINAMICO con selector de municipio |
| Javier reporta preguntas PERSONA deben ser por miembro | Sprint 21 completo: backend + DAO + UI + wizard |
| Javier reporta fecha como input manual en agregar miembro | Sprint 21-D fix: SelectorFecha en conformar y búsqueda RNI |
| Javier reporta wizard mejor que scroll largo | Sprint 21-F: wizard 1-a-la-vez con Anterior/Siguiente |

## 9. Métricas del esfuerzo extra

| Métrica | Valor |
|---|---|
| Sprints técnicos completados en mayo | 16 (6 a 21) |
| Commits firmados | 80 |
| Comandos Django nuevos | 6 |
| Scripts Python auxiliares | 5 |
| Scripts PowerShell de arranque | 2 |
| Endpoints REST nuevos en backend | 28+ |
| Componentes UI reusables nuevos en mobile | 3 (`SelectorMunicipio`, `SelectorFecha`, `ErrorBoundary`) |
| Schemas SQLite migrados | 2 (V4 → V5) |
| Migraciones Django nuevas | 9 |

## Cierre

Estas actividades **no estaban en el cronograma** del contrato pero se ejecutaron por iniciativa del contratista buscando calidad, seguridad y usabilidad del sistema entregable. Se documentan para constancia del supervisor.

— Javier Alexander Aguilar Castro · Mayo 2026
