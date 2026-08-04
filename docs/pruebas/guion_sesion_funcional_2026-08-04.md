# Guion de la sesión funcional — 4 de agosto de 2026

**Guion del conductor.** Sigue la agenda del correo, bloque por bloque, con el
minutado, lo que se dice, lo que se hace y **qué sería un fallo** en cada caso.

Cada prueba tiene tres partes, y la tercera es la que importa:

| | |
|---|---|
| **Qué se hace** | los pasos, en orden |
| **Qué debe pasar** | el comportamiento correcto |
| **Qué sería un fallo** | lo que hay que mirar de verdad — varios de estos defectos producen una respuesta **perfectamente creíble** cuando están mal |

> ⚠️ **Las pruebas se hacen sobre el padrón real.** Son 5.926.004 víctimas con
> datos personales verdaderos. **No son datos de prueba.** Los documentos de cada
> caso se sacan de la base en el momento con los comandos de este guion, se usan
> en la sesión y **no se escriben en actas, chats ni correos**.

---

## 0. Antes de que entre nadie (15 min antes)

| Qué verificar | Cómo | Qué esperar |
|---|---|---|
| El backend responde | abrir `https://caracterizacion.unidadvictimas.gov.co/api/` | **200** |
| El dominio va por HTTPS | abrir el dominio en el navegador | sin advertencia de certificado |
| La APK del día | descargar de `/descargar/` **en el momento** | instala sin desinstalar la anterior |
| El catálogo de hechos | ver el bloque 4 | **16 hechos** |

⚠️ **Una APK vieja invalida la sesión entera.** El almacén local cambió: una
versión anterior se comporta como antes y da por buenas cosas que ya no lo son.
Que cada quien descargue la del día **delante de todos**, no la que ya tenía.

### Los documentos de prueba se sacan así

En el servidor, **solo lectura**, antes de empezar. No se anotan en ningún lado:

```bash
docker exec -w /app cz_backend python manage.py shell <<'PY'
from apps.victimas.models import ColisionDocumento, Victima
for clase in ('AMBIGUO', 'DUPLICADO_FUENTE', 'NO_IDENTIFICANTE'):
    c = ColisionDocumento.objects.filter(clase=clase).first()
    if not c: continue
    v = Victima.objects.filter(numero_documento_hash=c.doc_hash).first()
    print(clase, '→', v.tipo_documento.codigo if v.tipo_documento_id else '(sin tipo)',
          v.numero_documento, f'({c.filas} filas → {c.personas} personas)')
PY
```

Anotar en un papel **cuál es cuál** (caso 1, 2, 3) y tenerlo a mano. Ese papel no
sale de la sala.

---

## Bloque 1 — Demostración del flujo completo · 15 min

**Objetivo:** que todos vean el recorrido entero una vez, sin interrupciones,
antes de meterse en los detalles. Lo conduce una sola persona; las preguntas se
anotan y se responden en el bloque que corresponda.

**Qué se hace, en este orden:**

1. **Ingreso.** Abrir la APK, entrar con un usuario de prueba.
2. **Búsqueda.** Buscar una víctima por documento (uno normal, sin colisión).
3. **Hogar.** Conformar el hogar: agregar dos o tres integrantes.
4. **Instrumento.** Entrar al instrumento y responder las primeras preguntas,
   mostrando **un salto** (una pregunta que aparece o desaparece según lo
   respondido).
5. **Envío.** Cerrar y sincronizar. Mostrar que aparece en el panel web.

**Qué debe pasar:** el recorrido completo sin errores, y la caracterización
visible en el panel web al final.

**Qué sería un fallo:** que algo obligue a salir y volver a entrar, que el envío
quede "pendiente" sin explicación, o que lo enviado no aparezca en el panel.

> **Qué decir mientras tanto:** que esto es lo que un encuestador hace 15 o 20
> veces por día, y que la sesión se trata de si el sistema **decide como
> decidirían ellos**, no de si se cae.

---

## Bloque 2 — Los cuatro caminos de identidad · 45 min

**El bloque más importante de la sesión.** Es lo que se les pide validar, porque
la decisión de fondo —**cuándo interrumpir al encuestador y cuándo no**— es
funcional, no técnica.

### Por qué existe esto (2 min de contexto, decirlo antes de probar)

En el padrón hay **768.096 documentos que aparecen en más de un registro**. Al
analizarlos:

| | | |
|---|---|---|
| **92 %** | la **misma persona** duplicada en el sistema de origen | no hay nada que decidir |
| **6,8 %** | personas **realmente distintas** que comparten el número | hay que preguntar |
| resto | valores de **relleno** (un "documento" con miles de nombres detrás) | no identifican a nadie |

La regla de diseño: **preguntar solo cuando hay algo que decidir**. Si el sistema
pregunta siempre, el encuestador aprende a ignorar el aviso — y entonces falla
justo el 6,8 % de los casos donde importaba.

