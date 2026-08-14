# Plan — Pre-llenado desde el RUV (no re-preguntar lo conocido)

> Requisito: la caracterización debe **jalar de la BD/RUV** lo que ya existe
> (identidad, grupo familiar, hechos victimizantes) y **no volver a preguntarlo**.
> La caracterización es para **ampliar/profundizar**, no para duplicar el RUV.

## 1. Qué pre-llenar (mapeo propuesto — VALIDAR con UARIV antes de suprimir)

| Grupo | Datos | Confianza | Acción |
|---|---|---|---|
| **Identidad** | nombres, tipo+número doc, fecha nac., género, pertenencia étnica, pueblo, discapacidad, municipio residencia | Alta | Pre-llenar solo-lectura |
| **Hecho principal** | `A21` hecho, `A22` fecha, `A23` municipio del hecho | Alta | Pre-llenar desde `hechos_victimizantes` |
| **Edad / grupo etario** | `B9` edad, `B10`/`GRU_ETAR` grupo etario | Alta | **Derivar** de `fecha_nacimiento` |
| **Capítulos extra de hechos** (HV/CA en buenaventura, san_andrés, rural) | descripción/ampliación del hecho | **REVISAR** | **NO suprimir** — piden detalle que el RUV no tiene |
| **victimas_exterior** | mapeo ambiguo | **REVISAR** | No tocar hasta confirmar |

> ⚠️ Los códigos (`A21`, `B9`, …) salieron de un análisis del JSON, no del spec oficial.
> Antes de **suprimir** una pregunta de hechos hay que validarlos contra el instrumento
> oficial UARIV. El pre-llenado de **identidad y edad** es de bajo riesgo y se puede hacer ya.

## 2. Grupo familiar (jalar al conformar)

Ya existe `GET /api/victimas/grupo-familiar/{cons_persona}/` (y `obtener_grupo_familiar`
en el repo). Hoy solo se muestra en el detalle del hogar. **Falta**: al conformar el
hogar, ofrecer los integrantes del RUV para **agregarlos con un toque**, pre-llenados
(nombre, doc, fecha, género), en vez de teclearlos. Offline: desde la pre-carga (jornada).

## 3. Mecanismo (recomendado): tag `prefill_source`

En cada pregunta del instrumento JSON, campo opcional:
```json
{ "codigo_externo": "A21", "texto": "Hecho victimizante principal",
  "tipo": "LISTA", "prefill_source": "hecho_principal" }
```
Valores: `tipo_documento`, `numero_documento`, `primer_nombre`, …, `fecha_nacimiento`,
`hecho_principal`, `hecho_fecha`, `hecho_municipio`, `edad` (derivado), `grupo_etario` (derivado).

- **Backend** (cargadores/serializer): cuelga el tag en la pregunta; un helper extrae el
  valor del `VictimaResumen` (mock ahora, Oracle después). Retrocompatible (sin tag = se
  pregunta normal).
- **Mobile** (`formulario/[temaId].tsx`): si la pregunta trae `prefill_source`, **pre-rellena
  la respuesta** desde la víctima y la muestra **solo-lectura** con estilo distinto
  (fondo gris, "tomado del RUV") — no se pregunta, pero queda visible y auditable.
- **Derivados** (`edad`, `grupo_etario`): se calculan de `fecha_nacimiento` en el cliente.

## 4. Secuencia recomendada (best practice)

1. **Grupo familiar al conformar** (A) — bajo riesgo, alto valor. *(Toca el flujo offline pendiente de validar → integrar con cuidado.)*
2. **Pre-llenar identidad + derivar edad/grupo etario** (B) — bajo riesgo.
3. **Mecanismo `prefill_source`** + tag de **identidad/hecho-principal** (alta confianza).
4. **Suprimir hechos**: solo tras **validar el mapeo con el spec UARIV** (capítulos HV/CA NO se suprimen).

## 5. Dependencias
- Validación del mapeo de hechos con UARIV (paso 4).
- Los valores reales (identidad/hechos/grupo familiar) salen del RUV → con mock funciona
  hoy; con Oracle igual vía la interfaz del repositorio (`get_repository()`).
