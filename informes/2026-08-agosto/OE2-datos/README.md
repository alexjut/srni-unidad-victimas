# OE2 — Captura, procesamiento y calidad de datos

> **Obligación contractual:** *Realizar la captura, el procesamiento, la transformación y la gestión de calidad de datos de las fuentes recibidas por la entidad en el desarrollo de las mediciones para las soluciones tecnológicas y aplicativos móviles.*

## Actividad desarrollada en este periodo

El trabajo del mes sobre datos se concentró en la **calidad de la identidad** del
padrón, porque es lo que sostiene toda la operación: si el sistema no reconoce bien
a una persona, o le atribuye datos de otra, todo lo demás falla.

- **Documentos repetidos clasificados.** El padrón trae **768.096 documentos
  compartidos por más de un registro**. Se midió —no se supuso— que el **92 % son la
  misma persona** cargada más de una vez por el sistema de origen, y solo el ~7 %
  son personas distintas con el mismo número. Con esa clasificación, el sistema deja
  de pedir confirmación en el caso masivo y solo la pide cuando de verdad hay
  ambigüedad de identidad.
- **Colapso por identidad en la búsqueda.** Ese mismo criterio se aplicó al panel:
  al buscar una persona en autorizaciones dejó de aparecer repetida (hallazgo
  H-025), colapsando los registros que son la misma persona igual que ya lo hacía la
  búsqueda de víctimas.
- **Estado NO_VERIFICADO.** Se consolidó un estado propio para quien **no aparece en
  el padrón descargado**, distinto de "no está en el registro de víctimas". La
  diferencia importa: no se le puede negar a nadie su condición por el hecho de que
  su ficha aún no esté materializada; se marca como *sin verificar* y se resuelve al
  autorizar (ver OE4).
- **Blindaje del cruce entre fuentes.** Se dejó explícito y con guardas que el
  enlace entre el padrón y el universo se hace por **número de documento**, nunca por
  el identificador interno, porque se midió que esos identificadores no coinciden
  entre los dos sistemas (ver OE5).

## Evidencia que soporta esta actividad

- `docs/oracle-legacy-padron/decision_documentos_duplicados.md` — 768.096 repetidos,
  92 % misma persona, criterio de clasificación.
- Comando de clasificación:
  `srni-backend/apps/victimas/management/commands/clasificar_colisiones.py`.
- Colapso por identidad en autorizaciones: commit `d949ec2` (H-025).
- Estado NO_VERIFICADO: `docs/ciclo_completo_tablas.md` §6; migraciones
  `victimas/0008`, `victimas/0009`, `hogares/0007`.

## Evidencia física recolectada

Archivos en [`evidencias/`](evidencias/):

| Archivo | Qué prueba |
|---|---|
| `commits-datos-agosto.txt` | Commits del mes sobre padrón, universo, identidad y duplicados (compartido con OE5) |

## Pendiente / siguiente paso

- Mostrar en el panel el aviso de "coincidencia solo por número" cuando aplique
  (tarea de frontend, Brando).
- Depurar contra la fuente los ~7 % de documentos con personas realmente distintas.
