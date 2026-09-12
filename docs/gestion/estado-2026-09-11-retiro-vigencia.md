# En qué quedamos — 11 de septiembre de 2026

**Asunto:** retiro del control de vigencia, pedido ese mismo día por el equipo de
caracterización.

## ✅ Está EN PRODUCCIÓN y verificado

El control se retiró la noche del 11-sep-2026. Comprobado contra el padrón real, no
contra pruebas:

| | Verificado |
|---|---|
| Interruptor | `BLOQUEO_ACTIVO = False` — preguntado al proceso, no al archivo |
| Repositorio | `VICTIMA_REPOSITORY = DJANGO` — el padrón real, no el mock |
| Persona con ficha vigente hasta dic-2026 | motivo `ELEGIBLE_SIN_CONTROL_VIGENCIA`, elegible, y **marcada para el libro** |
| La precarga que usa la APK sin señal | 199 de 199 con caracterización previa salen habilitadas |
| Migraciones | `encuestas.0010` y `hogares.0008` aplicadas |
| APK publicada | 1.2.5, versionCode 59, 76 MB, servida con el MIME correcto |
| Versión que anuncia la API | 1.2.5 / 10205 |
| Panel | sirviendo el bundle nuevo, con la pantalla **Recaracterizaciones** |
| Por el dominio institucional | `/` y `/api/movil/version/` en 200 |

**Para volver atrás:** `bash infra/deploy/scripts/retirar-control-vigencia.sh reponer`.
Las filas del libro se conservan: son el histórico.

### Lo que NO se abrió, y no se pudo verificar con dato real

Quien está **excluida del RUV** sigue bloqueada. No hay forma de comprobarlo en
producción porque **no existe ninguna fila excluida**: de 5.926.196 personas,
5.926.010 están en `NO_VERIFICADO` y 186 en `INCLUIDO`, resultado de la limpieza del
join roto (migración `victimas.0021`). Esa guarda queda cubierta por pruebas.

---

## Dos cosas que salieron mal al desplegar, y cómo quedaron

Las dos están corregidas y con script propio, pero conviene conocerlas porque las dos
fallan **en silencio**.

**El interruptor no llegaba al contenedor.** El `.env` decía `False` y Django seguía
viendo `True`: el compose tiene una lista explícita de variables y `--env-file` solo
interpola dentro de ese archivo, no inyecta nada en el contenedor. Ya declarada. El
compose documentaba esta misma trampa dos veces desde julio.

**Y el script dijo «RETIRADO ✅» de todos modos.** Ese era el defecto grave: se iba a
dictar la capacitación creyendo que el control estaba retirado. Ahora el script
pregunta al proceso y **falla con exit 1** si no coincide con el `.env`.

**El panel quedó en blanco respondiendo 200.** El `dist` del servidor era de `root`
—lo escribió el contenedor del build— y `sudo` cuelga la sesión SSH, así que los
bundles no se pudieron copiar; pero `index.html` sí era escribible y quedó apuntando
a un archivo inexistente. Resuelto con `infra/deploy/scripts/desplegar-panel.sh`, que
además nunca reemplaza el DIRECTORIO `dist`: `cz_nginx` lo monta por inode, y
cambiarlo lo dejaría sirviendo el panel viejo para siempre sin que ningún `curl` lo
delate.

---

## Lo que falta, y ya no es técnico

### 1. La instrucción escrita — lo único urgente

El correo de constancia está listo en
`docs/gestion/correo_retiro_control_vigencia_2026-09-11.md`. El cambio ya está en
producción por decisión de Javier; lo que falta es la línea de quien tiene competencia
sobre el Manual de Usuario §5.1.1 para el expediente.

**Importa el orden en que quedó:** se ejecutó primero y se pide la constancia después.
Es defendible —lo pidió el proceso por escrito y Javier tiene las decisiones de
negocio delegadas— pero conviene que la respuesta llegue antes del 15.

### 2. Probar en la APK, en este orden

1. **Cerrar sesión y volver a entrar con señal.** Es en el ingreso cuando el teléfono
   actualiza el padrón que usa sin conexión. Un celular con la sesión de días
   anteriores sigue diciendo «No habilitado» y no es un defecto.
2. Buscar a alguien caracterizado hace menos de dos años: debe salir habilitado.
3. Conformar su hogar: si lo creó otro encuestador, debe continuar **y mostrar la
   familia que ya estaba**.
4. Retirar a un integrante con motivo y fecha del hecho.
5. Cerrar la caracterización y ver la fila en el panel, en **Recaracterizaciones**.

El libro está en **0 filas**: nadie ha recaracterizado todavía. La primera fila es la
prueba de que la cadena completa funciona.

### 3. Lo que sigue abierto y no corre prisa

| | Qué | Por qué espera |
|---|---|---|
| 1 | Probar la **segunda escritura al Oracle** legacy sobre el mismo hogar | Los `GIC_*` tienen su propia regla de vigencia y pueden rechazarla —o aceptarla en silencio sin escribir—. Hoy no estorba: `ORACLE_SYNC_AUTOMATICA` está en `False` |
| 2 | Ajustar el **Manual de Usuario §5.1.1**, el documento misional | No es nuestro: lo define el proceso. El manual de uso de la APK ya está en 1.3 |
| 3 | Decidir si el soporte se **aplaza** o se **elimina** | Preguntado en el numeral 2 del correo. Si nadie contesta, queda eliminado y así consta |
| 4 | Que alguien **mire** el libro | Un registro que nadie consulta equivale a no tenerlo. Si en un mes nadie ha entrado a la pantalla, conviene decirlo antes de que lo pregunte control interno |

---

## Qué se construyó, y dónde está cada cosa

| | Qué | Dónde |
|---|---|---|
| 1 | Interruptor de vigencia | `settings.VIGENCIA['BLOQUEO_ACTIVO']` + compose + script |
| 2 | Libro de auditoría, escrito al cerrar la encuesta | `encuestas.RecaracterizacionVigente` |
| 3 | Punto de control: API + pantalla del panel | `/api/recaracterizaciones/`, `Recaracterizaciones.tsx` |
| 4 | Retiro de integrantes del hogar | `hogares.MiembroHogar` + acciones `retirar`/`reincorporar` |
| 5 | Salida del hogar y de la sesión (los dos 409) | `hogares/views.py`, `encuestas/views.py` |
| 6 | Sin señal también funciona | precarga + `authStore.cargarPerfil` |
| 7 | Los cuatro defectos de «no RUV» | 1.2.4 y 1.2.5 |
| 8 | Material de capacitación | cuestionario, anexos, manual 1.3, plan, 3 PDF |
| 9 | Tres scripts de despliegue con las trampas adentro | `desplegar-backend-codigo.sh`, `retirar-control-vigencia.sh`, `desplegar-panel.sh` |

Detalle técnico y el por qué de cada decisión:
`docs/operacion/plan_registro_silencioso_vigencia.md`.

**Pruebas:** 1.184 backend · 156 móvil · 19 panel. Verde al momento del despliegue.

---

## Una cosa fácil de leer al revés

**`dias_restantes` cuenta los días que le FALTABAN a la ficha por vencer.** El número
más alto es la recaracterización más temprana y por tanto la más grave: 723 significa
que la caracterización anterior tenía una semana.

La pantalla del panel ya lo traduce a «hace 7 días» y colorea por gravedad, pero quien
consulte la API directamente tiene que saberlo, o va a ordenar al contrario y dejar
fuera exactamente los casos que busca.
