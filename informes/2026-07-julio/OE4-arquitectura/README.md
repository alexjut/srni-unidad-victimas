# OE4 — Diseño e implementación de soluciones tecnológicas

> **Obligación contractual:** *Realizar el diseño e implementación de las soluciones tecnológicas y aplicativos móviles que genere la Subdirección Red Nacional de Información para el procedimiento de Instrumentalización de la Información.*

## Actividad desarrollada en este periodo

- **Cascada del correctivo del módulo B** a producción: publicación del commit `3249a85`
  en ambos remotes (GitHub + Azure DevOps) sobre `main`.
- Decisión de arquitectura sobre el **versionado del instrumento**: se documentó que los
  bundles se compilan en el APK (`require` por nombre) y se sirven desde memoria — no hay
  re-descarga runtime; la entrega del instrumento nuevo es la **cascada del APK**. Por eso
  el correctivo **no bumpea la versión** (V7/V1), manteniendo el UUID del instrumento
  estable para no romper sesiones en curso.
- Pendiente de despliegue en el servidor: `cargar_perfil` + `exportar_a_mobile` (reconcilia
  el UUID de la nueva pregunta B2_CANT entre BD y bundle) + build/publicación del APK.

## Evidencia que soporta esta actividad

- Push a producción: `cfd95fe..3249a85 main -> main` (GitHub + Azure DevOps).
- Memoria técnica del pipeline de instrumentos y del versionado (decisión "no bump").