### Caso 2.1 — Documento de una sola persona

- **Qué se hace:** buscar un documento normal.
- **Qué debe pasar:** aparece la ficha, **sin ningún aviso**.
- **Qué sería un fallo:** un aviso de "confirme cuál corresponde" cuando solo hay
  una persona.

### Caso 2.2 — Documento repetido que es LA MISMA persona (`DUPLICADO_FUENTE`)

Es el 92 % de los repetidos.

- **Qué se hace:** buscar el documento `DUPLICADO_FUENTE` del script.
- **Qué debe pasar:** responde normal, con **una sola ficha**. El encuestador
  **no debe notar nada**: puede haber cientos de filas de la misma señora en la
  fuente, pero eso no es una decisión suya.
- **Qué sería un fallo:** que pregunte cuál es. Preguntar cuando no hay nada que
  decidir es exactamente lo que enseña a ignorar el aviso del caso siguiente.

### Caso 2.3 — Personas realmente distintas (`AMBIGUO`) ⭐

**Este es el caso que hay que mirar con lupa.**

- **Qué se hace:** buscar el documento `AMBIGUO`.
- **Qué debe pasar:** el sistema **pide confirmar cuál es**, mostrando los
  candidatos con datos suficientes para distinguirlos.
- **Qué sería un fallo:**
  - que elija uno **solo** y siga (aunque acierte: acertó de casualidad);
  - que muestre los candidatos **sin datos suficientes** para elegir;
  - que el encuestador no entienda qué se le está preguntando.
- **Qué preguntarles a los funcionales:** *¿los datos que se muestran alcanzan
  para decidir en campo, con la persona enfrente?* Si la respuesta es no, **eso
  es el hallazgo de la sesión** y hay que anotar qué dato falta.

### Caso 2.4 — Documento de relleno (`NO_IDENTIFICANTE`)

- **Qué se hace:** buscar el documento `NO_IDENTIFICANTE`.
- **Qué debe pasar:** **no muestra a nadie** y lleva al alta manual.
- **Qué sería un fallo:** que muestre una lista de candidatos. Ofrecer a elegir
  entre miles de personas que comparten un valor de relleno es peor que no
  mostrar nada: invita a elegir al azar.

### Caso 2.5 — Sin señal

Repetir **2.1 y 2.3** con el dispositivo **en modo avión**.

- **Qué debe pasar:** el mismo comportamiento que con señal. La búsqueda funciona
  contra el padrón local (5.001.402 registros en el dispositivo).
- **Qué sería un fallo:** que sin señal *no* avise en el caso ambiguo. Sería el
  peor defecto posible: el encuestador trabaja sin señal la mayor parte del
  tiempo, así que el aviso no aparecería justo cuando más se necesita.

---

## Bloque 3 — Captura de un hogar completo, en dispositivo · 30 min

**Objetivo:** que un funcional capture un hogar de principio a fin, **él mismo**,
sin que nadie del equipo técnico le toque el teléfono.

**Qué se hace:**

1. Buscar a la persona y **conformarla como jefe de hogar**.
2. Agregar integrantes: al menos un menor de edad y una mujer en edad fértil (así
   se ven los saltos que dependen de edad y sexo).
3. **Alta manual de un integrante que no esté en el padrón** — ver el recuadro.
4. Recorrer el instrumento **completo**, sin saltearse capítulos.
5. Cerrar y sincronizar.

> **El alta manual no es un caso raro, es parte del flujo normal.**
> **1.884.872 víctimas incluidas (24 %) no pudieron incorporarse al padrón**
> porque su identidad no está resuelta en la fuente. Es **una de cada cuatro**.
> Si el alta manual es incómoda, eso afecta a un cuarto de la operación.

**Qué debe pasar:**

- Los saltos se comportan según lo respondido (preguntas que aparecen y
  desaparecen).
- Las validaciones impiden avanzar con datos imposibles.
- El progreso se conserva si se sale y se vuelve a entrar.
- Al sincronizar, la caracterización aparece completa en el panel web.

**Qué sería un fallo:**

- Que una pregunta que **no corresponde** aparezca igual (por ejemplo, semanas de
  embarazo a un hombre).
- Que una que **sí corresponde** no aparezca — es el peor, porque nadie lo nota:
  el instrumento se ve completo y le faltó un dato.
- Que al volver a entrar se haya perdido lo respondido.
- Que el envío diga "enviado" y en el panel no esté.

**Qué preguntarles:** *¿el orden de las preguntas es el que usan en campo?* Un
instrumento correcto pero en orden incómodo hace que el encuestador salte y
vuelva, y ahí se pierden respuestas.

---

## Bloque 4 — Hechos victimizantes · 20 min

### 🟢 Novedad: esto se resolvió hoy, antes de la sesión

