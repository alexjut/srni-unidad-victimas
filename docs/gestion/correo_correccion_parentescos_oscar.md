# Correo — corrección/aclaración sobre parentescos en RNIENTREVISTA

> **Borrador para revisión de Javier antes de enviar a Oscar.** Corrige el correo previo
> que escaló las 7 opciones de parentesco como "defecto activo de producción".

**Asunto:** Aclaración — parentescos en RNIENTREVISTA: revisado con el catálogo completo, no hay pérdida activa

---

Oscar, buenos días.

Te escribo para **corregir y precisar** el correo anterior, en el que te reporté con
prioridad una posible pérdida silenciosa de 7 opciones de parentesco. Tras auditarlo
contra el **catálogo completo** de RNIENTREVISTA (no una muestra) y contra el manual
oficial, **la conclusión cambia: no hay un defecto activo ni pérdida de información**.

**Qué revisé y qué encontré:**

- El manual oficial (11-MU, pág. 56) declara **6 opciones** de parentesco: Jefe(a),
  Cónyuge/Compañera(o), Hijo(a)-Hijastro(a), Padre/madre-Padrastro/madrastra,
  Hermano(a)-Hermanastro(a) y "Otro pariente del jefe".
- La aplicación (SICAV) **ofrece exactamente esas 6** — verificado opción por opción.
- En RNIENTREVISTA, **esas mismas 6 son justamente las que el sistema sí guarda**
  (`RES_IDRESPUESTA` 79, 80, 81, 84, 906, 912).
- Las 7 opciones que había señalado (Nieto, Yerno/nuera, Abuelo, Suegro, Tío, Sobrino,
  "Otros no parientes") **no las declara el manual y la aplicación no las ofrece al
  encuestador**. Es decir, **nadie puede seleccionarlas**, por lo que no hay dato que se
  pierda. Son opciones retiradas que quedaron en el catálogo histórico de la BD; que el
  sistema no las guarde es, de hecho, el mecanismo con el que se retiran las opciones que
  dejaron de ser oficiales — está **implementando el manual**, no fallando.

**En resumen:** el mecanismo que describí (el procedure descarta en silencio una opción
sin fila de escritura) es real, pero **solo importaría si la aplicación ofreciera esas
opciones, y no lo hace**. No hay hogares afectados ni corrección de catálogo pendiente en
este punto. Lamento la alarma anticipada; la verificación contra el catálogo completo
—que ya tenemos disponible localmente— es la que permitió cerrarlo con certeza.

**Lo que sí queda como consulta de negocio** (tema distinto, sin urgencia): en el tipo de
documento, RNIENTREVISTA tiene el texto "Cédula de ciudadanía/Contraseña" repetido con 4
identificadores, uno de ellos (`3854`) con un volumen de uso significativo. Cuando
podamos, me gustaría confirmar contigo cuál corresponde usar. Lo detallo aparte.

Quedo atento a cualquier duda.

Un saludo,
Javier
