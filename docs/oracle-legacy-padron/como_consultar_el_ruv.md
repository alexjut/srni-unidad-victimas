# Cómo consultar el RUV — el mapa, sacado de la propia base

> **Fecha:** 2026-07-29 · Todo lo de aquí salió de consultar la BD, solo `SELECT`.
> Responde las tres preguntas que estaban abiertas para implementar la lectura del padrón.

## Resumen

El RUV **no se consulta por tabla**: hay un **middleware de web services parametrizable**
cuyo catálogo vive en la propia base. Cada "método" del servicio es, por dentro, **un
procedure PL/SQL o una consulta SQL**. Está todo declarado en `RNIPAQUETES.WS_METODOS`
(**136 métodos**).

```
Aplicación  ──HTTP──▶  middleware Vivanto  ──▶  WS_METODOS.METODO_NOMBREPROC
(ID_APLICACION)         (Parametrizador)         = mi_pkg_consultas.MI_PERSONAS_UNICA
                                                 sobre METODO_CONEXION
```

## 1. El endpoint y su administración ✅

**El parametrizador de web services es una aplicación web de la Unidad**, y su URL está
en `ADMINUSUARIOS.NIVELACCESO`:

| Qué | URL |
|---|---|
| Parametrizador | `https://vivantov2.unidadvictimas.gov.co/Parametrizador/` |
| Métodos | `…/Parametrizador/Metodos/Metodos` |
| Variables | `…/Parametrizador/Variables/Variables` |
| Parámetros | `…/Parametrizador/Parametros/Parametros` |
| Parámetros por usuario | `…/Parametrizador/ParametrosUsuarios/ParametrosUsuarios` |

O sea: **los servicios se dan de alta y se configuran desde ahí**, y su definición aterriza
en las tablas `RNIPAQUETES.WS_*` que ya podemos leer.

## 2. El `ID_APLICACION` de SICAV ✅ — ya existe

`ADMINUSUARIOS.APLICACION` tiene 52 aplicaciones registradas. Entre ellas:

| id | Nombre | Descripción |
|---:|---|---|
| **309** | **IGED** | **IGED ENCUESTA** ← *nuestro proyecto, ya registrado* |
| 3 | CONSULTA INDIVIDUAL | Consulta Individual del RUV |
| 146 | WS RUV | WS RUV |
| 267 | WS MI_PERSONAS_RUV | WS MI_PERSONAS_RUV |
| 228 | FICHA MOVIL | Ficha caracterización para móvil |
| 227 | PARAMETRIZADOR | Parametrizador web services |

**No hay que pedir un `ID_APLICACION` nuevo: el 309 ya es nuestro.** Falta confirmar qué
métodos tiene autorizados y, si falta alguno, dárselos desde el parametrizador.

## 3. ¿Devuelve etnia, discapacidad y hechos? ✅ SÍ — hay métodos dedicados

De los 136 métodos, estos son los que sirven (todos **activos**):

| id | Método | Implementación | Conexión |
|---:|---|---|---|
| 75 | `MI_PERSONAS` | `mi_pkg_consultas.MI_PERSONAS` | ModeloIntegradoPru |
| **76** | **`MI_PERSONAS_UNICA`** | `mi_pkg_consultas.MI_PERSONAS_UNICA` | ModeloIntegradoPru |
| **78** | **`ETNIA`** | `mi_pkg_consultas.ETNIA` | ModeloIntegradoPru |
| **82** | **`DISCAPACIDAD`** | `mi_pkg_consultas.DISCAPACIDAD` | ModeloIntegradoPru |
| 91 | `MI_ESTADO_PERSONAS` | `mi_pkg_consultas.MI_ESTADO_PERSONAS` | ModeloIntegradoPru |
| 64 | `MI_PERSONAS_RUV` | `mi_pkg_consultas.MI_PERSONAS` | AuditoriaFuentes |
| 106 | `MI_TUTORES_PERSONAS` | `mi_pkg_consultas.MI_TUTORES_PERSONAS` | ModeloIntegradoPru |
| 146 | `FUD RUV LEY 1448` | `SELECT … FUENTE, ID_PERSONA, NOMBRE1…` | **RuvProduc** |
| 886 | `WS SERVICIO 418` | `VICTIMAS.PKG_VICTIMAS_RNI.CM_FUN_HEC…` | FuenteSIPODSIV |
| 147 / 148 / 149 | SIPOD 387 / SIV 418 / SIRAV 1290 | paquetes por fuente | varias |

**Los tres campos que faltaban tienen método propio: `ETNIA` (78) y `DISCAPACIDAD` (82).**
Los hechos victimizantes salen de `WS SERVICIO 418` / `PKG_VICTIMAS_RNI` y de los métodos
por ley (387, 418, 1290), que es coherente con que el RUV distinga la norma de origen.

## ⚠️ Lo que hay que mirar con lupa: las conexiones

`METODO_CONEXION` es un nombre de conexión configurado **en el middleware**, no un dblink
de Oracle. Reparto de los 136 métodos:

| Conexión | Métodos |
|---|---:|
| `ConexionModeloIntegradoPru` | **38** |
| `ConexionRegistraduria` | 24 |
| `ConexionFuentes1` | 20 |
| `ConexionCar` | 16 |
| `ConexionSirav` | 10 |
| `ConexionRuvProduc` | 4 |
| **`ConexionModeloIntegradoProd`** | **1** |

**Casi todos los métodos `MI_*` apuntan a `…Pru`, no a `…Prod`.** Esa es la explicación más
probable de que `MODELOINTEGRADO.MI_PERSONAS` esté **vacía en la base que alcanzamos**:
estamos viendo el Modelo Integrado de **pruebas**. El de producción es otra instancia, y a
ella no llegamos por `DBL_VIVANTO`.

