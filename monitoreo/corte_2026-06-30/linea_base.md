# Línea base del proyecto al corte — 30 de junio de 2026

**Proyecto:** PRY-0662064 — Modernización de la entrevista de caracterización · APK (SICAV Móvil)
**Corte:** 2026-06-30 23:59:59 −05:00
**Repositorio:** `srni-unidad-victimas` (Azure DevOps oficial UARIV · espejo GitHub)
**Elaborado:** 6 de agosto de 2026, para el repositorio de Gerencia de Proyectos del PETI

> **Trazabilidad.** Todo lo que sigue se derivó del repositorio con los comandos que se
> citan en cada sección. Lo que no se pudo derivar está marcado
> **`[NO DETERMINADO — verificar]`** y no se estimó.

---

## 0. Punto de corte exacto

```
commit del corte : 5fba1fa682c109089ccd397ecffc86cce6c4ac67
fecha            : 2026-06-30 19:15:42 −05:00
asunto           : feat(ui): integra gov-amarillo — franja full-width, sidebar activo,
                   badges EN_PROGRESO, Alert warning, Pagination dot, PageHeader accent
```

Obtenido con `git rev-list -1 --before='2026-06-30 23:59:59 -0500' main`. **Todas las
cifras de este documento se midieron sobre ese commit**, no sobre el estado actual del
repositorio.

## 1. Actividad registrada

| Mes | Commits (sin merges) |
|---|---:|
| Abril 2026 | 24 |
| Mayo 2026 | 110 |
| Junio 2026 | 151 |
| **Total al corte** | **285** |

El repositorio **inicia el 13 de abril de 2026** (`b08bc47 — chore: initial commit`). No
hay actividad registrada entre enero y el 12 de abril: el rango solicitado
(`--since=2026-01-01`) no arroja nada anterior a esa fecha.

```bash
git log 5fba1fa --since=2026-01-01 --date=short --pretty=format:'%ad|%h|%s' --no-merges
```

Salida completa: [`soportes/commits_al_corte.txt`](soportes/commits_al_corte.txt) (285 filas).

## 2. Sprints

**Cerrados al corte: 21 de 21.** El último commit con marca de sprint es del **26 de mayo
de 2026**; junio se trabajó como flujo continuo sobre `main`, sin numeración de sprint
(auditoría de la APK, instrumento Territorial V7, marca e identidad, despliegue).

| Sprint | Último commit ≤ corte | Sprint | Último commit ≤ corte |
|---|---|---|---|
| 2 | 2026-04-13 `12c7d7b` | 12 | 2026-05-25 `f6902e7` |
| 3 | 2026-04-16 `ec50cb3` | 13 | 2026-05-25 `f442e1f` |
| 4 | 2026-04-19 `6a66d64` | 14 | 2026-05-25 `908dc4b` |
| 5 | 2026-04-19 `2abf579` | 15 | 2026-05-25 `27dbe60` |
| 6 | 2026-04-28 `10d98c8` | 16 | 2026-05-25 `b187b3b` |
| 7 | 2026-05-21 `4742167` | 17 | 2026-05-26 `a1c976f` |
| 8 | 2026-05-21 `2c5230c` | 18 | 2026-05-26 `f71fb1c` |
| 9 | 2026-05-21 `6648be8` | 20 | 2026-05-26 `771761e` |
| 10 | 2026-05-21 `9373d0b` | 21 | 2026-05-26 `0aa818d` |
| 11 | 2026-05-21 `5ff906b` | | |

*(Los sprints 1 y 19 no usan el prefijo `sprint<N>` en el asunto del commit; sí tienen
documento de cierre —`docs/sprints/sprint-01.md` y el trabajo de ubicación de atención—,
por lo que se cuentan como cerrados. Criterio: existe documento de sprint **y** commits
asociados anteriores al corte.)*

**Documentados en `docs/sprints/` al corte: 16 archivos** (sprint-01 a sprint-15 y
sprint-18-arquitectura). Los sprints 16, 17, 19, 20 y 21 tienen commits pero **no tienen
documento de cierre propio** al corte — es una brecha de documentación, no de ejecución.

## 3. Tags y versiones liberadas

> ### ⚠️ El repositorio **no tiene ni un solo tag de Git**
> ```
> git tag → (0 resultados)
> ```
> **No existe versionado por tags**, así que las versiones liberadas **no se pueden
> derivar de la forma solicitada**. Lo que sigue proviene de commits y documentos, y es
> más débil como evidencia.

| Entregable | Evidencia al corte | Ambiente |
|---|---|---|
| APK builds **#15 y #16** (EAS) | `docs/estado-actual.md` §0 y `informes/2026-06-junio/README.md` (OE1) | Publicados al servidor con QR estable |
| Renombre a **"SICAV Móvil"** | `99403cd` (2026-06-30) | Código |
| Backend en `30.0.1.109:8090` | `infra/deploy/README.md`, `docs/INFORME-ARQUITECTURA-ESTADO.md` | Servidor institucional UARIV |

