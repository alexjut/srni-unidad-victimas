# Víctimas de prueba — Ambiente de validación SRNI

> **Para:** Equipo funcional / de caracterización
> **Ambiente:** https://prod-caracterizacion.ngrok.app (panel web) y APK de pruebas
> **Importante:** Todos los datos son **100 % ficticios**. Ninguna cédula ni nombre
> corresponde a una persona real. Los documentos empiezan por `999…` justamente para
> distinguirlos de cédulas reales.

Estas 10 personas **ya están cargadas** en el sistema (RNI de pruebas). No hay que
crearlas: se buscan por documento en la app/panel y aparecen, cada una pensada para
probar un escenario distinto del proceso de caracterización.

## ✅ Habilitadas — se puede caracterizar

| # | Tipo | Documento | Nombre | Escenario a probar |
|---|------|-----------|--------|--------------------|
| 1 | CC | **9990100001** | María Esperanza Rojas Mendoza | Desplazada, **con grupo familiar (3)** — conformación de hogar |
| 4 | RC | **9990100004** | Santiago de las Flores Martínez | **Menor de edad** → flujo **tutor** |
| 5 | CC | **9990100005** | Rosario del Carmen Valencia Ríos | **Discapacidad severa** → flujo **cuidador** |
| 6 | CC | **9990100006** | Héctor Fabio Quintero Ossa | Trae **todos los hechos victimizantes** (HV01–HV13) |
| 9 | CC | **9990100009** | Gloria Isabel Mosquera Cerón | **Familia numerosa** (5 miembros) |
| 10 | CC | **9990100010** | Lucía Neiza Yule Tombé | **Indígena NASA** (Cauca) → instrumento territorial/étnico |

## ⛔ No habilitadas — para probar los mensajes de control

| # | Tipo | Documento | Qué debe mostrar la app |
|---|------|-----------|--------------------------|
| 2 | CC | **9990100002** | "No incluida en el RUV" (solo Registraduría) |
| 3 | CC | **9990100003** | "Ya fue caracterizada" (no habilitada para nueva) |
| 7 | CC | **9990100007** | "No se encontró registro" (búsqueda negativa limpia) |
| 8 | CC | **9990100008** | "Excluida del RUV — no elegible" |

## Sugerencia de recorrido de prueba
1. **Caso 1** (`9990100001`) — flujo completo: buscar → conformar hogar → diligenciar instrumento → finalizar.
2. **Caso 9** (`9990100009`) — hogar grande, prueba de rendimiento del formulario.
3. **Casos 4 y 5** — flujos especiales (tutor / cuidador).
4. **Caso 10** — población étnica.
5. **Casos 2, 3, 7, 8** — confirmar que la app **bloquea** correctamente y muestra el motivo.

> ⚠️ Cualquier cédula que **no** esté en esta lista responde "no encontrada".
> Cuando el sistema se conecte al Oracle real de la UARIV, estas cédulas de prueba
> dejan de aplicar y se usan datos reales del RNI (trámite posterior con la OTI).
