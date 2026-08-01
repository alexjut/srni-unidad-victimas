# Correo/mensaje a OTI — Aviso de inicio de escritura SICAV en RNIENTREVISTA (prod) + confirmación de respaldo

> Borrador para revisión de Javier. **No es una solicitud de accesos:** SICAV opera con el
> usuario `RNIENTREVISTA` (dueño del esquema), que ya tiene lo necesario. Esto es un **aviso
> de gobernanza** + una **confirmación prudente de respaldo** antes del primer piloto en prod.
> (Reemplaza al borrador anterior de "solicitud de accesos", que quedó sin objeto.)

---

**Para:** [OTI / responsable del servidor 30.0.1.9 / DBA de RNIENTREVISTA]
**CC:** Oscar [supervisión funcional UARIV] · [PMO — Rommey Ruiz]
**Asunto:** Aviso — inicio de registro de caracterizaciones SICAV en RNIENTREVISTA (prod) vía procedimientos oficiales (PRY-0662064)

Estimados,

En el marco del proyecto **PRY-0662064**, el sistema **SICAV** comenzará a **registrar caracterizaciones en RNIENTREVISTA (producción)** usando **exclusivamente los procedimientos oficiales `GIC_*`** —nunca `INSERT` directo a tablas—, con auditoría propia (*ledger*), idempotencia y **verificación por consulta posterior** de cada escritura. La ruta completa ya fue validada de extremo a extremo en una réplica local.

Aclaraciones:

- **No requerimos accesos ni permisos nuevos.** SICAV opera con el usuario `RNIENTREVISTA` (dueño del esquema donde viven los paquetes `GIC_*`), que ya cuenta con lo necesario.
- Escribiremos con un **usuario de servicio identificable** (para que toda caracterización de origen SICAV quede trazable), no con usuarios reales de terceros.
- Comenzaremos con un **piloto controlado de 1 hogar**, identificable y reversible, verificado por consulta, **antes** de abrir el flujo general.

Lo único que solicitamos, por prudencia operativa:

- **Confirmar que existe un punto de respaldo/restauración reciente** de la base (servidor `30.0.1.9`) antes de ejecutar el primer piloto, como red de seguridad. Si el respaldo lo gestiona OTI, agradecemos su confirmación; si corresponde a nuestro lado, lo verificamos internamente.

Cualquier consideración operativa que deban señalarnos, con gusto la incorporamos.

Cordialmente,
**Javier Aguilar** — Desarrollo y arquitectura, SICAV / SRNI (PRY-0662064)

---

### Notas para Javier (no enviar)

- Si el servidor `30.0.1.9` y sus respaldos son **100 % nuestros**, este correo se reduce a un **aviso de cortesía** (gobernanza) y la confirmación de respaldo la hacés internamente — incluso podrías **no enviarlo**.
- **Rotación de la clave de RNIENTREVISTA** (pendiente 3a.5 del informe): la podemos hacer nosotros por ser dueños → **tarea interna**, no se le pide a OTI.
- **Sin relación con Oracle**, sigue pendiente de OTI el **TLS/dominio público** de `caracterizacion.unidadvictimas.gov.co` (registro A/CNAME público + `:443` + certificado). Si querés, lo sumo como segundo punto o en correo aparte.
- **Prerrequisito del piloto:** tener confirmado el respaldo. Con eso en verde, ejecutamos: crear usuario de servicio SICAV → escribir 1 hogar piloto → verificar por SELECT.