**Hay que confirmarlo antes de construir nada.** Si los métodos productivos apuntan a
`Pru`, es un problema del propio Vivanto, no nuestro — y conviene reportarlo.

---

## Cómo funciona el sistema, y dónde se parametriza cada cosa

Vivanto no tiene los servicios "programados": los tiene **declarados en tablas**. Una
aplicación pide un método por nombre, el middleware busca su definición, ejecuta el
procedure sobre la conexión que diga la ficha, y devuelve el resultado. Cambiar un
servicio es cambiar una fila, no desplegar código.

### Las tres capas

```
┌─ QUIÉN llama ────────────────────────────────────────────────┐
│  ADMINUSUARIOS.APLICACION            52 aplicaciones          │
│      309 = IGED (nosotros) · 3 = Consulta Individual del RUV  │
│  ADMINUSUARIOS.NIVELACCESO           menús, URLs y permisos   │
│      (árbol: IDPADRE; cada hoja cuelga de una IDAPLICACION)   │
│  + ROLAPLICACION (58) · POLITICAAPLICACION (195.703)          │
│    APLICACIONDELEGADA (679) · PARAMETROSAPLICACION (3.555)    │
└───────────────────────────────────────────────────────────────┘
                              │
┌─ QUÉ se puede llamar ────────▼───────────────────────────────┐
│  RNIPAQUETES.WS_METODOS              136 métodos              │
│      METODO_NOMBRE        nombre público del método           │
│      METODO_NOMBREPROC    el procedure PL/SQL o el SQL        │
│      METODO_CONEXION      contra qué base se ejecuta          │
│      METODO_TIPOCONSULTA / TIPO_SP / METODO_TIPOBD            │
│      ID_NIVEL_ACCESO      con qué permiso se puede invocar    │
│      METODO_ACTIVO        interruptor                         │
│      METODO_XML / CABEZERAXML   formato de la respuesta       │
│  + WS_PARAMETROS · WS_PARAMETROSUSUARIOS · WS_ERRORES         │
└───────────────────────────────────────────────────────────────┘
                              │
┌─ QUÉ QUEDA REGISTRADO ───────▼───────────────────────────────┐
│  AUDITORIAVIVANTOPROD.AU_CONSULTA_WEB_SERVICES   103.258.515  │
│      con ID_APLICACION: se sabe qué app consultó qué          │
│  AU_CONSULTA_INDIVIDUAL_RUV                      375.533.381  │
│  WS_AUDITORIA                                    378.870.362  │
└───────────────────────────────────────────────────────────────┘
```

### Dónde se toca cada cosa

| Si hay que… | Se hace en |
|---|---|
| dar de alta o editar un método | Parametrizador → **Metodos** (`…/Parametrizador/Metodos/Metodos`) |
| definir variables del servicio | Parametrizador → **Variables** |
| definir parámetros | Parametrizador → **Parametros** |
| ajustar parámetros por usuario | Parametrizador → **ParametrosUsuarios** |
| registrar una aplicación nueva | `ADMINUSUARIOS.APLICACION` (la nuestra ya existe) |
| dar permiso a una aplicación sobre un método | `NIVELACCESO` + `ID_NIVEL_ACCESO` del método |

### Lo que esto implica para nosotros

1. **No hay que construir un servicio**: hay que **usar** los que existen, y confirmar que
   la aplicación 309 los tenga habilitados.
2. **La respuesta puede venir en XML** (`METODO_XML`, `METODO_CABEZERAXML`), así que el
   cliente debe contemplarlo, no asumir JSON.
3. **Cada llamada queda auditada con nuestro `ID_APLICACION`.** Eso es bueno —trazabilidad
   de quién consultó a qué víctima— y es la razón principal para ir por el middleware y no
   por debajo, aunque técnicamente pudiéramos invocar el procedure directo.
4. **`METODO_ACTIVO` es un interruptor de terceros:** si alguien desactiva un método que
   usamos, nuestra consulta deja de funcionar sin que nada cambie de nuestro lado. Conviene
   que el repositorio degrade con un mensaje claro en vez de romperse.

> **Nota de honestidad sobre esta sección.** La estructura de las tablas y sus conteos
> están medidos. La descripción del *flujo* (que el middleware resuelve el método y ejecuta
> el procedure) es la lectura más razonable de esa estructura, pero **no la vimos ejecutar**:
> falta confirmarla con el equipo de Vivanto o viendo una llamada real. Está redactada como
> descripción y no como certeza a propósito.

## Camino ahora

1. **Entrar al parametrizador** (`vivantov2…/Parametrizador/`) con las credenciales de la
   Unidad y mirar: qué métodos tiene autorizados la aplicación **309 (IGED)**, y a qué
   apuntan de verdad `ConexionModeloIntegradoPru` y `…Prod`.
2. **Confirmar la firma** de `mi_pkg_consultas.MI_PERSONAS_UNICA` (qué parámetros pide).
   No es visible desde nuestro dblink porque el paquete vive en la base del Modelo
   Integrado, no en `ENTREVISTARN`.
3. Con eso, implementar el repositorio contra el contrato que ya existe. Sigue en pie que
   **no se inventa el mapeo** de `estado_ruv` ni de `habilitado_para_caracterizacion`.

> **Lo que cambió respecto a ayer:** ya no hace falta pedir "el endpoint y las credenciales"
> a ciegas. Sabemos que el sistema es parametrizable, dónde se administra, que nuestra
> aplicación ya está dada de alta, y qué método concreto devuelve cada cosa.
