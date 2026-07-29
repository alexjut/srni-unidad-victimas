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