**`[NO DETERMINADO — verificar]`** el número de versión formal (`versionName`/`versionCode`)
de cada APK entregada y **la fecha exacta de publicación de cada build**: no hay tags,
ni changelog de versiones, ni registro de entregas en el repositorio al corte.

**Recomendación para la próxima entrega:** etiquetar cada APK liberada
(`git tag -a apk-v1.2 -m "..."`). Sin eso, ninguna entrega futura será auditable por fecha.

## 4. Módulos con código funcional al corte

### Backend — 11 módulos (`srni-backend/apps/`), 204 archivos `.py`

`auditoria` · `autenticacion` · `encuestas` · `formulario` · `hogares` · `ia` · `movil` ·
`parametricas` · `reportes` · `sincronizacion` · `victimas`

Cubre los **siete módulos comprometidos** en el acta (§3): víctimas, hogares, encuestas,
formulario/instrumentos, paramétricas, autenticación y auditoría — más cuatro no
comprometidos (`ia`, `movil`, `reportes`, `sincronizacion`).

### Aplicación móvil — 77 archivos `.ts/.tsx`

Con los **8 instrumentos empaquetados** para operación sin conexión:

```
asistencia_v8 · buenaventura_v7 · rural_etnico_v1 · san_andres_v7
telefonico_v8 · territorial_v7 · urbano_etnico_v1 · victimas_exterior_v1
```

### Panel web — 37 archivos `.js/.jsx/.tsx` (74 archivos en total)

En desarrollo por Brando al corte (`docs/frontend/estado-actual.md`).

### No iniciado al corte

| Componente | Estado al 30-jun | Fuente |
|---|---|---|
| Integración productiva con Oracle/RUV real | **No iniciada** — excluida del alcance por el acta §3 mientras la OTI no habilite | `docs/gestion/acta-constitucion-PRY-0662064.md` |
| Aplicación iOS | **No iniciada** — excluida explícitamente del alcance | ídem |
| Exposición a internet del servicio | **No iniciada** — en trámite por comité de cambios | ídem |

## 5. ADR (decisiones de arquitectura)

> ### ⚠️ No existe la carpeta `doc/adr/`, y **no hay ADR formales al corte**
> El único documento con formato ADR del repositorio es
> `docs/arquitectura/adr-padron-universo-victimas.md`, fechado **5 de agosto de 2026** —
> **posterior al corte**, por lo que **no cuenta** para este monitoreo.

El informe de junio lo reconoce como pendiente del propio mes: *"ADRs nuevos (decisiones
de mayo/junio que no estaban formalizadas)"*.

Documentos de arquitectura **que sí existían** al corte y cumplen función equivalente:

| Documento | Qué decide/documenta |
|---|---|
| `docs/arquitectura/ARQUITECTURA.md` | Arquitectura general de la solución |
| `docs/arquitectura/ANALISIS_APK.md` | Análisis de la APK original a replicar |
| `docs/arquitectura/plan-offline-precarga.md` | Estrategia de pre-carga para operación sin conexión |
| `docs/arquitectura/plan-prellenado-ruv.md` | Reutilización de datos del RUV |
| `docs/INFORME-ARQUITECTURA-ESTADO.md` | Informe consolidado de arquitectura y estado |

## 6. Documentación de soporte al corte

**49 documentos `.md`** bajo `docs/` al 30 de junio. Los de valor probatorio para el PETI:

| Documento | Sirve como soporte de |
|---|---|
| `docs/gestion/acta-constitucion-PRY-0662064.md` | Constitución del proyecto (18-jun-2026) |
| `docs/INFORME-ARQUITECTURA-ESTADO.md` | Arquitectura y estado consolidado |
| `docs/estado-actual.md` | Estado del proyecto (corte 23-jun-2026) |
| `docs/auditoria-pre-tiendas-2026-06-10.md` | Auditoría previa a publicación (10-jun-2026) |
| `docs/gestion/respuesta-analisis-seguridad-2026-06.md` | Atención a análisis de seguridad (jun-2026) |
| `docs/qa-perfiles-sprint20.md` | QA por perfil de instrumento |
| `docs/publicacion/manual-de-uso-srni-mobile.md` | Manual de uso de la aplicación |
| `docs/publicacion/politica-privacidad-srni-mobile.md` | Política de privacidad (Ley 1581) |
| `docs/backend/seguridad.md` | Medidas de seguridad y protección de PII |
| `informes/2026-05-mayo/` y `informes/2026-06-junio/` | Informes mensuales por obligación contractual |

Inventario completo con rutas: [`soportes/INDICE.md`](soportes/INDICE.md).

---

## 7. Lo que este documento NO pudo determinar

| Campo | Por qué |
|---|---|
| **Cronograma aprobado con fechas** | El acta §6 tiene 5 hitos y **3 dicen `[Por completar]`**. Sin fechas planeadas **no se puede calcular avance planeado ni desviación** |
| **Patrocinador del proyecto** | El acta lo deja en `[Por completar]` |
| **Presupuesto** | El acta §10 lo deja en `[Por completar]` |
| **Versiones formales de APK y fechas de entrega** | No hay tags ni changelog (§3) |
| **Actas de reunión firmadas** | El informe de junio marca OE7 como *"📝 Pendiente actas"* |
