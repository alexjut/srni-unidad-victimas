# Casos de uso de la capacitación — pruebas del 11-sep-2026

**Contra producción** (`caracterizacion.unidadvictimas.gov.co`) · **Para la Sesión 1
del martes 15 de septiembre** y las dos jornadas territoriales del 24 y el 29.

Este documento dice qué se probó, qué pasó y qué quedó abierto. No es un informe
de estado: es lo que hay que mirar antes de repartir credenciales.

---

## 1. Qué se dejó montado

**37 cuentas**, una por participante del Plan de Capacitación, con perfil
`COORDINADOR`. Se eligió ese perfil porque es el único que cubre la jornada
entera: caracteriza en la aplicación (Bloque A), autoriza excepciones (Caso 2) y
abre supervisión, reportes y auditoría (Bloque B). Con `ENCUESTADOR` el Bloque B
se ve a medias y el Caso 2 no se puede practicar.

El `codigo_usuario` sigue la convención del sistema —iniciales de los nombres +
primer apellido + inicial del segundo—, verificada contra cuatro códigos reales
existentes (`KLMUÑOZM`, `KDCARRIONT`, `KTSOSCUEL`, `DLVIVASL`): los reproduce
exactamente. No se inventó un esquema paralelo tipo `CAP01` porque el
participante debe entrar el 15 con el mismo código con el que entrará en campo.

**185 personas de práctica**, cinco por participante, todas con documento que
empieza por `999` —la convención del proyecto para datos que no son una víctima
real—, numeradas con el índice del participante para que dos personas nunca se
pisen el hogar:

| Documento | Para qué |
|---|---|
| `999NN00001` | Caso 2 — ficha vigente, bloqueada, hay que autorizarla |
| `999NN00002` | Caso 2 — miembro del mismo hogar |
| `999NN00003` | Caso 1 — la señora que recibe |
| `999NN00004` | Caso 1 — hijo de 14 años |
| `999NN00005` | Caso 1 — madre de 71 años |
| `999NN00009` | Caso 3 — **no existe a propósito**: es el alta manual |

Todo esto lo produce `preparar_capacitacion`, que es idempotente: se corrió dos
veces y la segunda actualizó sin duplicar nada.

---

## 2. Qué se probó, y cuántas veces

Con `scripts/qa/probar_casos_uso_capacitacion.py`, por la misma API que usan la
aplicación móvil y el panel.

| Paso | Caso |
|---|---|
| Ingreso y perfil con los cuatro permisos | 0 |
| Titular, hijo y madre elegibles | 1 |
| La persona está bloqueada por ficha vigente, con el motivo correcto | 2 |
| El panel la encuentra y coordinación registra la autorización | 2 |
| La aplicación ya la deja caracterizar | 2 |
| **Se puede continuar sobre el hogar, sin quedar bloqueado** | 2 |
| Se anula y vuelve a quedar bloqueada | 2 |
| El documento que no existe no devuelve a nadie | 3 |
| Abre hogares, encuestas, autorizaciones, reportes y auditoría | B |
| **No** puede administrar usuarios | B |

**Resultados:**

| Corrida | Participantes | Comprobaciones | Fallas |
|---|---|---|---|
| Sesión 1, dos vueltas seguidas | 7 | **253** | 0 |
| Las tres sesiones, una vuelta | **37** | **740** | **0** |

Las dos corridas se hicieron **contra producción**, con las cuentas reales que se
van a repartir y sobre los datos de práctica de cada participante.

El banco **deja el escenario como lo encontró**: al terminar cada Caso 2 anula la
autorización que creó. Sin eso, la segunda corrida encontraría a la persona ya
habilitada y la prueba pasaría sin haber probado nada.

---

## 3. Hallazgos

### 3.1 El tope de ingresos por IP no se dispara — y es una buena noticia

El servidor declara `login: 5/minute` y ese tope es **por IP, no por usuario**.
El 15 hay quince personas en una sala detrás de una sola salida a internet: si el
tope aplicara, la sexta persona en entrar entre las 8:30 y las 8:31 vería
«demasiados intentos» con la clave correcta, y eso se lee como que las
credenciales no sirven.

**Medido: ocho ingresos seguidos desde la misma máquina, ninguno rechazado.** La
causa es que el WAF institucional reenvía al cliente como `IP:puerto` y el puerto
cambia en cada conexión, así que cada petición cuenta como un origen distinto.

Para la jornada: no hay riesgo. Como control de seguridad: **ese tope está
inerte en producción**. La protección que sí funciona es la otra —cinco intentos
fallidos sobre el mismo código bloquean la cuenta quince minutos—, que es la que
importa contra fuerza bruta. Queda anotado, no es urgente y **no se toca antes
del 15**: endurecerlo ahora es exactamente lo que rompería la sala.

### 3.2 La regla de vigencia funciona — con una sola excepción, y es la que se reportó

Medido sobre producción el 11-sep:

| | |
|---|---|
| Padrón | 5.926.196 |
| Con caracterización registrada | 2.536.018 |
| Con ficha vigente (menos de dos años) | 973.964 |
| De esas, **bloqueadas** por el sistema | 973.963 |
| De esas, **no bloqueadas** | **1** |

Esa única fila es la cédula `1115724047`, que es justamente el caso reportado.

### 3.3 El caso `1115724047` — qué pasó de verdad

Lo que se encontró en la base, solo lectura:

