# En qué quedamos — 11 de septiembre de 2026

**Asunto:** retiro del control de vigencia, pedido ese mismo día por el equipo de
caracterización. Todo lo de código está **construido, probado y subido a los dos
remotes**. Falta ejecutarlo en producción.

---

## Lo único que falta, y por qué no se hizo

**La VPN estaba caída toda la tarde.** `30.0.1.109` no respondía por SSH, así que no
se pudo desplegar el backend, ni mover el interruptor, ni subir la APK.

Con la VPN conectada son tres comandos, en este orden:

```bash
# 1. El código nuevo (incluye las migraciones 0010 de encuestas y 0008 de hogares)
bash infra/deploy/scripts/desplegar-backend-codigo.sh

# 2. Abrir la caracterización para todos. Deja su propia huella con fecha
bash infra/deploy/scripts/retirar-control-vigencia.sh retirar

# 3. La APK. Ya está compilada y descargada: NO la vuelva a construir
APK_LOCAL="C:/Users/millo/AppData/Local/Temp/claude/D--desarrollo-unidad-victima/800b5e71-cb21-4f8f-96d2-dd624dba879a/scratchpad/app-1.2.5-vc59.apk" \
  bash infra/deploy/scripts/deploy-apk.sh
```

> **La APK 1.2.5 (versionCode 59) ya está compilada**, con estado FINISHED en EAS y
> descargada localmente (76 MB, verificada). Volver a construirla subiría el
> versionCode y publicaría un artefacto distinto del que se probó. Si el archivo
> local se perdió, el artefacto sigue en
> `https://expo.dev/accounts/alexjut/projects/srni-mobile/builds/1020b741-e77e-46f5-be57-fb3e4fe0f3fb`.

El paso 2 va aparte del 1 a propósito: retirar una regla del Manual de Usuario
§5.1.1 es una decisión del proceso, no un efecto de desplegar, y separarlo deja el
acto con su fecha y su responsable en el historial del servidor. Para volver atrás:
el mismo script con `reponer`.

### Qué verificar después, en este orden

1. `/api/` responde **200** y no 502 (lo comprueban los propios scripts).
2. El interruptor, preguntándole al proceso y no al archivo:
   `bash infra/deploy/scripts/retirar-control-vigencia.sh estado`
3. En la APK: **cerrar sesión y volver a entrar con señal.** Es en el ingreso cuando
   el teléfono actualiza el padrón que usa sin conexión.
4. Buscar una persona caracterizada hace menos de dos años: debe salir habilitada,
   sin mensaje de excepción.
5. Conformar su hogar: si lo creó otro encuestador, debe continuar **y mostrar la
   familia que ya estaba registrada**.
6. Cerrar una caracterización y comprobar el libro, en el panel
   (**Recaracterizaciones**) o por consola:
   `docker exec cz_backend python manage.py shell -c "from apps.encuestas.models import RecaracterizacionVigente as R; print(R.objects.count())"`

---

## La decisión que sigue siendo del proceso

**El material de capacitación ya está corregido al régimen nuevo.** El cuestionario,
el Caso 2 del Anexo B, el manual 1.3 y el plan enseñan que la persona ya
caracterizada se continúa sin pedir autorización.

De ahí sale una consecuencia que hay que resolver antes del 15:

- **Si el interruptor se enciende antes del 15**, todo cuadra.
- **Si NO se enciende**, las tres jornadas van a enseñar algo que el sistema todavía
  no hace, y la práctica en vivo va a chocar con «No habilitado».

No hay una tercera opción, y la que quedó por defecto en el repositorio es el
material nuevo.

**Y falta la instrucción escrita.** El correo de constancia está listo para enviar en
`docs/gestion/correo_retiro_control_vigencia_2026-09-11.md`. Pide una línea de quien
tiene competencia sobre el Manual §5.1.1. El código no la necesita para funcionar —el
interruptor se mueve igual— pero el expediente sí.

---

## Lo que se construyó, con dónde está cada cosa

| | Qué | Dónde |
|---|---|---|
| 1 | Interruptor de vigencia, apagado por defecto | `settings.VIGENCIA['BLOQUEO_ACTIVO']` |
| 2 | Libro de auditoría, escrito al cerrar la encuesta | `encuestas.RecaracterizacionVigente` |
| 3 | Punto de control: API + pantalla del panel | `/api/recaracterizaciones/`, `Recaracterizaciones.tsx` |
| 4 | Retiro de integrantes del hogar | `hogares.MiembroHogar` + acciones `retirar`/`reincorporar` |
| 5 | Salida del hogar y de la sesión (los dos 409) | `hogares/views.py`, `encuestas/views.py` |
| 6 | Sin señal también funciona | precarga + `authStore.cargarPerfil` |
| 7 | Los cuatro defectos de «no RUV» | 1.2.4 y 1.2.5 |
| 8 | Material de capacitación | cuestionario, anexos, manual 1.3, plan, 3 PDF |

Detalle técnico y el por qué de cada decisión:
`docs/operacion/plan_registro_silencioso_vigencia.md`.

**Pruebas:** 1.184 backend · 156 móvil · 19 panel. Todo verde al cierre del día.

---

## Lo que sigue abierto, y no es urgente para el 15

| | Qué | Por qué espera |
|---|---|---|
| 1 | Probar la **segunda escritura al Oracle** del sistema anterior sobre el mismo hogar | Los `GIC_*` tienen su propia regla de vigencia y pueden rechazarla —o aceptarla en silencio sin escribir—. Hoy no estorba porque `ORACLE_SYNC_AUTOMATICA` está en `False` |
| 2 | Ajustar el **Manual de Usuario §5.1.1**, el documento misional | No es nuestro: lo define el proceso. El manual de uso de la APK ya está en 1.3 |
| 3 | Decidir si el soporte se **aplaza** o se **elimina** | Está preguntado en el numeral 2 del correo. Si nadie contesta, queda eliminado y así consta |

---

## Dos cosas que conviene no olvidar

**El registro se llena solo, pero nadie lo mira solo.** La pantalla del panel existe
precisamente para eso; si en un mes nadie ha entrado, el libro no está sirviendo para
nada y conviene decirlo antes de que lo pregunte control interno.

**`dias_restantes` se lee al revés.** Cuenta los días que le FALTABAN a la ficha por
vencer, así que el número más alto es la recaracterización más temprana y por tanto
la más grave. La pantalla ya lo traduce a «hace 7 días», pero quien consulte la API
directamente tiene que saberlo o va a ordenar al contrario y dejar fuera justo los
casos que busca.