**El correo pedía ayuda para encontrar de dónde salen los hechos. Ya no hace
falta: se encontraron.** Conviene decirlo apenas empiece el bloque, para no
hacerles perder tiempo buscando algo que ya apareció.

**Qué se encontró.** Los hechos viven en el RUV, en `TBSINIESTROS_PERSONA`, y son
alcanzables **desde la misma base que ya usamos**, con un enlace que ya existía.
**No hay que pedir accesos nuevos ni esperar a nadie.**

| | |
|---|---|
| Catálogo oficial de hechos | **13** |
| Hechos con fecha y lugar | **4.033.355** registros |
| Relación persona ↔ hecho | **9.331.396** registros |

**Además de las 14 columnas, se puede poner cuándo y dónde** ocurrió cada hecho,
porque esa tabla trae fecha y ubicación.

### Lo que sí se puede mostrar hoy

- **El catálogo cargado en producción: 16 hechos.** Se ve en el panel de
  administración. Antes de hoy **esa tabla estaba vacía**.
- **Qué debe pasar:** aparecen los 13 hechos oficiales del RUV más los tres que
  el RUV no nombra pero la operación sí necesita (Pérdida de bienes,
  Confinamiento, Sin información).

### Lo que NO se puede mostrar hoy — decirlo claro

La lectura automática de los hechos de cada persona **está construida y probada
pero todavía no desplegada**. Hoy se explica y se muestra el catálogo; **el
poblado automático se ve en la próxima sesión**. No prometer que se ve hoy.

### El punto fino que conviene explicar (y es el que evita un error caro)

Hay **tres catálogos de hechos distintos** en juego: el de SICAV, el del sistema
actual (congelado en 2015) y el del RUV. **Coinciden del 1 al 11 y se separan
justo al final**, que es donde está el volumen:

| Número | En el sistema actual | En el RUV |
|---|---|---|
| **12** | Pérdida de bienes muebles o inmuebles | **Otro** |
| **13** | Otros | **Censo Masivo** |

Copiar el número de un lado al otro habría escrito **el hecho equivocado en
509.442 registros**, sin que ningún error saltara. Se traduce por **significado**,
no por número.

**Decisión ya tomada (Javier):** *Censo Masivo* —que el sistema actual no sabe
nombrar, y son **434.178 personas**— se reporta allá como **"Otros"**, y en SICAV
se conserva con su nombre real. Se pierde precisión en el reporte del sistema
viejo, pero **la persona queda contada y visible**, y el dato real no se pierde.

**Qué preguntarles a los funcionales:**

1. ¿*Censo Masivo* como "Otros" en los reportes del sistema actual es aceptable,
   o necesitan que se distinga?
2. ¿Qué esperan ver en las 14 columnas cuando una persona tiene **más de un**
   hecho?

---

## Bloque 5 — Compromisos y fechas · 10 min

**Cerrar con esto, por escrito, antes de que se levante nadie:**

| Qué | Quién | Para cuándo |
|---|---|---|
| Hallazgos del bloque 2 (¿alcanzan los datos para decidir?) | funcionales | en la sesión |
| Respuesta sobre *Censo Masivo* → "Otros" | funcionales | en la sesión |
| Visto bueno para encender el registro en el sistema actual | funcionales + OTI | fecha a definir |
| Revisar juntos la forma del dato en `RNIENTREVISTA` | OTI | fecha a definir |

### Lo que hay que decir sí o sí antes de terminar

> **La sesión de hoy no toca la base actual.** La ruta que registra las
> caracterizaciones en `RNIENTREVISTA` está terminada pero **apagada a
> propósito**: cuatro interruptores en apagado y **cero escrituras** hasta hoy.
> Se enciende cuando esté lista la reversión y ustedes den el visto bueno, no
> antes.

---

## Anexo — Cosas que se van a preguntar, con la respuesta corta

| Pregunta | Respuesta |
|---|---|
| *¿Por qué 24 % no está en el padrón?* | Su identidad no está resuelta en la fuente. No es un fallo de SICAV: el dato no existe resuelto del otro lado. Por eso el alta manual es parte del flujo normal. |
| *¿Los datos son reales?* | Sí. Padrón real, PII de víctimas. Por eso los documentos no circulan por escrito. |
| *¿Se puede trabajar todo el día sin señal?* | Sí: el padrón está en el dispositivo (5.001.402 registros) y la captura es local. Se sincroniza al recuperar señal. |
| *¿Esto borra o cambia algo en el sistema actual?* | No. Cero escrituras a la fecha, y los interruptores están apagados. |
| *¿Cuándo se enciende el registro en el sistema actual?* | Cuando exista el respaldo y el comando de reversión, y con visto bueno funcional. Ninguna de las dos cosas está lista. |
| *¿Los hechos ya están?* | La fuente ya se encontró y el catálogo está cargado. La lectura automática está construida y probada; falta desplegarla. |