- **No tiene ningún hogar.** Cero, de ningún dueño. El mensaje «esta persona ya
  tiene hogar» **no vino del servidor**: la búsqueda devuelve `hogar_activo: null`
  y la consulta de la aplicación ni siquiera incluye ese campo.
- **No está bloqueada.** El veredicto del servidor es `ELEGIBLE`, no
  `FICHA_VIGENTE`. O sea que **la autorización no hacía falta**.
- Tiene fecha de última caracterización del **28 de julio de 2026** pero la marca
  de habilitación quedó en `True`. Las dos cosas se escriben juntas al cerrar una
  encuesta (`apps/encuestas/views.py:357-361`), así que algo las separó después:
  lo más probable es que su hogar se borrara en una limpieza de datos de prueba
  y la fecha quedara estampada.
- La autorización que se registró está **VIGENTE y sin usar**, con radicado `1`.

**Por qué se cuela.** `describir_elegibilidad` devuelve `ELEGIBLE` en cuanto la
marca es `True`, **antes** de mirar la fecha
(`apps/victimas/repository/base.py:376`). Una fila con la marca en `True` y fecha
reciente nunca llega a la regla de los dos años. Hoy es una sola fila de
973.964, pero el atajo está ahí.

**Qué hacer:** anular esa autorización para no dejar un permiso abierto sobre una
persona real, y corregir la marca de esa ficha. Ninguna de las dos se hizo:
**son escrituras sobre una víctima real y esperan visto bueno.**

### 3.4 Defecto latente: una víctima no puede tener un segundo hogar, nunca

Confirmado en el código y en la base, aunque **no es lo que pasó en el caso 3.3**.

`Hogar` tiene una restricción de unicidad sobre la persona autorizada para todo
hogar que no esté archivado (`apps/hogares/models.py:127-136`), y **nada en el
código pone jamás un hogar en archivado**: en producción hay **0 archivados de
45**. La válvula de escape existe y nunca se abre.

La autorización de excepción **no toca esa regla**: levanta la vigencia y nada
más. El resultado es que a una persona se le puede autorizar la excepción y aun
así quedar bloqueada, con un mensaje que no nombra la causa real.

Se salva cuando el hogar es del **mismo** encuestador: ahí el servidor lo
reutiliza y responde 200. Solo muerde cuando el hogar es de **otro**. Por eso el
banco de pruebas ahora incluye ese paso y por eso da verde: en el escenario de
práctica el hogar es del propio participante.

**Para la jornada no es un riesgo.** Para campo sí, y necesita una decisión de
negocio: continuar sobre el hogar existente, o archivar el anterior al autorizar
la excepción.

### 3.5 Corregido: los integrantes del hogar llegaban sin apellidos ni cédula

Reportado el 11-sep: al conformar un hogar, el autorizado sale completo y **los
demás integrantes llegan con el primer nombre y nada más**.

Dos huecos encadenados:

- **Servidor.** El listado de miembros entregaba el nombre **solo como una cadena
  concatenada** y el documento no lo entregaba en absoluto: estaba marcado como
  de solo escritura. La aplicación no tenía de dónde sacar los apellidos ni la
  cédula.
- **Aplicación.** Al no tenerlos, partía la cadena y **se quedaba con el primer
  pedazo**. El autorizado se salvaba porque recibe además la ficha completa del
  padrón, que sí trae los cuatro campos por separado.

Arreglado en los dos lados. El servidor expone ahora `primer_nombre`,
`segundo_nombre`, `primer_apellido`, `segundo_apellido`, `numero_documento` y
`tipo_documento_codigo`, leídos de la víctima vinculada; la aplicación los usa y
solo parte la cadena como respaldo, para una APK que hable con un servidor
anterior.

Partir la cadena **no era el arreglo**: «José Luis Vargas Mora» y «José Vargas
Mora» no se distinguen sin saber cuántos nombres tiene la persona, y adivinarlo
le escribe a alguien un apellido que no es el suyo.

> ⚠️ **La parte de la aplicación necesita una APK nueva.** El arreglo del
> servidor sirve solo cuando el dispositivo tiene una versión que lo consume. Hay
> que compilar y publicar antes del 15.

---

## 4. Lo que queda abierto

| # | Qué | Quién decide |
|---|---|---|
| 1 | Anular la autorización sobrante de `1115724047` y corregir su marca de habilitación | Javier — son escrituras sobre una víctima real |
| 2 | Compilar y publicar la APK con el arreglo de los integrantes | Javier |
| 3 | Segundo hogar de una víctima: continuar sobre el existente o archivar el anterior | Negocio (§3.4) |
| 4 | Retiro del control de vigencia solicitado por el área funcional | Área funcional — ver `docs/gestion/correo_retiro_control_vigencia_2026-09-11.md` |
| 5 | El tope de ingresos por IP está inerte | Después del 15 |

---

## 5. Cómo repetir todo esto

```bash
# 1. Dejar montadas cuentas y datos de práctica (ensayo primero, sin --confirmar)
python manage.py preparar_capacitacion
python manage.py preparar_capacitacion --confirmar --salida /tmp/cred.csv

# 2. Correr los casos de uso contra producción
python scripts/qa/probar_casos_uso_capacitacion.py --credenciales cred.csv --sesion 1
python scripts/qa/probar_casos_uso_capacitacion.py --credenciales cred.csv --vueltas 3
python scripts/qa/probar_casos_uso_capacitacion.py --credenciales cred.csv --medir-limite-ingreso
```

El CSV de credenciales tiene claves en texto plano. Va fuera del repositorio y
se borra al repartirlas.
